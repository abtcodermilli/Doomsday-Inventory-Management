import csv
import sqlite3
import tempfile
import unittest
from pathlib import Path

from database import Database, price_to_paise


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "test.db"
        self.db = Database(self.path)

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def add(self, sku="TEST-1", quantity=10, name="Test item"):
        return self.db.add_product(sku, name, "Stationery", "Supplier", "10.25", quantity, 3)

    def test_product_is_persisted_with_exact_price(self):
        product_id = self.add()
        self.db.close()
        self.db = Database(self.path)
        self.assertEqual(self.db.get_product(product_id)["price_paise"], 1025)
        self.assertEqual(self.db.summary()["value"], 10250)

    def test_duplicate_sku_is_case_insensitive_and_atomic(self):
        self.add()
        with self.assertRaises(ValueError):
            self.add("test-1")
        self.assertEqual(len(self.db.products()), 1)
        self.assertEqual(len(self.db.history()), 1)

    def test_stock_changes_and_history_balances(self):
        product_id = self.add()
        self.assertEqual(self.db.change_stock(product_id, "IN", 4, "Delivery"), 14)
        self.assertEqual(self.db.change_stock(product_id, "OUT", 11, "Sold"), 3)
        self.assertEqual([r["balance"] for r in self.db.history()], [3, 14, 10])
        self.assertEqual(self.db.summary()["low"], 1)

    def test_overselling_rolls_back_both_tables(self):
        product_id = self.add()
        with self.assertRaises(ValueError):
            self.db.change_stock(product_id, "OUT", 11)
        self.assertEqual(self.db.get_product(product_id)["quantity"], 10)
        self.assertEqual(len(self.db.history()), 1)

    def test_invalid_quantities(self):
        product_id = self.add()
        for value in ("-1", "1.5", "abc", "0", "1000001", "²"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.db.change_stock(product_id, "IN", value)
        self.assertEqual(self.db.get_product(product_id)["quantity"], 10)

    def test_prices_reject_nonfinite_negative_and_excess_precision(self):
        for value in ("nan", "Infinity", "-1", "1.999", "abc", "10000001", "1e1000"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                price_to_paise(value)
        self.assertEqual(price_to_paise("0.29"), 29)

    def test_edit_preserves_quantity_and_original_history(self):
        product_id = self.add()
        self.db.update_product(product_id, "NEW-1", "Renamed", "Electronics", "New supplier", "20.50", 2)
        self.assertEqual(self.db.get_product(product_id)["quantity"], 10)
        self.assertEqual(self.db.history()[0]["sku"], "TEST-1")
        self.assertEqual(self.db.history()[0]["product_name"], "Test item")

    def test_archive_preserves_history_and_blocks_updates(self):
        product_id = self.add()
        with self.assertRaises(ValueError):
            self.db.archive_product(product_id)
        self.db.change_stock(product_id, "OUT", 10)
        self.db.archive_product(product_id)
        self.assertEqual(len(self.db.products()), 0)
        self.assertEqual(len(self.db.history()), 2)
        with self.assertRaises(ValueError):
            self.db.change_stock(product_id, "IN", 1)

    def test_search_treats_sql_and_wildcards_as_text(self):
        self.add(name="100% Cotton")
        self.add("TEST-2", name="Notebook")
        self.assertEqual(len(self.db.products("%")), 1)
        self.assertEqual(len(self.db.products("' OR 1=1 --")), 0)
        self.assertEqual(len(self.db.products(category="Stationery")), 2)

    def test_csv_export_and_formula_protection(self):
        self.add(name="=SUM(1,1)")
        path = Path(self.temp.name) / "report.csv"
        self.db.export_products(path)
        with path.open(encoding="utf-8-sig", newline="") as file:
            rows = list(csv.reader(file))
        self.assertEqual(rows[1][1], "'=SUM(1,1)")
        self.assertEqual(rows[1][4], "10.25")
        self.db.export_history(path)
        with path.open(encoding="utf-8-sig", newline="") as file:
            self.assertEqual(len(list(csv.reader(file))), 2)

    def test_backup_can_be_opened_independently(self):
        self.add()
        path = Path(self.temp.name) / "backup.db"
        self.db.backup(path)
        with sqlite3.connect(path) as backup:
            self.assertEqual(backup.execute("SELECT quantity FROM products").fetchone()[0], 10)
            self.assertEqual(backup.execute("PRAGMA integrity_check").fetchone()[0], "ok")
        with self.assertRaises(ValueError):
            self.db.backup(self.path)

    def test_demo_and_summary(self):
        self.assertEqual(self.db.summary()["products"], 0)
        self.db.load_demo()
        self.assertEqual(self.db.summary()["products"], 8)
        self.assertEqual(self.db.summary()["units"], 174)
        self.assertEqual(self.db.summary()["low"], 3)
        self.assertEqual(sum(r["value"] for r in self.db.category_summary()), self.db.summary()["value"])
        with self.assertRaises(ValueError):
            self.db.load_demo()


if __name__ == "__main__":
    unittest.main()
