# Doomsday v3 — Classroom demonstration

Use a practice database. The sample records below are fictional demonstration data.
Create your Admin account with sample data enabled. Read `PROJECT_GUIDE.md` before
presenting so you can explain the choices and follow your course's attribution rules.

## 1. Show the interface and team

- Open Dashboard, then Our Team.
- Show the blue-and-white design, charts, three names and registration numbers.
- Explain that Tkinter handles the interface and Python services handle database operations.

## 2. Prove that a sale really changes the database

- Add product DEMO-01, name Demo Notebook, price INR 50, opening stock 10, reorder level 2.
- Record a sale for 3 units. Show the receipt total of INR 150 and remaining stock 7.
- Try to sell 20 units. Show the error; no new completed sale should exist.
- Open History and Activity to show the accepted movement and logged action.
- Close and reopen the app. Sign in and show that stock remains 7.

What to explain: the backend validates stock, writes the order and its items,
updates quantity, and logs the movement in one transaction. A failed sale rolls back.

## 3. Demonstrate a useful file import

- Products → Import CSV → Choose CSV → `examples/products_invalid.csv`.
- Show the missing name, negative quantity, duplicate SKU and invalid price.
- Select an invalid row to read all its errors. The import action is disabled.
- Choose `examples/products_valid.csv`. Show all three rows as ready.
- Confirm the import, search IMP-101, and show its stock and opening history.
- Try importing the same file again. Existing SKUs are rejected.

What to explain: preview is read-only; import revalidates against current database
records and saves every row together. It does not overwrite products or skip errors.

## 4. Edit the order cart

- Create another sale for DEMO-01, initially quantity 1 at INR 50.
- Double-click its Qty cell, enter 2, and press Enter. The total becomes INR 100.
- Double-click its Price cell, enter 45, and press Enter. The total becomes INR 90.
- Complete the sale. Show remaining stock 5 and the saved line price of INR 45.

What to explain: cart edits are held in memory. Saving the order rechecks available
stock in the database. Prices are stored as integer paise, so totals remain exact.

## 5. Show a date-filtered business report

- Reports → Sales analytics → Today.
- Show completed sales value, order count, units sold and best-selling products.
- Enter a date before any records existed and apply it. Show the empty result.
- Return to Today and export the report to CSV.
- Optionally void one sale as Admin and rerun the report to show its exclusion.

What to explain: dates include both endpoints. SQL filters completed sales, joins
order items to products, groups by product, and sums quantities and historical prices.
Order totals are calculated separately to avoid double-counting multi-item orders.

## 6. Archive and restore without losing history

- The sample Water Bottle starts at zero stock. Archive it from Products.
- Open Archived products, search AC-102 and restore it.
- Show the same SKU, zero stock, original product ID and a new Activity event.
- If that product has since received stock, use another zero-stock demo product.

What to explain: archiving sets `active=0`; restoring sets `active=1`. It does not
create a second product or manufacture an additional stock movement.

## 7. Show permissions and actual database records

- Accounts → Add account: create a Staff account, then sign out and sign in as Staff.
- Show Sales and Reports, and the absence of Admin-only purchase/import/restore actions.
- Sign back in as Admin and show table counts on Accounts.
- In a terminal in the project folder, run:

```bash
python3 inspect_database.py
python3 -m unittest discover -s tests -v
```

The first command reads the database without modifying it. The second runs 46 tests
using temporary databases. Your actual inventory is not changed by these tests.

## Be ready to explain a small code change

Trace these functions before your presentation:

- `sales_report()` in services.py: date checks, SQL queries and grouped totals.
- `validate_import_rows()` / `import_products()`: preview validation and atomic writes.
- `restore_product()`: the same row is reactivated and an action is logged.
- `OrderCart.update()` in cart.py: validate a replacement line before changing it.

As an optional practice exercise, add a category filter to the best-seller report.
Decide whether its summary cards represent the selected category or all sales, label
that choice clearly, and add a test with two categories. This is intentionally a
learning exercise; the supplied report filters by date and includes all categories.
