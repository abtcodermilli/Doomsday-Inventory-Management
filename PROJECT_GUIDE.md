# Doomsday Inventory & Operations — Project Guide

## Aim

Develop a Python desktop application that manages products, suppliers, purchasing,
sales and stock movements with a Tkinter interface and persistent SQLite database.

## Team

| Name | Registration number |
|---|---|
| Aditya Malik | RA2511003012354 |
| Shashank Singh Solanki | RA2511003012371 |
| Ankur Bikram Thapa | RA2511003012373 |

## What is the backend in this project?

The backend is the logic behind the buttons. It checks credentials, validates input,
checks permissions, calculates totals, updates inventory and saves records. It does
not need to run on a website or remote server to be a backend.

Example: clicking **Complete sale** in `workflows.py` calls
`InventoryService.create_order()` in `services.py`. The method checks the logged-in
user, reads product quantities, creates the sale and its item rows, reduces stock,
adds stock-movement rows and records an activity event. SQLite persists the changes.

The whole sale is one transaction. If a second item is unavailable, the first item's
quantity change and all new sale rows are rolled back too.

## Application layers

| Layer | Files | Main responsibilities |
|---|---|---|
| Presentation | `main.py`, `workflows.py`, `widgets.py` | Widgets, forms, tables, charts, navigation |
| Business logic | `services.py` | Accounts, permissions, suppliers, orders, receipts and activity |
| Data access | `database.py` | Connections, queries, products, stock and exports |
| Persistence | `data/inventory.db` | Durable SQLite records |

`InventoryService` extends `Database`, reusing the product/stock methods and adding
workflow rules. `InventoryApp` combines the Tkinter root window and a screen mixin
called `WorkflowViews`, plus `EnhancementViews` for CSV import, reports and archive
recovery. These mixins group related screens; they share the same backend instance.
`OrderCart` validates in-memory edits before orders are submitted.

## Seven database tables

| Table | Key columns | Purpose |
|---|---|---|
| products | id, sku, name, category, supplier, price_paise, quantity, reorder_level, active | Active/archived product catalogue |
| movements | id, product_id, sku, product_name, kind, quantity, balance, note, created_at | Opening, incoming and outgoing stock history |
| users | id, username, full_name, salt, password_hash, role | Local Admin/Staff accounts |
| suppliers | id, name, contact, phone, email | Supplier contact records |
| orders | id, kind, partner, supplier_id, status, total_paise, created_by, created_at, completed_at | Purchase and sale headers |
| order_items | id, order_id, product_id, sku, product_name, quantity, price_paise | Multiple items per order |
| activity | id, user_id, action, detail, created_at | Account-linked actions |

Relationships:

- A product has many stock movements and can appear on many order items.
- An order has many items, and each item references one product.
- Purchase orders reference suppliers. Sale customer names are stored in `partner`.
- Orders and activity events reference the user who created them.
- Product `supplier` text is an optional catalogue label; the purchase's `supplier_id`
  is the actual foreign key to the supplier table.

`id` is a primary key. `product_id`, `order_id`, `supplier_id` and `user_id` are foreign
keys where declared in the schema. SQLite foreign-key checking is explicitly enabled.
Unique constraints protect usernames, supplier names, SKUs and product-per-order pairs.

## States and calculations

| Operation | Before | After | Stock effect |
|---|---|---|---|
| Create purchase | No order | PENDING | None |
| Receive purchase | PENDING | COMPLETED | Increase every line quantity |
| Cancel purchase | PENDING | CANCELLED | None |
| Complete sale | No order | COMPLETED | Decrease every line quantity |
| Void sale | COMPLETED | CANCELLED | Restore every line quantity once |

A received purchase cannot be cancelled. A cancelled sale cannot be voided again.
All orders receive readable numbers: `PO-00002`, `SO-00003`, etc. Both kinds share the
same internal order sequence, so each prefix's numbers need not be consecutive.

- Line total = quantity × unit price.
- Order total = sum of all line totals.
- Inventory value = current stock × current product price, summed across products.
- Low stock = quantity less than or equal to reorder level.
- Sales total = completed sales only; cancelled sales are excluded.
- Price storage: INR 49.99 is stored as 4999 paise to keep arithmetic exact.

The application does not calculate profit, tax or payment settlement. Purchase unit
costs are recorded on order lines without replacing the product's selling price.

For the complete version 3 demonstration, including CSV import, cart editing and
archive restoration, follow `DEMO_CHECKLIST.md`. See `DATABASE_GUIDE.md` for the
included starter database and read-only inspection command.

## Demonstration: show the frontend and the real backend

1. Run `python3 main.py` and create an Admin account. Leave sample data selected.
2. Show the dashboard, sidebar icons, blue/white theme, charts and low-stock badges.
3. Open **Our Team** and show all three names and registration numbers.
4. Open **Accounts**. Show the seven table names and current record counts.
5. Open **Suppliers**. Add a supplier with a contact name and email, then edit it.
6. Open **Purchasing → New purchase**. Select Campus Tech. Add USB-C Cable, quantity
   10 and unit cost 180. Create the purchase. Note its order number.
7. Open **Products**. USB-C Cable still has 6 units: pending orders do not change stock.
8. Return to **Purchasing**, select the order you just created, and click
   **Receive selected**. USB-C Cable now has 16 units.
9. Open **Sales → New sale**. Enter a customer, add 3 USB-C Cables at INR 249 and complete
   the sale. The receipt total is INR 747 and inventory becomes 13 units.
