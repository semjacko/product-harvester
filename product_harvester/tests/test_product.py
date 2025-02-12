from unittest import TestCase

from pydantic import ValidationError

from product_harvester.product import Product


class TestProduct(TestCase):
    def test_ok(self):
        Product(name="Banana", qty=1.5, qty_unit="kg", price=1, barcode=123, brand="", category="fruit")
        Product(name="Banana", qty=1.5, qty_unit="kg", price=1, barcode=123, category="fruit")
        Product(name="Milk", qty=1000, qty_unit="ml", price=10, barcode=456, brand="Rajo", category="milk")
        Product(name="Kiwi", qty=3, qty_unit="pcs", price=10.54, barcode=567, category="fruit")

    def test_empty(self):
        with self.assertRaises(ValidationError):
            Product()

    def test_empty_name(self):
        with self.assertRaises(ValidationError):
            Product(name="", qty=10, qty_unit="kg", price=10, barcode=123, category="something")

    def test_invalid_qty(self):
        with self.assertRaises(ValidationError):
            Product(name="Banana", qty=0, qty_unit="kg", price=10, barcode=123, category="fruit")
        with self.assertRaises(ValidationError):
            Product(name="Banana", qty=-2, qty_unit="kg", price=10, barcode=123, category="fruit")

    def test_invalid_qty_unit(self):
        with self.assertRaises(ValidationError):
            Product(name="Banana", qty=10, qty_unit="", price=10, barcode=123, category="fruit")
        with self.assertRaises(ValidationError):
            Product(name="Banana", qty=10, qty_unit="wat", price=10, barcode=123, category="fruit")

    def test_invalid_price(self):
        with self.assertRaises(ValidationError):
            Product(name="Banana", qty=10, qty_unit="kg", price=0, barcode=123, category="fruit")
        with self.assertRaises(ValidationError):
            Product(name="Banana", qty=10, qty_unit="kg", price=-2, barcode=123, category="fruit")

    def test_invalid_barcode(self):
        with self.assertRaises(ValidationError):
            Product(name="Banana", qty=10, qty_unit="kg", price=10, barcode=-1, category="fruit")

    def test_empty_category(self):
        with self.assertRaises(ValidationError):
            Product(name="Banana", qty=10, qty_unit="kg", price=10, barcode=123, category="")
