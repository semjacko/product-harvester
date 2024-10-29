from unittest import TestCase

from product_harvester.product import Product


class TestProduct(TestCase):
    def test_ok(self):
        Product(name="Banana", qty=1.5, qty_unit="kg", price=1)
        Product(name="Milk", qty=1000, qty_unit="ml", price=10)
        Product(name="Kiwi", qty=3, qty_unit="pcs", price=10.54)

    def test_empty(self):
        with self.assertRaises(ValueError):
            Product()

    def test_invalid_name(self):
        with self.assertRaises(ValueError):
            Product(name="", qty=10, qty_unit="kg", price=10)

    def test_invalid_qty(self):
        with self.assertRaises(ValueError):
            Product(name="Banana", qty=0, qty_unit="kg", price=10)
        with self.assertRaises(ValueError):
            Product(name="Banana", qty=-2, qty_unit="kg", price=10)

    def test_invalid_qty_unit(self):
        with self.assertRaises(ValueError):
            Product(name="Banana", qty=10, qty_unit="", price=10)
        with self.assertRaises(ValueError):
            Product(name="Banana", qty=10, qty_unit="wat", price=10)

    def test_invalid_price(self):
        with self.assertRaises(ValueError):
            Product(name="Banana", qty=10, qty_unit="kg", price=0)
        with self.assertRaises(ValueError):
            Product(name="Banana", qty=10, qty_unit="kg", price=-2)
