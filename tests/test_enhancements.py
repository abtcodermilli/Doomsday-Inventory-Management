import csv
import sqlite3
import tempfile
import unittest
from pathlib import Path

from services import InventoryService
from cart import OrderCart
from import_utils import CSV_COLUMNS, read_product_csv, write_template


class EnhancementTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name)
        self.db=InventoryService(self.root/'test.db')
        self.db.setup_admin('admin','Doomsday','test-password')
        self.p=self.db.add_product('P-1','Product One','General','','20',20,2)
        self.q=self.db.add_product('P-2','Product Two','General','','10',10,2)

    def tearDown(self):
        self.db.close(); self.temp.cleanup()

    def csv(self,rows,header=None):
        path=self.root/'products.csv'
        with path.open('w',newline='',encoding='utf-8-sig') as file:
            writer=csv.writer(file); writer.writerow(CSV_COLUMNS if header is None else header); writer.writerows(rows)
        return path

    def sale(self,day,lines=None):
        lines=lines or [{'product_id':self.p,'quantity':2,'price':'20'}]
        order_id=self.db.create_order('SALE','Customer',lines)
        with self.db.connection:
            self.db.connection.execute('UPDATE orders SET created_at=?,completed_at=? WHERE id=?',(day,day,order_id))
        return order_id

    def test_report_includes_both_date_boundaries_and_avoids_join_double_count(self):
        self.sale('2026-11-01 00:00:00',[{'product_id':self.p,'quantity':2,'price':'20'}, {'product_id':self.q,'quantity':3,'price':'10'}])
        self.sale('2026-11-03 23:59:59'); self.sale('2026-11-04 00:00:00')
        report=self.db.sales_report('2026-11-01','2026-11-03')
        self.assertEqual((report['sales'],report['order_count'],report['units']),(11000,2,7))
        self.assertEqual([r['units'] for r in report['products']],[4,3])
        self.assertEqual(sum(r['revenue'] for r in report['products']),report['sales'])

    def test_report_excludes_cancelled_sales_and_purchases(self):
        order=self.sale('2026-11-01 12:00:00'); self.db.cancel_order(order)
        supplier=self.db.save_supplier('Supplier')
        self.db.create_order('PURCHASE','',[{'product_id':self.p,'quantity':4,'price':'10'}],supplier_id=supplier)
        report=self.db.sales_report('2020-01-01','2030-12-31')
        self.assertEqual((report['sales'],report['units'],report['order_count']),(0,0,0))

    def test_report_keeps_archived_products_and_historical_prices(self):
        self.sale('2026-11-01 12:00:00',[{'product_id':self.p,'quantity':20,'price':'5.25'}])
        self.db.update_product(self.p,'NEW-SKU','Renamed','General','','99',2)
        self.db.archive_product(self.p)
        report=self.db.sales_report('2026-11-01','2026-11-01')
        self.assertEqual(report['sales'],10500)
        self.assertEqual(report['products'][0]['name'],'Renamed')

    def test_invalid_dates_rejected(self):
        for start,end in [('2026-02-30','2026-11-01'),('2026-11-02','2026-11-01'),('20261101','2026-11-01'),('','2026-11-01')]:
            with self.subTest(start=start),self.assertRaises(ValueError): self.db.sales_report(start,end)

    def test_report_export_contains_dates_totals_and_orders(self):
        self.sale('2026-11-01 12:00:00'); path=self.root/'report.csv'
        self.db.export_sales_report(path,'2026-11-01','2026-11-01')
        with path.open(encoding='utf-8-sig',newline='') as file: rows=list(csv.reader(file))
        self.assertEqual(rows[0][2],'2026-11-01'); self.assertEqual(rows[1][1],'40.00')
        self.assertIn('SO-00001',path.read_text(encoding='utf-8-sig'))

    def test_template_preview_is_read_only_and_import_persists_opening_history(self):
        path=self.root/'template.csv'; write_template(path)
        preview=self.db.preview_product_import(path)
        self.assertTrue(all(not r['errors'] for r in preview)); self.assertEqual(len(self.db.products()),2)
        self.assertEqual(self.db.import_products(preview),3)
        self.assertEqual(len(self.db.products()),5)
        self.assertEqual(len(self.db.history('IMP-101')),1)
        self.assertEqual(self.db.activities()[0]['action'],'CSV IMPORTED')
        self.db.close(); self.db=InventoryService(self.root/'test.db')
        self.assertEqual(self.db.products('IMP-101')[0]['quantity'],25)

    def test_import_invalid_row_prevents_all_writes(self):
        path=self.csv([['IMP-A','Good','General','','2.50','4','1'],['IMP-B','','General','','nan','-1','3']])
        preview=self.db.preview_product_import(path)
        self.assertFalse(preview[0]['errors']); self.assertGreaterEqual(len(preview[1]['errors']),3)
        with self.assertRaisesRegex(ValueError,'Row 3'): self.db.import_products(preview)
        self.assertEqual(len(self.db.products()),2); self.assertFalse(self.db.history('IMP-A'))

    def test_duplicate_skus_mark_both_csv_rows(self):
        path=self.csv([['DUP','First','General','','2','0','1'],['dup','Second','General','','2','0','1']])
        preview=self.db.preview_product_import(path)
        self.assertTrue(all(any('Duplicate SKU' in e for e in r['errors']) for r in preview))
        with self.assertRaises(ValueError): self.db.import_products(preview)

    def test_existing_archived_sku_rejected(self):
        self.db.change_stock(self.p,'OUT',20); self.db.archive_product(self.p)
        path=self.csv([['p-1','Existing','General','','2','0','1']])
        self.assertIn('archived',self.db.preview_product_import(path)[0]['errors'][0])

    def test_import_revalidates_if_database_changed_after_preview(self):
        path=self.csv([['IMP-A','First','General','','2','1','1'],['IMP-B','Second','General','','2','1','1']])
        preview=self.db.preview_product_import(path)
        self.db.add_product('IMP-B','Concurrent product','General','','1',0,1)
        with self.assertRaises(ValueError): self.db.import_products(preview)
        self.assertFalse(self.db.products('IMP-A'))

    def test_import_snapshot_does_not_reread_changed_file(self):
        path=self.csv([['IMP-A','First','General','','2','1','1']]); preview=self.db.preview_product_import(path)
        path.write_text('corrupted file')
        self.db.import_products(preview)
        self.assertEqual(self.db.products('IMP-A')[0]['quantity'],1)

    def test_database_failure_mid_import_rolls_back_products_movements_and_activity(self):
        path=self.csv([['IMP-A','First','General','','2','1','1'],['IMP-B','Second','General','','2','1','1']])
        preview=self.db.preview_product_import(path); before=len(self.db.activities())
        self.db.connection.execute("CREATE TEMP TRIGGER reject_import BEFORE INSERT ON products WHEN NEW.sku='IMP-B' BEGIN SELECT RAISE(ABORT,'simulated failure'); END")
        with self.assertRaises(sqlite3.IntegrityError): self.db.import_products(preview)
        self.assertFalse(self.db.products('IMP-A')); self.assertFalse(self.db.history('IMP-A')); self.assertEqual(len(self.db.activities()),before)

    def test_csv_headers_structure_and_encoding(self):
        with self.assertRaisesRegex(ValueError,'Missing columns'): read_product_csv(self.csv([['X']],['sku']))
        with self.assertRaisesRegex(ValueError,'duplicate column'): read_product_csv(self.csv([],['sku','sku']))
        path=self.csv([['X','Missing other cells']])
        self.assertTrue(self.db.preview_product_import(path)[0]['file_errors'])
        path.write_bytes(b'\xff\xfe\x80')
        with self.assertRaisesRegex(ValueError,'UTF-8'): read_product_csv(path)

    def test_exported_inventory_headers_can_be_read(self):
        path=self.root/'export.csv'; self.db.export_products(path)
        parsed=read_product_csv(path)
        self.assertEqual(parsed[0]['values']['name'],'Product One')
        self.assertEqual(parsed[0]['values']['price'],'20.00')

    def test_restore_preserves_id_quantity_and_history(self):
        self.db.change_stock(self.p,'OUT',20); self.db.archive_product(self.p)
        before=len(self.db.history()); self.assertEqual(self.db.archived_products('P-1')[0]['id'],self.p)
        self.db.restore_product(self.p)
        self.assertEqual(self.db.get_product(self.p)['quantity'],0)
        self.assertEqual(len(self.db.history()),before); self.assertFalse(self.db.archived_products())
        self.assertEqual(self.db.activities()[0]['action'],'PRODUCT RESTORED')
        with self.assertRaises(ValueError): self.db.restore_product(self.p)

    def test_staff_cannot_import_or_restore_but_can_read_reports(self):
        self.db.add_user('staff','Staff','test-password'); self.db.login('staff','test-password')
        for action in [lambda:self.db.preview_product_import('unused.csv'),lambda:self.db.import_products([]),lambda:self.db.restore_product(self.p),self.db.archived_products]:
            with self.assertRaises(ValueError): action()
        self.assertEqual(self.db.sales_report('2026-01-01','2026-12-31')['sales'],0)

    def test_cart_edits_recalculate_exact_total_without_changing_stock(self):
        cart=OrderCart(self.db,'SALE'); cart.add(self.p,2,'19.99'); cart.add(self.q,1,'9.50')
        cart.update(self.p,3,'20.25')
        self.assertEqual(cart.total_paise,7025); self.assertEqual(self.db.get_product(self.p)['quantity'],20)
        order=self.db.create_order('SALE','Customer',cart.items)
        self.assertEqual(self.db.order_details(order)[0]['total_paise'],7025)
        self.assertEqual(self.db.get_product(self.p)['quantity'],17)

    def test_invalid_cart_edits_leave_original_item_unchanged(self):
        cart=OrderCart(self.db,'SALE'); cart.add(self.p,2,'19.99')
        for qty,price in [(21,'20'),('1.5','20'),(0,'20'),(3,'nan'),(3,'1.999')]:
            with self.assertRaises(ValueError): cart.update(self.p,qty,price)
            self.assertEqual(cart.total_paise,3998)
        with self.assertRaises(ValueError): cart.add(self.p,1,'20')
        cart.remove(self.p); self.assertEqual(cart.total_paise,0)

    def test_cart_edit_uses_latest_stock_and_purchase_can_exceed_on_hand(self):
        cart=OrderCart(self.db,'SALE'); cart.add(self.p,2,'20'); self.db.change_stock(self.p,'OUT',19)
        with self.assertRaises(ValueError): cart.update(self.p,2,'20')
        with self.assertRaises(ValueError): self.db.create_order('SALE','Customer',cart.items)
        purchase=OrderCart(self.db,'PURCHASE'); purchase.add(self.p,40,'10'); purchase.update(self.p,50,'9')
        self.assertEqual(purchase.total_paise,45000)


if __name__=='__main__': unittest.main()
