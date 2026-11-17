# The database included in this project

`data/inventory.db` is a real SQLite database supplied with all seven application
tables and no accounts or inventory records. First launch creates your own Admin
account and optionally adds sample products, suppliers and orders. No MySQL
installation, credentials or remote database service is required.

When upgrading, extract this package into a NEW folder. Copy your previous database
over this package's empty starter database before running it. Do not extract the
starter database over your only copy of an existing inventory database.

## Where each action is stored

- Adding a product creates a `products` row. Nonzero opening stock also creates a
  `movements` row. Admin actions are recorded in `activity`.
- CSV import adds all product rows, opening movements and one import activity event
  in a single transaction. It creates no new tables.
- Archiving/restoring changes `products.active`, preserving the primary key and
  historical foreign-key references. Restoration adds an activity event.
- A purchase or sale creates an `orders` header and one or more `order_items` rows.
- Receiving a purchase increases `products.quantity`, adds `movements`, updates
  `orders.status` and inserts `activity` together.
- Completing a sale decreases stock while saving its header, items, movements and
  activity together. A failed line rolls back the entire sale.
- Reports read existing records. They do not create duplicate sales or summary rows.
- Local account credentials are stored in `users` as salted password hashes.
- Supplier contacts live in `suppliers`; purchases reference their IDs.

## Relationships to explain

One user can create many orders and activity events. One supplier can have many
purchase orders. One order has many order items. Each order item points to one product.
One product can have many stock movements and can be sold in many orders.

The `products`, `users`, `suppliers` and `orders` IDs are primary keys in their own
tables. Foreign keys connect the related records. There are seven application tables
plus SQLite's own internal metadata. Indexes speed up common lookups.

## Read-only inspection

From the project folder:

```bash
python3 inspect_database.py
```

This prints the database path, integrity result, foreign-key consistency, all seven
table counts, and the first five products. It deliberately omits account hashes and
salts. The script uses SQLite's `mode=ro` connection flag and cannot create a missing
database or write changes.

Inspect a backup without changing it:

```bash
python3 inspect_database.py --db /path/to/your/backup.db
```

The app's Accounts page also shows record counts for Admin users. It is useful for
showing that creating a sale updates multiple related tables.

## A report query worth understanding

The best-seller query joins `order_items`, `orders` and `products`. It filters
`kind='SALE'`, `status='COMPLETED'` and dates between the selected endpoints. It groups
by product ID, then calculates total units, line revenue and distinct order count.

Historical line prices come from `order_items.price_paise`, not the current catalogue
price. Current product names/SKUs label the report, including products later archived.
Receipts keep the original name/SKU snapshots stored on each order item.

The total sales value is summed from order headers separately. Summing header totals
after joining a multi-item order would incorrectly repeat that total for each item.
The tests cover this case.

## Preservation and limits

All mutations save automatically. Back up through Reports → Inventory & backups.
Restore a database backup only while the application is closed. A backup includes
accounts, inventory, orders and history at its creation time.

CSV imports accept up to 2,000 nonempty product rows and a file size up to 2 MB. They
require unique SKUs and reject duplicates against active AND archived products.
Imports use the reviewed in-memory snapshot, then revalidate it while holding the
write transaction, so later file changes cannot silently alter the reviewed values.

This is a local academic application. Application permissions do not protect against
someone who directly changes the Python source or database file. Backups contain the
entire local database, including account hashes, and should be treated accordingly.
