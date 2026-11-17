"""SQLite storage and validation for the Doomsday Inventory project."""

import csv
import sqlite3
from decimal import Decimal, InvalidOperation
from pathlib import Path


def whole_number(value, label, minimum=0):
    text = str(value).strip()
    if not text.isascii() or not text.isdigit():
        raise ValueError(f"{label} must be a whole number.")
    number = int(text)
    if not minimum <= number <= 1_000_000:
        raise ValueError(f"{label} must be between {minimum:,} and 1,000,000.")
    return number


def price_to_paise(value):
    try:
        number = Decimal(str(value).strip())
        if not number.is_finite() or not 0 <= number <= 10_000_000:
            raise ValueError("Price must be between 0 and 10,000,000.")
        if number != number.quantize(Decimal("0.01")):
            raise ValueError("Price can have at most two decimal places.")
        return int(number * 100)
    except InvalidOperation:
        raise ValueError("Enter a valid price, for example 149.50.") from None


def required_text(value, label, limit=100):
    text = str(value).strip()
    if not text or len(text) > limit:
        raise ValueError(f"{label} is required (maximum {limit} characters).")
    return text


def csv_safe(value):
    # Prevent spreadsheet programs from treating text as a formula.
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


class Database:
    def __init__(self, path=None):
        self.path = Path(path) if path else Path(__file__).resolve().parent / "data" / "inventory.db"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sku TEXT NOT NULL COLLATE NOCASE UNIQUE,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                supplier TEXT NOT NULL DEFAULT '',
                price_paise INTEGER NOT NULL CHECK(price_paise >= 0),
                quantity INTEGER NOT NULL CHECK(quantity >= 0),
                reorder_level INTEGER NOT NULL CHECK(reorder_level >= 0),
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            );
            CREATE TABLE IF NOT EXISTS movements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL REFERENCES products(id),
                sku TEXT NOT NULL,
                product_name TEXT NOT NULL,
                kind TEXT NOT NULL CHECK(kind IN ('OPENING', 'IN', 'OUT')),
                quantity INTEGER NOT NULL CHECK(quantity > 0),
                balance INTEGER NOT NULL CHECK(balance >= 0),
                note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            );
        """)
        self.connection.commit()

    def close(self):
        self.connection.close()

    def _details(self, sku, name, category, supplier, price, reorder_level):
        return (required_text(sku, "SKU", 30).upper(), required_text(name, "Product name"),
                required_text(category, "Category", 50), str(supplier).strip()[:100],
                price_to_paise(price), whole_number(reorder_level, "Reorder level"))

    def add_product(self, sku, name, category, supplier, price, quantity, reorder_level):
        details = self._details(sku, name, category, supplier, price, reorder_level)
        quantity = whole_number(quantity, "Opening quantity")
        try:
            with self.connection:
                cursor = self.connection.execute("""
                    INSERT INTO products(sku, name, category, supplier, price_paise, reorder_level, quantity)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (*details, quantity))
                product_id = cursor.lastrowid
                if quantity:
                    self._movement(product_id, details[0], details[1], "OPENING", quantity, quantity, "Opening stock")
            return product_id
        except sqlite3.IntegrityError:
            raise ValueError("This SKU already exists, possibly in archived products. Use a unique SKU.") from None

    def update_product(self, product_id, sku, name, category, supplier, price, reorder_level):
        details = self._details(sku, name, category, supplier, price, reorder_level)
        try:
            with self.connection:
                cursor = self.connection.execute("""
                    UPDATE products SET sku=?, name=?, category=?, supplier=?, price_paise=?, reorder_level=?
                    WHERE id=? AND active=1
                """, (*details, product_id))
                if not cursor.rowcount:
                    raise ValueError("This product is no longer active.")
        except sqlite3.IntegrityError:
            raise ValueError("This SKU already exists. Use a unique SKU.") from None

    def get_product(self, product_id):
        row = self.connection.execute("SELECT * FROM products WHERE id=? AND active=1", (product_id,)).fetchone()
        if row is None:
            raise ValueError("Product not found or archived.")
        return row

    def products(self, search="", category="All categories", low_only=False):
        sql = "SELECT * FROM products WHERE active=1"
        values = []
        if search.strip():
            term = search.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            sql += " AND (sku LIKE ? ESCAPE '\\' OR name LIKE ? ESCAPE '\\' OR supplier LIKE ? ESCAPE '\\')"
            values.extend([f"%{term}%"] * 3)
        if category != "All categories":
            sql += " AND category=?"
            values.append(category)
        if low_only:
            sql += " AND quantity <= reorder_level"
        return self.connection.execute(sql + " ORDER BY name COLLATE NOCASE", values).fetchall()

    def categories(self):
        return [r[0] for r in self.connection.execute(
            "SELECT DISTINCT category FROM products WHERE active=1 ORDER BY category COLLATE NOCASE")]

    def _movement(self, product_id, sku, name, kind, quantity, balance, note):
        self.connection.execute("""
            INSERT INTO movements(product_id, sku, product_name, kind, quantity, balance, note)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (product_id, sku, name, kind, quantity, balance, note))

    def change_stock(self, product_id, kind, quantity, note=""):
        if kind not in ("IN", "OUT"):
            raise ValueError("Choose stock IN or OUT.")
        quantity = whole_number(quantity, "Quantity", 1)
        note = str(note).strip()
        if len(note) > 200:
            raise ValueError("Note must be 200 characters or fewer.")
        # Lock before reading so the update and history entry stay consistent.
        with self.connection:
            self.connection.execute("BEGIN IMMEDIATE")
            product = self.get_product(product_id)
            balance = product["quantity"] + (quantity if kind == "IN" else -quantity)
            if balance < 0:
                raise ValueError(f"Only {product['quantity']} units are available.")
            if balance > 1_000_000:
                raise ValueError("A product can hold at most 1,000,000 units.")
            self.connection.execute("UPDATE products SET quantity=? WHERE id=?", (balance, product_id))
            self._movement(product_id, product["sku"], product["name"], kind, quantity, balance, note)
        return balance

    def archive_product(self, product_id):
        with self.connection:
            self.connection.execute("BEGIN IMMEDIATE")
            product = self.get_product(product_id)
            if product["quantity"]:
                raise ValueError("Record stock out for the remaining units before archiving this product.")
            self.connection.execute("UPDATE products SET active=0 WHERE id=?", (product_id,))

    def history(self, search="", kind="All types"):
        sql = "SELECT * FROM movements WHERE 1=1"
        values = []
        if search.strip():
            term = search.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            sql += " AND (sku LIKE ? ESCAPE '\\' OR product_name LIKE ? ESCAPE '\\' OR note LIKE ? ESCAPE '\\')"
            values.extend([f"%{term}%"] * 3)
        if kind != "All types":
            sql += " AND kind=?"
            values.append(kind)
        return self.connection.execute(sql + " ORDER BY id DESC", values).fetchall()

    def summary(self):
        return self.connection.execute("""
            SELECT COUNT(*) AS products, COALESCE(SUM(quantity),0) AS units,
                   COALESCE(SUM(quantity*price_paise),0) AS value,
                   COALESCE(SUM(quantity<=reorder_level),0) AS low
            FROM products WHERE active=1
        """).fetchone()

    def category_summary(self):
        return self.connection.execute("""
            SELECT category, COUNT(*) AS products, SUM(quantity) AS units,
                   SUM(quantity*price_paise) AS value
            FROM products WHERE active=1 GROUP BY category ORDER BY value DESC
        """).fetchall()

    def export_products(self, path, rows=None):
        rows = self.products() if rows is None else rows
        with open(path, "w", newline="", encoding="utf-8-sig") as file:
            writer = csv.writer(file)
            writer.writerow(["SKU", "Product", "Category", "Supplier", "Unit price INR", "Quantity", "Reorder level", "Stock value INR", "Status"])
            for p in rows:
                writer.writerow([csv_safe(p["sku"]), csv_safe(p["name"]), csv_safe(p["category"]),
                                 csv_safe(p["supplier"]), f"{p['price_paise']/100:.2f}", p["quantity"],
                                 p["reorder_level"], f"{p['price_paise']*p['quantity']/100:.2f}",
                                 "Low stock" if p["quantity"] <= p["reorder_level"] else "In stock"])

    def export_history(self, path, rows=None):
        rows = self.history() if rows is None else rows
        with open(path, "w", newline="", encoding="utf-8-sig") as file:
            writer = csv.writer(file)
            writer.writerow(["Date", "SKU", "Product", "Type", "Quantity", "Balance after", "Note"])
            for r in rows:
                writer.writerow([csv_safe(r[k]) for k in ("created_at", "sku", "product_name", "kind", "quantity", "balance", "note")])

    def backup(self, destination):
        if Path(destination).resolve() == self.path.resolve():
            raise ValueError("Choose a different file from the working database.")
        target = sqlite3.connect(destination)
        try:
            self.connection.backup(target)
        finally:
            target.close()

    def load_demo(self):
        if self.connection.execute("SELECT COUNT(*) FROM products").fetchone()[0]:
            raise ValueError("Demo data can only be loaded into a new, empty database.")
        samples = [
            ("EL-101", "Wireless Mouse", "Electronics", "Campus Tech", "599", 32, 8),
            ("EL-102", "USB-C Cable", "Electronics", "Campus Tech", "249", 6, 10),
            ("EL-103", "Keyboard", "Electronics", "Campus Tech", "899", 14, 5),
            ("ST-101", "A4 Notebook", "Stationery", "Paper House", "85", 75, 20),
            ("ST-102", "Blue Pen Pack", "Stationery", "Paper House", "120", 9, 10),
            ("ST-103", "Desk Organizer", "Stationery", "Paper House", "349", 18, 5),
            ("AC-101", "Laptop Sleeve", "Accessories", "Everyday Supplies", "699", 20, 5),
            ("AC-102", "Water Bottle", "Accessories", "Everyday Supplies", "399", 0, 5),
        ]
        for sample in samples:
            self.add_product(*sample)