10. Try selling 100 USB-C Cables. The app rejects the quantity without changing stock.
11. Open **History** and **Activity**. Show the purchase receipt, sale movement, user
    names and timestamps. Return to **Accounts** to see the updated record counts.
12. Create a Staff account and sign out. Sign in as Staff. Demonstrate that Sales is
    available while purchasing and manual inventory management are unavailable.
13. Sign back in as Admin and save a database backup from **Reports**.
14. Close and reopen the application to show that records persist.

The initial sample data also includes a pending purchase for 20 cables. For the
numbers above, receive only the new 10-unit purchase you created in step 6.

## Functions to understand

| Function | Explanation |
|---|---|
| `mainloop()` | Keeps Tkinter running and processes events |
| `show_page()` | Changes the visible screen using sidebar navigation |
| `product_dialog()` | Collects product details and calls the backend |
| `setup_admin()` | Creates the first administrator on an empty account database |
| `login()` | Looks up the account and verifies the supplied password hash |
| `require()` | Checks sign-in status and Admin permissions |
| `create_order()` | Validates and saves a purchase or sale and its item rows |
| `receive_purchase()` | Receives a pending purchase once and adds stock |
| `cancel_order()` | Cancels a pending purchase or reverses a completed sale |
| `_movement()` | Inserts a stock history row |
| `_log()` | Inserts an account-linked activity event |
| `business_summary()` | Reads completed sales totals and pending purchase count |
| `backup()` | Creates a consistent SQLite backup |

## Viva questions

**1. What is Tkinter?**  
Python's standard interface to the Tcl/Tk GUI toolkit. We use it for desktop windows,
forms and events. ttk supplies themed entries, buttons, tables and scrollbars.

**2. What is your backend?**  
The Python service and database classes. They validate requests, enforce permissions,
process orders and save/query SQLite records.

**3. Why SQLite instead of MySQL?**  
SQLite runs locally and stores the database in one file. It does not require a
separate database server, which keeps this desktop demonstration easy to run.

**4. How do you store passwords?**  
We generate a random salt per account and derive a PBKDF2-HMAC-SHA256 hash. We store
only the salt and hash, not the plain password. Login recomputes the hash and compares it.

**5. What are roles?**  
They are permission groups. Staff can record sales and view reports. Admins can also
manage products, suppliers, purchases, accounts and database backups.

**6. Why check roles in the backend if buttons are hidden?**  
Hiding a button only changes the interface. The backend must also reject a request
that the current role is not allowed to perform.

**7. What is a database transaction?**  
A group of changes committed together. If any part fails, all changes in that group
are rolled back. We use this for stock updates and their associated order records.

**8. How do you prevent overselling?**  
The backend takes a write transaction, reads current stock, and rejects any sale line
that needs more units than available. The whole sale rolls back on an error.

**9. How do you prevent receiving the same order twice?**  
Only PENDING purchases can be received. Receiving updates stock and changes status to
COMPLETED in the same transaction. A later receive attempt is rejected.

**10. Why have separate orders and order_items tables?**  
One order can contain many products. The orders table stores shared details and
order_items stores each product, quantity and unit price.

**11. Why use `?` in SQL?**  
They are parameter placeholders. Data is passed separately from SQL statements so
user input cannot change the intended query structure.

**12. What is soft deletion?**  
Marking a record inactive instead of removing it. Archiving a zero-stock product
preserves its order relationships and history.

**13. Why store snapshot names and prices?**  
An old receipt should still show what was sold and its original price after the
catalogue is edited. Each order item stores those values at the time of the order.

**14. What are the charts based on?**  
Actual database queries: completed sales grouped by day and current stock grouped
by category. No fake growth percentages or invented historical sales are shown.

**15. How did you test it?**  
There are 46 automated tests covering persistence, validation, account permissions,
transaction rollback, receiving/cancellation, receipts, backups and migration. GUI
workflows were also exercised with a virtual display. Physical Mac testing remains.

**16. What are the limitations?**  
It is a local academic project, without payment processing, tax invoices, partial
receiving or cloud sync. Application roles do not stop someone who directly edits
local code/database files. That would need stronger deployment controls.

## Suggested learning split

These are suggested study responsibilities, not claims about who wrote each file:

- Aditya: Tkinter layout, events, forms and reusable widgets.
- Shashank: SQL schema, password verification, role checks and transactions.
- Ankur: purchasing/sales flow, reports, tests and the complete presentation.

Everyone should be able to explain the entire data flow. Follow your course's
requirements for acknowledging assistance and understand the code before presenting.


## Version 3 functions to explain

- `sales_report()`: validates inclusive From/To dates, reads completed sale headers,
  joins items to products, groups best sellers and avoids repeated header totals.
- `preview_product_import()`: reads a UTF-8 CSV and validates rows without saving.
- `validate_import_rows()`: checks required fields, money, whole-number quantities,
  existing SKUs and within-file duplicates. Both duplicate rows are highlighted.
- `import_products()`: starts a write transaction, revalidates the reviewed values,
  and saves product rows, opening movements and an activity event together.
- `restore_product()`: changes `active` back to 1 on the original row and logs it.
- `OrderCart.update()`: validates replacement quantity/price before changing an item;
  failed edits preserve the original cart and no stock changes until order submission.

A useful viva distinction: validation in a form gives early feedback, while validation
in the backend still protects the database if a different form or program calls it.
The cart may show a stock snapshot, but saving the sale reads current stock inside
its transaction. The same principle applies to CSV previews and final imports.
