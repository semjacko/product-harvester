from unittest import TestCase
from unittest.mock import Mock, patch

import requests
from pydantic import ValidationError

from product_harvester.importers import ImportedProduct, ImportedProductDetail, ProductsImporter, APIProductsImporter
from product_harvester.product import Product


class TestImportedProduct(TestCase):

    def test_from_product_convert_unit_ml_to_l(self):
        product = Product(name="Milk", qty=1500, qty_unit="ml", price=1, barcode=123, brand="Rajo", category="voda")
        imported_product = ImportedProduct.from_product(product, shop_id=1)
        want_imported_product = ImportedProduct(
            product=ImportedProductDetail(
                barcode=product.barcode,
                name=product.name,
                amount=1.5,
                brand=product.brand,
                unit="l",
                category_id=1,
            ),
            price=product.price,
            shop_id=1,
        )
        self.assertEqual(imported_product, want_imported_product)

    def test_from_product_convert_unit_g_to_kg(self):
        product = Product(name="Bananas", qty=2545, qty_unit="g", price=4.53, barcode=22, brand="Ban", category="jedlo")
        imported_product = ImportedProduct.from_product(product, shop_id=4)
        want_imported_product = ImportedProduct(
            product=ImportedProductDetail(
                barcode=product.barcode,
                name=product.name,
                amount=2.545,
                brand=product.brand,
                unit="kg",
                category_id=2,
            ),
            price=product.price,
            shop_id=4,
        )
        self.assertEqual(imported_product, want_imported_product)

    def test_from_product_convert_unit_pcs(self):
        product = Product(name="Tools", qty=25, qty_unit="pcs", price=9.43, barcode=13, brand="Som", category="ostatné")
        imported_product = ImportedProduct.from_product(product, shop_id=55)
        want_imported_product = ImportedProduct(
            product=ImportedProductDetail(
                barcode=product.barcode,
                name=product.name,
                amount=25,
                brand=product.brand,
                unit="pcs",
                category_id=3,
            ),
            price=product.price,
            shop_id=55,
        )
        self.assertEqual(imported_product, want_imported_product)

    def test_from_product_invalid_category(self):
        product = Product(name="Bananas", qty=2545, qty_unit="g", price=4.53, barcode=22, brand="Ban", category="wat")
        with self.assertRaises(ValidationError):
            ImportedProduct.from_product(product, shop_id=1)

    def test_from_product_invalid_shop_id(self):
        product = Product(name="Bananas", qty=2545, qty_unit="g", price=4.53, barcode=22, brand="Ban", category="jedlo")
        with self.assertRaises(ValidationError):
            ImportedProduct.from_product(product, shop_id=0)


class TestProductsImporter(TestCase):
    def test_process_not_implemented(self):
        product = Product(name="Milk", qty=1500, qty_unit="ml", price=1, barcode=123, brand="Rajo", category="voda")
        imported_product = ImportedProduct.from_product(product, shop_id=1)
        with self.assertRaises(NotImplementedError):
            ProductsImporter().import_product(imported_product)


class TestAPIProductsImporter(TestCase):
    def setUp(self):
        self._token = "test_token"
        self._base_url = "https://test-api.example.com"
        self._importer = APIProductsImporter(token=self._token, base_url=self._base_url)
        self._imported_product = ImportedProduct(
            product=ImportedProductDetail(
                barcode=123,
                name="Bananas",
                amount=1.5,
                brand="Clever",
                unit="kg",
                category_id=2,
            ),
            price=1.45,
            shop_id=2,
        )
        self._imported_product_json = self._imported_product.model_dump()

    @patch("product_harvester.importers.requests.Session.post")
    def test_import_product_success(self, mock_post):
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        self._importer.import_product(self._imported_product)
        mock_post.assert_called_once_with(
            f"{self._base_url}/products", json=self._imported_product_json, headers={"user-id": self._token}
        )
        mock_response.raise_for_status.assert_called_once()

    @patch("product_harvester.importers.requests.Session.post")
    def test_import_product_invalid_token(self, mock_post):
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("401 Unauthorized")
        mock_post.return_value = mock_response
        with self.assertRaises(requests.exceptions.HTTPError):
            self._importer.import_product(self._imported_product)
        mock_post.assert_called_once_with(
            f"{self._base_url}/products", json=self._imported_product_json, headers={"user-id": self._token}
        )

    @patch("product_harvester.importers.requests.Session.post")
    def test_import_product_generic_exception(self, mock_post):
        mock_post.side_effect = Exception("Generic Exception")
        with self.assertRaises(Exception):
            self._importer.import_product(self._imported_product)
        mock_post.assert_called_once_with(
            f"{self._base_url}/products", json=self._imported_product_json, headers={"user-id": self._token}
        )

    def tearDown(self):
        self._importer._session.close()
