"""Read-only database summary for learning and demonstrations."""
import argparse
import sqlite3
from pathlib import Path


def inspect_database(path):
    path = Path(path).resolve()
    if not path.is_file():
        raise ValueError('Database not found. Run main.py once, or choose an existing file with --db.')
    connection = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)
    try:
        print('DOOMSDAY DATABASE INSPECTION (READ ONLY)')
        print('Database:', path)
        print('Integrity:', connection.execute('PRAGMA integrity_check').fetchone()[0])
        print('Foreign-key problems:', len(connection.execute('PRAGMA foreign_key_check').fetchall()))
        print('\nApplication tables and record counts:')
        tables = ['products', 'movements', 'users', 'suppliers', 'orders', 'order_items', 'activity']
        for table in tables:
            count = connection.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
            print(f'  {table}: {count}')
        print('\nFirst five products:')
        for sku, name, quantity, active in connection.execute('SELECT sku,name,quantity,active FROM products ORDER BY id LIMIT 5'):
            print(f'  {sku} | {name} | quantity={quantity} | {"active" if active else "archived"}')
        print('\nAccount passwords, hashes and salts are not displayed.')
    finally:
        connection.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Inspect Doomsday inventory records without changing them.')
    parser.add_argument('--db', default=str(Path(__file__).resolve().parent / 'data' / 'inventory.db'))
    args = parser.parse_args()
    try:
        inspect_database(args.db)
    except (ValueError, sqlite3.Error, OSError) as error:
        parser.exit(1, f'Could not inspect database: {error}\n')
