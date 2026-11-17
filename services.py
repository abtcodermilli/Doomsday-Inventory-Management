"""Application backend: accounts, permissions, purchasing, sales and activity."""

import hashlib
import hmac
import secrets
import sqlite3
import csv
from datetime import date, timedelta

from database import Database, price_to_paise, required_text, whole_number, csv_safe
from import_utils import CSV_COLUMNS, read_product_csv


class InventoryService(Database):
    def __init__(self, path=None):
        super().__init__(path)
        self.user = None
        self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL COLLATE NOCASE UNIQUE,
                full_name TEXT NOT NULL,
                salt TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('Admin','Staff'))
            );
            CREATE TABLE IF NOT EXISTS suppliers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL COLLATE NOCASE UNIQUE,
                contact TEXT NOT NULL DEFAULT '',
                phone TEXT NOT NULL DEFAULT '',
                email TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL CHECK(kind IN ('PURCHASE','SALE')),
                partner TEXT NOT NULL,
                supplier_id INTEGER REFERENCES suppliers(id),
                status TEXT NOT NULL CHECK(status IN ('PENDING','COMPLETED','CANCELLED')),
                total_paise INTEGER NOT NULL CHECK(total_paise >= 0),
                note TEXT NOT NULL DEFAULT '',
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
                completed_at TEXT
            );
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL REFERENCES orders(id),
                product_id INTEGER NOT NULL REFERENCES products(id),
                sku TEXT NOT NULL,
                product_name TEXT NOT NULL,
                quantity INTEGER NOT NULL CHECK(quantity > 0),
                price_paise INTEGER NOT NULL CHECK(price_paise >= 0),
                UNIQUE(order_id, product_id)
            );
            CREATE TABLE IF NOT EXISTS activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                action TEXT NOT NULL,
                detail TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
            );
            CREATE INDEX IF NOT EXISTS idx_movements_product ON movements(product_id);
            CREATE INDEX IF NOT EXISTS idx_orders_kind_status ON orders(kind,status);
            CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);
            PRAGMA user_version = 2;
        """)
        self.connection.commit()

    def needs_setup(self):
        return self.connection.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0

    def require(self, admin=False):
        if self.user is None:
            raise ValueError("Please sign in first.")
        if admin and self.user["role"] != "Admin":
            raise ValueError("This action requires an Admin account.")

    @staticmethod
    def password_digest(password, salt):
        return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 600_000).hex()

    def _add_user(self, username, full_name, password, role):
        username = required_text(username, "Username", 30).lower()
        if not all(c.isascii() and (c.isalnum() or c in "_.-") for c in username):
            raise ValueError("Username can contain letters, digits, dots, underscores and hyphens.")
        full_name = required_text(full_name, "Full name", 80)
        if not 8 <= len(password) <= 128:
            raise ValueError("Choose a password between 8 and 128 characters.")
        if role not in ("Admin", "Staff"):
            raise ValueError("Choose Admin or Staff.")
        salt = secrets.token_hex(16)
        try:
            return self.connection.execute(
                "INSERT INTO users(username,full_name,salt,password_hash,role) VALUES(?,?,?,?,?)",
                (username, full_name, salt, self.password_digest(password, salt), role)).lastrowid
        except sqlite3.IntegrityError:
            raise ValueError("That username already exists.") from None

    def setup_admin(self, username, full_name, password):
        with self.connection:
            self.connection.execute("BEGIN IMMEDIATE")
            if not self.needs_setup():
                raise ValueError("An administrator already exists. Sign in instead.")
            self._add_user(username, full_name, password, "Admin")
        return self.login(username, password)

    def login(self, username, password):
        self.user = None
        if len(password) > 128:
            raise ValueError("Incorrect username or password.")
        row = self.connection.execute("SELECT * FROM users WHERE username=?", (username.strip(),)).fetchone()
        salt = row["salt"] if row else "00" * 16
        digest = self.password_digest(password, salt)
        if row is None or not hmac.compare_digest(digest, row["password_hash"]):
            raise ValueError("Incorrect username or password.")
        self.user = {key: row[key] for key in ("id", "username", "full_name", "role")}
        with self.connection:
            self._log("SIGNED IN", "Opened inventory workspace")
        return self.user

    def logout(self):
        if self.user:
            with self.connection:
                self._log("SIGNED OUT", "Closed inventory session")
        self.user = None

    def add_user(self, username, full_name, password, role="Staff"):
        self.require(admin=True)
        with self.connection:
            user_id = self._add_user(username, full_name, password, role)
            self._log("ACCOUNT CREATED", f"{username} / {role}")
        return user_id

    def users(self):
        self.require(admin=True)
        return self.connection.execute("SELECT id,username,full_name,role FROM users ORDER BY id").fetchall()

    def change_password(self, old_password, new_password):
        self.require()
        row = self.connection.execute("SELECT * FROM users WHERE id=?", (self.user["id"],)).fetchone()
        if not hmac.compare_digest(self.password_digest(old_password, row["salt"]), row["password_hash"]):
            raise ValueError("Current password is incorrect.")
        if not 8 <= len(new_password) <= 128:
            raise ValueError("Choose a password between 8 and 128 characters.")
        salt = secrets.token_hex(16)
        with self.connection:
            self.connection.execute("UPDATE users SET salt=?, password_hash=? WHERE id=?",
                                    (salt, self.password_digest(new_password, salt), self.user["id"]))
            self._log("PASSWORD CHANGED", "Updated own sign-in password")

    def _log(self, action, detail):
        self.connection.execute("INSERT INTO activity(user_id,action,detail) VALUES(?,?,?)",
                                (self.user["id"], action, detail))

    def activities(self, limit=100):
        self.require()
        return self.connection.execute("""
            SELECT a.*, u.full_name FROM activity a JOIN users u ON a.user_id=u.id
            ORDER BY a.id DESC LIMIT ?
        """, (limit,)).fetchall()

    def add_product(self, *args, **kwargs):
        self.require(admin=True)
        product_id = super().add_product(*args, **kwargs)
        with self.connection:
            self._log("PRODUCT ADDED", self.get_product(product_id)["name"])
        return product_id

    def update_product(self, *args, **kwargs):
        self.require(admin=True)
        super().update_product(*args, **kwargs)
        with self.connection:
            self._log("PRODUCT UPDATED", "Saved product details")

    def change_stock(self, *args, **kwargs):
        self.require(admin=True)
        balance = super().change_stock(*args, **kwargs)
        with self.connection:
            self._log("STOCK ADJUSTED", f"Manual movement saved; balance {balance}")
        return balance

    def archive_product(self, product_id):
        self.require(admin=True)
        pending = self.connection.execute("""
            SELECT COUNT(*) FROM order_items i JOIN orders o ON i.order_id=o.id
            WHERE i.product_id=? AND o.status='PENDING'
        """, (product_id,)).fetchone()[0]
        if pending:
            raise ValueError("Receive or cancel pending purchase orders for this product first.")
        name = self.get_product(product_id)["name"]
        super().archive_product(product_id)
        with self.connection:
            self._log("PRODUCT ARCHIVED", name)

    def save_supplier(self, name, contact="", phone="", email="", supplier_id=None):
        self.require(admin=True)
        name = required_text(name, "Supplier name")
        values = [name]
        for value, label in [(contact, "Contact"), (phone, "Phone"), (email, "Email")]:
            value = value.strip()
            if len(value) > 100:
                raise ValueError(f"{label} must be 100 characters or fewer.")
            values.append(value)
        if values[3] and ("@" not in values[3] or "." not in values[3].split("@")[-1]):
            raise ValueError("Enter a valid supplier email or leave it blank.")
        try:
            with self.connection:
                if supplier_id is None:
                    supplier_id = self.connection.execute(
                        "INSERT INTO suppliers(name,contact,phone,email) VALUES(?,?,?,?)", values).lastrowid
                else:
                    cursor = self.connection.execute("UPDATE suppliers SET name=?,contact=?,phone=?,email=? WHERE id=?", (*values, supplier_id))
                    if not cursor.rowcount:
                        raise ValueError("Supplier not found.")
                self._log("SUPPLIER SAVED", name)
        except sqlite3.IntegrityError:
            raise ValueError("A supplier with this name already exists.") from None
        return supplier_id

    def suppliers(self, search=""):
        self.require()
        rows = self.connection.execute("SELECT * FROM suppliers ORDER BY name COLLATE NOCASE").fetchall()
        return [r for r in rows if search.lower() in (r["name"] + " " + r["contact"] + " " + r["email"]).lower()]

    def _validate_lines(self, lines):
        if not lines or len(lines) > 100:
            raise ValueError("An order needs between 1 and 100 product lines.")
        seen, items = set(), []
        for line in lines:
            product = self.get_product(line["product_id"])
            if product["id"] in seen:
                raise ValueError("Each product can appear only once. Edit its quantity instead.")
            seen.add(product["id"])
            qty = whole_number(line["quantity"], "Quantity", 1)
            price = price_to_paise(line["price"])
            items.append((product, qty, price))
        return items

    @staticmethod
    def order_number(order):
        return f"{'PO' if order['kind'] == 'PURCHASE' else 'SO'}-{order['id']:05d}"

    def create_order(self, kind, partner, lines, supplier_id=None, note=""):
        self.require(admin=(kind == "PURCHASE"))
        if kind not in ("PURCHASE", "SALE"):
            raise ValueError("Unknown order type.")
        if len(note) > 200:
            raise ValueError("Order note must be 200 characters or fewer.")
        with self.connection:
            self.connection.execute("BEGIN IMMEDIATE")
            if kind == "PURCHASE":
                supplier = self.connection.execute("SELECT name FROM suppliers WHERE id=?", (supplier_id,)).fetchone()
                if supplier is None:
                    raise ValueError("Select a supplier first.")
                partner = supplier[0]
            else:
                supplier_id = None
                partner = required_text(partner, "Customer name")
            items = self._validate_lines(lines)
            total = sum(qty * price for p, qty, price in items)
            status = "PENDING" if kind == "PURCHASE" else "COMPLETED"
            order_id = self.connection.execute("""
                INSERT INTO orders(kind,partner,supplier_id,status,total_paise,note,created_by)
                VALUES(?,?,?,?,?,?,?)
            """, (kind, partner, supplier_id, status, total, note.strip(), self.user["id"])).lastrowid
            for p, qty, price in items:
                self.connection.execute("""
                    INSERT INTO order_items(order_id,product_id,sku,product_name,quantity,price_paise)
                    VALUES(?,?,?,?,?,?)
                """, (order_id, p["id"], p["sku"], p["name"], qty, price))
                if kind == "SALE":
                    balance = p["quantity"] - qty
                    if balance < 0:
                        raise ValueError(f"{p['name']}: only {p['quantity']} units available.")
                    self.connection.execute("UPDATE products SET quantity=? WHERE id=?", (balance, p["id"]))
                    self._movement(p["id"], p["sku"], p["name"], "OUT", qty, balance, f"Sale SO-{order_id:05d} / {partner}"[:200])
            if kind == "SALE":
                self.connection.execute("UPDATE orders SET completed_at=datetime('now','localtime') WHERE id=?", (order_id,))
            self._log("PURCHASE CREATED" if kind == "PURCHASE" else "SALE RECORDED", f"{'PO' if kind == 'PURCHASE' else 'SO'}-{order_id:05d} / {partner}")
        return order_id

    def orders(self, kind):
        self.require()
        return self.connection.execute("SELECT * FROM orders WHERE kind=? ORDER BY id DESC", (kind,)).fetchall()

    def order_details(self, order_id):
        self.require()
        order = self.connection.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
        if order is None:
            raise ValueError("Order not found.")
        items = self.connection.execute("SELECT * FROM order_items WHERE order_id=? ORDER BY id", (order_id,)).fetchall()
        return order, items

    def receive_purchase(self, order_id):
        self.require(admin=True)
        with self.connection:
            self.connection.execute("BEGIN IMMEDIATE")
            order, items = self.order_details(order_id)
            if order["kind"] != "PURCHASE" or order["status"] != "PENDING":
                raise ValueError("Only a pending purchase can be received, once.")
            for item in items:
                p = self.get_product(item["product_id"])
                balance = p["quantity"] + item["quantity"]
                if balance > 1_000_000:
                    raise ValueError(f"Receiving this order would exceed the quantity limit for {p['name']}.")
                self.connection.execute("UPDATE products SET quantity=? WHERE id=?", (balance, p["id"]))
                self._movement(p["id"], p["sku"], p["name"], "IN", item["quantity"], balance, f"Received PO-{order_id:05d}")
            self.connection.execute("UPDATE orders SET status='COMPLETED',completed_at=datetime('now','localtime') WHERE id=?", (order_id,))
            self._log("PURCHASE RECEIVED", f"PO-{order_id:05d} / Stock added")

    def cancel_order(self, order_id):
        self.require(admin=True)
        with self.connection:
            self.connection.execute("BEGIN IMMEDIATE")
            order, items = self.order_details(order_id)
            if order["status"] == "CANCELLED":
                raise ValueError("This order was already cancelled.")
            if order["kind"] == "PURCHASE" and order["status"] != "PENDING":
                raise ValueError("Received purchases cannot be cancelled. Record a stock adjustment if required.")
            if order["kind"] == "SALE":
                for item in items:
                    p = self.connection.execute("SELECT * FROM products WHERE id=?", (item["product_id"],)).fetchone()
                    balance = p["quantity"] + item["quantity"]
                    if balance > 1_000_000:
                        raise ValueError("The reversal would exceed the stock limit.")
                    self.connection.execute("UPDATE products SET quantity=?,active=1 WHERE id=?", (balance, p["id"]))
                    self._movement(p["id"], p["sku"], p["name"], "IN", item["quantity"], balance, f"Voided SO-{order_id:05d}")
            self.connection.execute("UPDATE orders SET status='CANCELLED' WHERE id=?", (order_id,))
            self._log("ORDER CANCELLED", f"{self.order_number(order)} / {'Stock restored' if order['kind']=='SALE' else 'No stock movement'}")

    def business_summary(self):
        self.require()
        return self.connection.execute("""
            SELECT COALESCE(SUM(CASE WHEN kind='SALE' AND status='COMPLETED' THEN total_paise ELSE 0 END),0) sales,
                   COALESCE(SUM(CASE WHEN kind='SALE' AND status='COMPLETED' AND date(created_at)=date('now','localtime') THEN total_paise ELSE 0 END),0) today_sales,
                   COALESCE(SUM(kind='PURCHASE' AND status='PENDING'),0) pending,
                   COALESCE(SUM(kind='SALE' AND status='COMPLETED'),0) sales_count
            FROM orders
        """).fetchone()

    def weekly_sales(self):
        self.require()
        totals = {r[0]: r[1] for r in self.connection.execute("""
            SELECT date(created_at),SUM(total_paise) FROM orders
            WHERE kind='SALE' AND status='COMPLETED' GROUP BY date(created_at)
        """)}
        days = [date.today() - timedelta(days=i) for i in range(6, -1, -1)]
        return [(day.strftime("%a"), totals.get(day.isoformat(), 0)) for day in days]

    def database_info(self):
        self.require(admin=True)
        names = ["products", "movements", "users", "suppliers", "orders", "order_items", "activity"]
        return [(name, self.connection.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]) for name in names]

    def backup(self, destination):
        self.require(admin=True)
        return super().backup(destination)

    def load_demo(self):
        self.require(admin=True)
        super().load_demo()
        existing = {s["name"].lower(): s["id"] for s in self.suppliers()}
        supplier_ids = [existing.get(name.lower()) or self.save_supplier(name, contact) for name, contact in
                        [("Campus Tech", "Sales desk"), ("Paper House", "Orders team"), ("Everyday Supplies", "Customer care")]]
        products = {p["sku"]: p for p in self.products()}
        self.create_order("SALE", "Campus Lab", [
            {"product_id": products["EL-101"]["id"], "quantity": 2, "price": "599"},
            {"product_id": products["ST-101"]["id"], "quantity": 5, "price": "85"}], note="Sample sale")
        self.create_order("PURCHASE", "", [{"product_id": products["EL-102"]["id"], "quantity": 20, "price": "180"}], supplier_id=supplier_ids[0], note="Sample restock order")

    def receipt_text(self, order_id):
        order, items = self.order_details(order_id)
        title = "PURCHASE ORDER" if order["kind"] == "PURCHASE" else "SALES RECEIPT"
        lines = ["DOOMSDAY INVENTORY", title, self.order_number(order),
                 f"Date: {order['created_at']}", f"Status: {order['status']}",
                 f"{'Supplier' if order['kind']=='PURCHASE' else 'Customer'}: {order['partner']}", ""]
        for item in items:
            lines.append(f"{item['sku']} - {item['product_name']}")
            lines.append(f"  {item['quantity']} x INR {item['price_paise']/100:.2f} = INR {item['quantity']*item['price_paise']/100:.2f}")
        lines.extend(["", f"TOTAL: INR {order['total_paise']/100:,.2f}", f"Note: {order['note']}",
                      "", "Academic project receipt. No tax calculation included."])
        return "\n".join(lines)

    def archived_products(self, search=""):
        self.require(admin=True)
        rows = self.connection.execute("SELECT * FROM products WHERE active=0 ORDER BY name COLLATE NOCASE").fetchall()
        term = search.strip().lower()
        return [row for row in rows if term in (row["sku"] + " " + row["name"]).lower()]

    def restore_product(self, product_id):
        self.require(admin=True)
        with self.connection:
            self.connection.execute("BEGIN IMMEDIATE")
            row = self.connection.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
            if row is None or row["active"]:
                raise ValueError("Select a product that is currently archived.")
            self.connection.execute("UPDATE products SET active=1 WHERE id=?", (product_id,))
            self._log("PRODUCT RESTORED", f"{row['sku']} / {row['name']}")

    def validate_import_rows(self, rows):
        self.require(admin=True)
        if not 1 <= len(rows) <= 2000:
            raise ValueError("Import between 1 and 2,000 product rows.")
        existing = {r[0].upper() for r in self.connection.execute("SELECT sku FROM products")}
        seen, results = {}, []
        for index, row in enumerate(rows):
            values = {key: str(row.get("values", {}).get(key, "")).strip() for key in CSV_COLUMNS}
            errors = list(row.get("file_errors", []))
            parsed = {}
            for key, label, limit in [("sku", "SKU", 30), ("name", "Product name", 100), ("category", "Category", 50)]:
                try:
                    parsed[key] = required_text(values[key], label, limit)
                except ValueError as error:
                    errors.append(str(error))
            parsed["supplier"] = values["supplier"]
            if len(values["supplier"]) > 100:
                errors.append("Supplier must be 100 characters or fewer.")
            for key, label in [("quantity", "Quantity"), ("reorder_level", "Reorder level")]:
                try:
                    parsed[key] = whole_number(values[key], label)
                except ValueError as error:
                    errors.append(str(error))
            try:
                parsed["price_paise"] = price_to_paise(values["price"])
            except ValueError as error:
                errors.append(str(error))
            sku = values["sku"].upper()
            parsed["sku"] = sku
            if sku in existing:
                errors.append("SKU already exists in active or archived products.")
            result = {"row": row.get("row", index + 2), "values": values,
                      "file_errors": list(row.get("file_errors", [])), "errors": errors, "parsed": parsed}
            if sku:
                if sku in seen:
                    first = seen[sku]
                    errors.append(f"Duplicate SKU in this file (also row {first['row']}).")
                    if not any(e.startswith("Duplicate SKU") for e in first["errors"]):
                        first["errors"].append(f"Duplicate SKU in this file (also row {result['row']}).")
                else:
                    seen[sku] = result
            results.append(result)
        return results

    def preview_product_import(self, path):
        self.require(admin=True)
        return self.validate_import_rows(read_product_csv(path))

    def import_products(self, rows):
        self.require(admin=True)
        with self.connection:
            self.connection.execute("BEGIN IMMEDIATE")
            # Revalidate the preview snapshot against current database records.
            checked = self.validate_import_rows(rows)
            bad = [r for r in checked if r["errors"]]
            if bad:
                first = bad[0]
                raise ValueError(f"Nothing was imported. Row {first['row']}: {' '.join(first['errors'])}")
            for row in checked:
                p = row["parsed"]
                cursor = self.connection.execute("""
                    INSERT INTO products(sku,name,category,supplier,price_paise,quantity,reorder_level)
                    VALUES(?,?,?,?,?,?,?)
                """, tuple(p[key] for key in ("sku", "name", "category", "supplier", "price_paise", "quantity", "reorder_level")))
                if p["quantity"]:
                    self._movement(cursor.lastrowid, p["sku"], p["name"], "OPENING", p["quantity"], p["quantity"], "Opening stock from CSV import")
            self._log("CSV IMPORTED", f"Added {len(checked)} products with validated opening stock")
        return len(checked)

    @staticmethod
    def report_dates(start, end):
        try:
            first, last = date.fromisoformat(start), date.fromisoformat(end)
            if first.isoformat() != start or last.isoformat() != end:
                raise ValueError()
        except (ValueError, TypeError):
            raise ValueError("Enter both dates as YYYY-MM-DD, for example 2026-11-01.") from None
        if first > last:
            raise ValueError("From date must be on or before To date.")
        return start, end

    def sales_report(self, start, end):
        self.require()
        start, end = self.report_dates(start, end)
        orders = self.connection.execute("""
            SELECT * FROM orders WHERE kind='SALE' AND status='COMPLETED'
            AND date(created_at) BETWEEN ? AND ? ORDER BY created_at DESC,id DESC
        """, (start, end)).fetchall()
        products = self.connection.execute("""
            SELECT p.id,p.sku,p.name,SUM(i.quantity) AS units,
                   SUM(i.quantity*i.price_paise) AS revenue,COUNT(DISTINCT o.id) AS order_count
            FROM order_items i JOIN orders o ON i.order_id=o.id JOIN products p ON p.id=i.product_id
            WHERE o.kind='SALE' AND o.status='COMPLETED' AND date(o.created_at) BETWEEN ? AND ?
            GROUP BY p.id,p.sku,p.name ORDER BY units DESC,revenue DESC,p.id
        """, (start, end)).fetchall()
        return {"start": start, "end": end, "orders": orders, "products": products,
                "sales": sum(r["total_paise"] for r in orders), "order_count": len(orders),
                "units": sum(r["units"] for r in products)}

    def export_sales_report(self, path, start, end):
        report = self.sales_report(start, end)
        with open(path, "w", newline="", encoding="utf-8-sig") as file:
            writer = csv.writer(file)
            writer.writerow(["Doomsday sales report", "From", start, "To (inclusive)", end])
            writer.writerow(["Sales INR", f"{report['sales']/100:.2f}", "Completed orders", report["order_count"], "Units sold", report["units"]])
            writer.writerow([])
            writer.writerow(["SKU", "Product (current name)", "Units sold", "Sales INR", "Order count"])
            for p in report["products"]:
                writer.writerow([csv_safe(p["sku"]), csv_safe(p["name"]), p["units"], f"{p['revenue']/100:.2f}", p["order_count"]])
            writer.writerow([])
            writer.writerow(["Order", "Date", "Customer", "Total INR"])
            for order in report["orders"]:
                writer.writerow([self.order_number(order), order["created_at"], csv_safe(order["partner"]), f"{order['total_paise']/100:.2f}"])
