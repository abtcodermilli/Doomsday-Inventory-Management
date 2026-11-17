"""Read a bounded CSV into plain rows; the service validates and saves them."""
import csv
from pathlib import Path


CSV_COLUMNS = ["sku", "name", "category", "supplier", "price", "quantity", "reorder_level"]
TEMPLATE_ROWS = [
    ["IMP-101", "Sticky Notes", "Stationery", "Paper House", "45.00", "25", "5"],
    ["IMP-102", "HDMI Cable", "Electronics", "Campus Tech", "349.50", "12", "3"],
    ["IMP-103", "Desk Mat", "Accessories", "Everyday Supplies", "299.00", "8", "2"],
]


def write_template(path):
    with open(path, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)
        writer.writerow(CSV_COLUMNS)
        writer.writerows(TEMPLATE_ROWS)


def read_product_csv(path):
    if Path(path).stat().st_size > 2 * 1024 * 1024:
        raise ValueError("Choose a CSV smaller than 2 MB (maximum 2,000 product rows).")
    aliases = {"product": "name", "unit price inr": "price", "reorder level": "reorder_level"}
    try:
        with open(path, newline="", encoding="utf-8-sig") as file:
            reader = csv.reader(file, strict=True)
            header = next(reader, [])
            header = [aliases.get(value.strip().lower(), value.strip().lower()) for value in header]
            if not header:
                raise ValueError("The CSV file is empty. Download the template to get started.")
            if len(header) != len(set(header)):
                raise ValueError("The CSV has duplicate column names.")
            required = set(CSV_COLUMNS) - {"supplier"}
            missing = sorted(required - set(header))
            if missing:
                raise ValueError("Missing columns: " + ", ".join(missing))
            rows = []
            for row in reader:
                if not row or not any(value.strip() for value in row):
                    continue
                rows.append({"row": reader.line_num,
                             "values": dict(zip(header, row)),
                             "file_errors": ["Number of fields does not match the header."] if len(row) != len(header) else []})
                if len(rows) > 2000:
                    raise ValueError("A single import supports at most 2,000 product rows.")
            if not rows:
                raise ValueError("The CSV contains no product rows.")
            return rows
    except (UnicodeError, csv.Error) as error:
        raise ValueError(f"Could not read the CSV. Save it as UTF-8 CSV. Details: {error}") from None
