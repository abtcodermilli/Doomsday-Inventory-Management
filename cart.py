"""Editable order draft. Changes stay in memory until the order is submitted."""
from database import whole_number, price_to_paise


class OrderCart:
    def __init__(self, service, kind):
        if kind not in ("SALE", "PURCHASE"):
            raise ValueError("Unknown order type.")
        self.service, self.kind = service, kind
        self.items = []

    def _validated(self, product_id, quantity, price):
        product = self.service.get_product(product_id)
        quantity = whole_number(quantity, "Quantity", 1)
        cents = price_to_paise(price)
        if self.kind == "SALE" and quantity > product["quantity"]:
            raise ValueError(f"{product['name']}: only {product['quantity']} units available.")
        return {"product_id": product_id, "quantity": quantity, "price": f"{cents / 100:.2f}"}

    def add(self, product_id, quantity, price):
        if any(item["product_id"] == product_id for item in self.items):
            raise ValueError("This product is already in the cart. Edit its quantity or price in the table.")
        self.items.append(self._validated(product_id, quantity, price))

    def update(self, product_id, quantity, price):
        for index, item in enumerate(self.items):
            if item["product_id"] == product_id:
                self.items[index] = self._validated(product_id, quantity, price)
                return
        raise ValueError("Select a cart item first.")

    def remove(self, product_id):
        self.items[:] = [item for item in self.items if item["product_id"] != product_id]

    @property
    def total_paise(self):
        return sum(item["quantity"] * price_to_paise(item["price"]) for item in self.items)
