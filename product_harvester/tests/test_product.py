from unittest import TestCase

from pydantic import ValidationError

from product_harvester.product import Product


class TestProduct(TestCase):
    def test_ok(self):
        Product(name="Banana", qty=1.5, qty_unit="kg", price=1, barcode="123", brand="", tags=[])
        Product(name="Banana", qty=1.5, qty_unit="kg", price=1, barcode="123")
        Product(name="Milk", qty=1000, qty_unit="ml", price=10, barcode="abc", brand="Rajo")
        Product(name="Kiwi", qty=3, qty_unit="pcs", price=10.54, barcode="abc", tags=["milk", "yogurt"])

    def test_empty(self):
        with self.assertRaises(ValidationError):
            Product()

    def test_empty_name(self):
        with self.assertRaises(ValidationError):
            Product(name="", qty=10, qty_unit="kg", price=10, barcode="123", brand="", tags=[])

    def test_invalid_qty(self):
        with self.assertRaises(ValidationError):
            Product(name="Banana", qty=0, qty_unit="kg", price=10, barcode="123", brand="", tags=[])
        with self.assertRaises(ValidationError):
            Product(name="Banana", qty=-2, qty_unit="kg", price=10, barcode="123", brand="", tags=[])

    def test_invalid_qty_unit(self):
        with self.assertRaises(ValidationError):
            Product(name="Banana", qty=10, qty_unit="", price=10, barcode="123", brand="", tags=[])
        with self.assertRaises(ValidationError):
            Product(name="Banana", qty=10, qty_unit="wat", price=10, barcode="123", brand="", tags=[])

    def test_invalid_price(self):
        with self.assertRaises(ValidationError):
            Product(name="Banana", qty=10, qty_unit="kg", price=0, barcode="123", brand="", tags=[])
        with self.assertRaises(ValidationError):
            Product(name="Banana", qty=10, qty_unit="kg", price=-2, barcode="123", brand="", tags=[])

    def test_empty_barcode(self):
        with self.assertRaises(ValidationError):
            Product(name="Banana", qty=10, qty_unit="kg", price=10, barcode="", brand="", tags=[])
