# Doomsday Inventory & Operations — Version 3

A Python desktop project with a blue-and-white Tkinter frontend and a persistent
SQLite backend. Version 3 adds date-filtered sales reports, validated CSV imports, archive restoration
and editable order carts, alongside accounts, suppliers, purchases, sales and receipts.

## Team

| Name | Registration number |
|---|---|
| Aditya Malik | RA2511003012354 |
| Shashank Singh Solanki | RA2511003012371 |
| Ankur Bikram Thapa | RA2511003012373 |

## Start on your Mac

1. Extract the ZIP into a writable folder.
2. Open the extracted **Doomsday_Inventory** folder in VS Code.
3. Open **Terminal → New Terminal**.
4. Run:

   ```bash
   python3 main.py
   ```

5. On the first launch, create your administrator account. Choose your own username
   and a password of at least eight characters. There is no preset password.
6. Keep **Start with sample products and orders** selected for your demonstration,
   or uncheck it to start empty.
7. On subsequent launches, sign in with the account you created.

Python 3.10 or newer with Tkinter is required. There are no pip dependencies.
To check Tkinter, run `python3 -m tkinter`; it should open a small test window.
If Tkinter is missing, use a Python installation with Tcl/Tk support, such as the
[official Python macOS installer](https://www.python.org/downloads/macos/).
Do not run `pip install tkinter`.

On Windows use `py main.py` or `python main.py`. On Linux use `python3 main.py`
from a desktop session with Tkinter installed. The app requires a graphical display.

## Upgrading from versions 1 or 2

Extract version 3 into a NEW folder and keep the old project/database as a backup.
This ZIP includes an EMPTY starter `data/inventory.db`. To retain your records,
copy your old `data/inventory.db` OVER that starter file before first launch.
Do not extract this ZIP directly over your only working copy of the project.

Existing products, movements, accounts and orders remain intact. Version 1 users
are asked to create their first administrator; version 2 users sign in normally.
The application creates any missing tables/indexes automatically.

## Frontend and backend

| File | Responsibility |
|---|---|
| `main.py` | Login screen, navigation, dashboard, product and stock pages |
| `workflows.py` | Supplier, purchase, sale, receipt, activity and account screens |
| `enhancements.py` | Date reports, CSV preview/import and archive restoration screens |
| `cart.py` | Validated in-memory cart with quantity/price editing |
| `import_utils.py` | CSV reader and downloadable template |
| `inspect_database.py` | Read-only database inspection for demonstrations |
| `widgets.py` | Reusable cards, navigation icons and Canvas illustrations |
| `services.py` | Login, permissions, suppliers, order transactions and activity |
| `database.py` | SQLite tables, product CRUD, stock movements, validation and exports |
| `data/inventory.db` | Included empty SQLite database with all seven application tables |
| `tests/` | 46 automated backend tests |
| `PROJECT_GUIDE.md` | Data flow, database design, demo steps and viva answers |
| `DATABASE_GUIDE.md` | Database connections, relationships and preservation |
| `DEMO_CHECKLIST.md` | Classroom walkthrough and learning exercise |
| `examples/` | Valid and deliberately invalid product-import CSV files |
| `screenshots/` | Actual application previews using sample data |

The backend is real application logic and storage, not a separate window or web
server. Tkinter calls Python backend methods, which validate data and execute SQL
against SQLite. No HTML, CSS, JavaScript, MySQL server or network service is needed.

## Features

- **Dashboard:** inventory value, sales today, low-stock count, open purchases,
  seven-day sales chart, stock by category and a restock watchlist.
- **Products:** add/edit/archive products, search, category filter, low-stock filter
  CSV import/export and an Archived products screen. Stock quantities are changed through stock movements or orders.
- **Sales:** multi-product sale cart, customer name, item prices, automatic stock
  deduction, saved receipts and CSV export. Double-click cart Qty/Price cells to edit them.
  Press Enter to apply an edit or Escape to cancel it.
- **Purchasing:** multi-product purchase orders linked to suppliers; pending,
  completed and cancelled statuses; receive a purchase to add its stock.
- **Suppliers:** save and edit names, contact people, phone numbers and emails.
- **Stock In / Out:** manual adjustments for returns, damage, usage or deliveries
  that are not part of a purchase order.
- **History:** permanent opening-stock, stock-in and stock-out records.
- **Reports:** date-filtered sales totals, completed order count, units sold, best-selling
  products and CSV export. The Inventory & backups tab keeps category totals, stock
  exports, history exports and database backups together.
- **Activity:** recent account, product, supplier and order actions with user names
  and timestamps. The screen shows the latest 500 events.
- **Accounts:** administrator-managed user creation and password changes. Admins can
  inspect the seven database tables and their row counts on this page.
- **Our Team:** all three team members and their registration numbers.

## Account permissions

| Action | Admin | Staff |
|---|---|---|
| View inventory, dashboard, history and activity | Yes | Yes |
| Record sales and export receipts/reports | Yes | Yes |
| Change own password | Yes | Yes |
| Add/edit/archive/restore products, import CSV or adjust stock manually | Yes | No |
| Manage suppliers and purchase orders | Yes | No |
| Void sales | Yes | No |
| Add users and inspect database counts | Yes | No |
| Export complete database backup | Yes | No |

Passwords are stored as salted PBKDF2-HMAC-SHA256 hashes, with 600,000 iterations.
The normal application workflow enforces role checks in the Python backend as well
as hiding unavailable screens/actions. This is a local academic application: anyone
who can directly edit the Python files or database can bypass those controls.
There is no email-based password recovery or remote authentication service.

## Important workflow rules

**Purchases:** Creating an order saves a pending record without changing stock.
**Receive selected** adds all its quantities and marks it completed in one database
transaction. It cannot be received twice. Only pending purchases can be cancelled.
Purchase unit costs do not overwrite product selling prices.

**Sales:** Completing a sale saves the order and its items, subtracts all quantities,
and records stock history in one transaction. If any item has insufficient stock,
the entire sale is rolled back. **Void sale** restores stock once and excludes the
sale from revenue totals. A previously archived product is reactivated if voiding a
sale restores its stock.

**Products:** SKU values are unique, including archived products. Archive only when
stock is zero and no pending purchase references the product. Admins can restore a
product from Products → Archived products, keeping its original ID and quantity.
Transaction records keep product name/SKU snapshots.

**Figures:** Prices are in INR and stored as integer paise. Inventory value uses the
current product price, not purchase cost. Sales values are completed, non-voided
order totals; they are not profit or collected payment amounts. No taxes, discounts,
refund payments or cost-of-goods accounting are calculated. The category chart shows
the first three categories by inventory value; Reports lists all categories.

## Where data is saved

All records are saved automatically to `data/inventory.db` next to the source files.
Closing and reopening the app preserves them. All timestamps and dashboard days use
the computer's local clock.

**Backup:** As an Admin, choose **Reports → Inventory & backups → Backup database**.

**Restore:** Close the application, keep a copy of your current database, then copy
the backup into `data` and name that copy `inventory.db`. Restart the application.
Accounts and passwords revert to the state included in that backup.

For a clean demo, close the app and move the whole `data` folder somewhere safe.
The next launch creates a fresh database and setup screen. Do not delete your
working database just to reset a password.

## Using the new features

**Date reports:** Open Reports → Sales analytics. Enter From/To as YYYY-MM-DD and
click Apply dates, or use Today / Last 7 days / This month. Both endpoints are included.
The report includes only currently completed sales. Voided sales are excluded. Export
report saves the period, totals, best sellers and matching sale headers in one CSV.
These reports reflect the current status of historical orders, not an as-of snapshot.

**CSV import:** Products → Import CSV → Choose CSV. Try `examples/products_invalid.csv`
to see validation errors, then `examples/products_valid.csv` for a successful import.
Select a row to see all its errors. Download template saves an editable CSV locally.
All rows must be valid before import. Limits: 2 MB, 2,000 product rows. No existing
product is overwritten. A duplicate SKU, including an archived one, blocks import.

Required columns: `sku,name,category,price,quantity,reorder_level`. `supplier` is
optional. Exported inventory header labels are also understood. Extra columns are
ignored, but row field counts must match the header. Use a UTF-8 comma-separated CSV.
Product price/quantity errors are reported by CSV line number; blank rows are skipped.
A preview does not save records. A confirmed import saves products, nonzero opening
stock movements and its activity event together, or rolls everything back.

**Cart editing:** Before completing a sale or purchase, double-click its Qty or Price
cell. Type the new value and press Enter. Totals update after each accepted edit.
Escape cancels the active edit. Invalid edits leave the saved cart item unchanged.
Completing an order also validates any active editor and rechecks current stock.
Cart drafts are in memory and are discarded if their window is closed.

**Archive restoration:** Products → Archived products → select a row → Restore
selected. This reactivates the same record and logs the action; it does not create
new stock or remove history.

**Inspect the actual database:** Run `python3 inspect_database.py`. See
`DATABASE_GUIDE.md` and `DEMO_CHECKLIST.md` for the presentation walkthrough.

## Validation and testing

Run from the project folder:

```bash
python3 -m unittest discover -s tests -v
```

All **46 backend tests** passed. They cover product storage, validation, CSV safety,
backups, migration from version 1, password hashing, login, role permissions, order
rollback, duplicate-receipt prevention, cancellation, stock restoration and receipts.
New tests cover inclusive report dates, multi-item order totals, import validation and
rollback, stale previews, archived-product restoration and cart editing.
Tests use temporary databases and do not alter your real inventory.

GUI checks exercised setup/login, all 11 Admin pages, the supplier form, multi-item
sale form and receipt, purchase creation, receiving, account creation and Staff login.
Version 3 checks also exercised invalid/valid import previews, import commits, archive
restoration, inline cart editing, report date filters and report CSV exports.
Screens were checked at 1280 x 850 and 1120 x 780. The dashboard scrolls on smaller
windows. Verification ran on Linux with Python 3.12 and a virtual display; physical
macOS/Windows testing has not been performed. Native rendering can differ slightly.

## Project scope

This is a single-computer student project. It has no cloud sync, separate customer
master table, tax invoicing, payment processing, barcode hardware integration or
networked multi-user deployment. It supports full-order receiving and full-sale
voiding; partial receiving and partial returns are future work. Suppliers cannot be
deleted, preserving historical order references. Users can be added and change their
own password; user deactivation and administrator password resets are future work.

Official references: [Tkinter](https://docs.python.org/3/library/tkinter.html),
[sqlite3](https://docs.python.org/3/library/sqlite3.html),
[hashlib](https://docs.python.org/3/library/hashlib.html).
