import sqlite3
import tempfile
import unittest
from pathlib import Path

from database import Database
from services import InventoryService


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.path=Path(self.temp.name)/'test.db'
        self.db=InventoryService(self.path)
        self.db.setup_admin('admin','Team Doomsday','test-password')
        self.p=self.db.add_product('A-1','Notebook','Stationery','Paper House','100',10,3)
        self.q=self.db.add_product('A-2','Pen','Stationery','Paper House','20',2,3)
        self.supplier=self.db.save_supplier('Paper House','Orders','123456','orders@example.com')

    def tearDown(self):
        self.db.close(); self.temp.cleanup()

    def line(self,p=None,q=2,price='100'):
        return {'product_id':self.p if p is None else p,'quantity':q,'price':price}

    def purchase(self):
        return self.db.create_order('PURCHASE','',[self.line(q=5,price='75')],supplier_id=self.supplier)

    def test_passwords_are_salted_hashes_and_login_validated(self):
        self.db.add_user('staff','Staff Member','test-password')
        rows=self.db.connection.execute('SELECT salt,password_hash FROM users').fetchall()
        self.assertNotEqual(rows[0]['salt'],rows[1]['salt'])
        self.assertNotEqual(rows[0]['password_hash'],rows[1]['password_hash'])
        with self.assertRaises(ValueError): self.db.login('admin','wrong-pass')
        self.assertIsNone(self.db.user)
        self.db.login('ADMIN','test-password')
        self.assertEqual(self.db.user['role'],'Admin')
        with self.assertRaises(ValueError): self.db.setup_admin('other','Other','test-password')

    def test_password_change_survives_reopen(self):
        self.db.change_password('test-password','new-password')
        self.db.close(); self.db=InventoryService(self.path)
        with self.assertRaises(ValueError): self.db.login('admin','test-password')
        self.db.login('admin','new-password')
        self.assertEqual(self.db.user['username'],'admin')

    def test_staff_permissions_enforced_in_backend(self):
        self.db.add_user('staff','Staff Member','test-password')
        self.db.login('staff','test-password')
        denied=[lambda:self.db.save_supplier('Denied'),lambda:self.db.change_stock(self.p,'IN',1),
                self.purchase,lambda:self.db.add_user('x','X','test-password'),
                lambda:self.db.archive_product(self.p),lambda:self.db.backup(Path(self.temp.name)/'b.db'),
                self.db.database_info]
        for action in denied:
            with self.assertRaises(ValueError): action()
        order_id=self.db.create_order('SALE','Student',[self.line()])
        self.assertEqual(self.db.order_details(order_id)[0]['created_by'],self.db.user['id'])
        self.assertEqual(self.db.get_product(self.p)['quantity'],8)
        with self.assertRaises(ValueError): self.db.cancel_order(order_id)

    def test_purchase_draft_does_not_change_stock_then_receive_once(self):
        order_id=self.purchase()
        self.assertEqual(self.db.get_product(self.p)['quantity'],10)
        self.assertEqual(self.db.order_details(order_id)[0]['status'],'PENDING')
        self.db.receive_purchase(order_id)
        self.assertEqual(self.db.get_product(self.p)['quantity'],15)
        with self.assertRaises(ValueError): self.db.receive_purchase(order_id)
        self.assertEqual(self.db.get_product(self.p)['quantity'],15)
        self.assertEqual(self.db.history()[0]['note'],f'Received PO-{order_id:05d}')

    def test_failed_sale_rolls_back_all_rows_and_stock(self):
        before=(len(self.db.orders('SALE')),len(self.db.history()),len(self.db.activities()))
        with self.assertRaises(ValueError):
            self.db.create_order('SALE','Customer',[self.line(q=3),self.line(self.q,9,'20')])
        self.assertEqual(self.db.get_product(self.p)['quantity'],10)
        self.assertEqual(self.db.get_product(self.q)['quantity'],2)
        self.assertEqual((len(self.db.orders('SALE')),len(self.db.history()),len(self.db.activities())),before)
        self.assertEqual(self.db.connection.execute('SELECT COUNT(*) FROM order_items').fetchone()[0],0)

    def test_sale_snapshot_and_receipt_total(self):
        order_id=self.db.create_order('SALE','Customer',[self.line(q=3,price='49.99'),self.line(self.q,1,'20')])
        self.db.update_product(self.p,'A-1','New name','Stationery','','999',3)
        order,items=self.db.order_details(order_id)
        self.assertEqual(order['total_paise'],16997)
        self.assertEqual(items[0]['product_name'],'Notebook')
        self.assertIn('TOTAL: INR 169.97',self.db.receipt_text(order_id))
        self.assertEqual(self.db.business_summary()['sales'],16997)

    def test_void_sale_restores_stock_once_and_excludes_revenue(self):
        order_id=self.db.create_order('SALE','Customer',[self.line(q=10)])
        self.db.archive_product(self.p)
        self.db.cancel_order(order_id)
        self.assertEqual(self.db.get_product(self.p)['quantity'],10)
        self.assertEqual(self.db.business_summary()['sales'],0)
        with self.assertRaises(ValueError): self.db.cancel_order(order_id)
        self.assertEqual(self.db.get_product(self.p)['quantity'],10)

    def test_cancel_purchase_does_not_move_stock(self):
        order_id=self.purchase(); self.db.cancel_order(order_id)
        self.assertEqual(self.db.get_product(self.p)['quantity'],10)
        with self.assertRaises(ValueError): self.db.receive_purchase(order_id)

    def test_received_purchase_cannot_be_cancelled(self):
        order_id=self.purchase(); self.db.receive_purchase(order_id)
        with self.assertRaises(ValueError): self.db.cancel_order(order_id)
        self.assertEqual(self.db.get_product(self.p)['quantity'],15)

    def test_receive_rolls_back_if_one_product_exceeds_limit(self):
        order_id=self.db.create_order('PURCHASE','',[self.line(),self.line(self.q,2,'20')],supplier_id=self.supplier)
        self.db.change_stock(self.q,'IN',999998)
        with self.assertRaises(ValueError): self.db.receive_purchase(order_id)
        self.assertEqual(self.db.get_product(self.p)['quantity'],10)
        self.assertEqual(self.db.order_details(order_id)[0]['status'],'PENDING')

    def test_pending_orders_prevent_archiving(self):
        self.purchase(); self.db.change_stock(self.p,'OUT',10)
        with self.assertRaises(ValueError): self.db.archive_product(self.p)

    def test_empty_and_duplicate_order_lines_are_rejected(self):
        for lines in [[],[self.line(),self.line()]]:
            with self.assertRaises(ValueError): self.db.create_order('SALE','Customer',lines)
        self.assertFalse(self.db.orders('SALE'))

    def test_supplier_validation_and_update(self):
        with self.assertRaises(ValueError): self.db.save_supplier('paper house')
        with self.assertRaises(ValueError): self.db.save_supplier('New supplier',email='not-an-email')
        self.db.save_supplier('Paper House Ltd',supplier_id=self.supplier)
        self.assertEqual(self.db.suppliers()[0]['name'],'Paper House Ltd')

    def test_database_foreign_keys_and_integrity(self):
        self.purchase()
        self.assertEqual(len(self.db.database_info()),7)
        self.assertEqual(self.db.connection.execute('PRAGMA integrity_check').fetchone()[0],'ok')
        self.assertEqual(self.db.connection.execute('PRAGMA foreign_key_check').fetchall(),[])

    def test_legacy_database_upgrades_without_data_loss(self):
        path=Path(self.temp.name)/'legacy.db'
        old=Database(path); old.add_product('OLD','Legacy','Other','','10',7,2); old.close()
        new=InventoryService(path)
        self.assertTrue(new.needs_setup())
        self.assertEqual(new.products()[0]['quantity'],7)
        self.assertEqual(len(new.history()),1)
        self.assertEqual(new.connection.execute('PRAGMA user_version').fetchone()[0],2)
        new.close()


if __name__=='__main__': unittest.main()
