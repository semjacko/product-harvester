from unittest import TestCase
from unittest.mock import Mock, patch

import requests
from pydantic import ValidationError

from product_harvester.dolacna_client import _DoLacnaAPIProductDetail
from product_harvester.importers import (
    _DoLacnaAPIProduct,
    ProductsImporter,
    DoLacnaAPIProductsImporter,
    StdOutProductsImporter,
    _DoLacnaClient,
    _DoLacnaAPICategory,
)
from product_harvester.product import Product


class _TestDoLacnaAPIProduct(TestCase):

    def test_from_product_convert_unit_ml_to_l(self):
        product = Product(name="Milk", qty=1500, qty_unit="ml", price=1, barcode=123, brand="Rajo", category="voda")
        imported_product = _DoLacnaAPIProduct.from_product(product, category_id=1, shop_id=1)
        want_imported_product = _DoLacnaAPIProduct(
            product=_DoLacnaAPIProductDetail(
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
        imported_product = _DoLacnaAPIProduct.from_product(product, category_id=2, shop_id=4)
        want_imported_product = _DoLacnaAPIProduct(
            product=_DoLacnaAPIProductDetail(
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
        imported_product = _DoLacnaAPIProduct.from_product(product, category_id=3, shop_id=55)
        want_imported_product = _DoLacnaAPIProduct(
            product=_DoLacnaAPIProductDetail(
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

    def test_from_product_invalid_shop_id(self):
        product = Product(name="Bananas", qty=2545, qty_unit="g", price=4.53, barcode=22, brand="Ban", category="jedlo")
        with self.assertRaises(ValidationError):
            _DoLacnaAPIProduct.from_product(product, category_id=2, shop_id=0)


class TestProductsImporter(TestCase):
    def test_process_not_implemented(self):
        product = Product(name="Milk", qty=1500, qty_unit="ml", price=1, barcode=123, brand="Rajo", category="voda")
        with self.assertRaises(NotImplementedError):
            ProductsImporter().import_product(product)


class TestStdOutProductsImporter(TestCase):
    def setUp(self):
        self._product = Product(
            name="Bananas",
            qty=1.5,
            qty_unit="kg",
            price=1.45,
            brand="Clever",
            barcode=123,
            category="jedlo",
        )

    @patch("builtins.print")
    def test_print_imported_product_success(self, print_mock):
        StdOutProductsImporter().import_product(self._product)
        print_mock.assert_called_once_with(self._product)


class TestDoLacnaClient(TestCase):
    def setUp(self):
        self._token = "test_token"
        self._client = _DoLacnaClient(token=self._token)
        self._imported_product = _DoLacnaAPIProduct(
            product=_DoLacnaAPIProductDetail(
                barcode=123,
                name="Bananas",
                amount=1.5,
                brand="Clever",
                unit="kg",
                category_id=3,
            ),
            price=1.45,
            shop_id=12,
        )
        self._imported_product_json = self._imported_product.model_dump()
        self._mock_response = Mock()

    @patch("product_harvester.importers.requests.Session.post")
    def test_import_product_success(self, mock_post):
        self._mock_response.raise_for_status.return_value = None
        mock_post.return_value = self._mock_response
        self._client.import_product(self._imported_product)
        mock_post.assert_called_once_with(
            _DoLacnaClient._products_endpoint, json=self._imported_product_json, headers={"user-id": self._token}
        )
        self._mock_response.raise_for_status.assert_called_once()

    @patch("product_harvester.importers.requests.Session.post")
    def test_import_product_invalid_token(self, mock_post):
        self._mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("401 Unauthorized")
        mock_post.return_value = self._mock_response
        with self.assertRaises(requests.exceptions.HTTPError):
            self._client.import_product(self._imported_product)
        mock_post.assert_called_once_with(
            _DoLacnaClient._products_endpoint, json=self._imported_product_json, headers={"user-id": self._token}
        )

    @patch("product_harvester.importers.requests.Session.get")
    def test_get_categories_success(self, mock_get):
        self._mock_response.raise_for_status.return_value = None
        self._mock_response.json.return_value = {"categories": [{"id": 1, "name": "food"}, {"id": 2, "name": "drink"}]}
        mock_get.return_value = self._mock_response
        categories = self._client.get_categories()
        self.assertEqual(categories, [_DoLacnaAPICategory(id=1, name="food"), _DoLacnaAPICategory(id=2, name="drink")])
        mock_get.assert_called_once_with(_DoLacnaClient._categories_endpoint)

    @patch("product_harvester.importers.requests.Session.get")
    def test_get_categories_empty_response(self, mock_get):
        self._mock_response.raise_for_status.return_value = None
        self._mock_response.json.return_value = {}
        mock_get.return_value = self._mock_response
        categories = self._client.get_categories()
        self.assertEqual(categories, [])
        mock_get.assert_called_once_with(_DoLacnaClient._categories_endpoint)

    @patch("product_harvester.importers.requests.Session.get")
    def test_get_categories_failure(self, mock_get):
        self._mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("401 Unauthorized")
        mock_get.return_value = self._mock_response
        with self.assertRaises(requests.exceptions.HTTPError):
            self._client.get_categories()
        mock_get.assert_called_once_with(_DoLacnaClient._categories_endpoint)

    def tearDown(self):
        self._client._session.close()


class TestDoLacnaAPIProductsImporter(TestCase):
    def setUp(self):
        self._token = "test_token"
        self._product = Product(
            name="Bananas",
            qty=1.5,
            qty_unit="kg",
            price=1.45,
            brand="Clever",
            barcode=123,
            category="jedlo",
        )
        self._category_id = 2
        self._shop_id = 12
        self._imported_product = _DoLacnaAPIProduct.from_product(self._product, self._category_id, self._shop_id)

    @patch("product_harvester.importers._DoLacnaClient")
    def test_import_product_success(self, mocked_client):
        mock_client = mocked_client.return_value
        mock_client.get_categories.return_value = [
            _DoLacnaAPICategory(id=1, name="drink"),
            _DoLacnaAPICategory(id=2, name="jedlo"),
        ]
        importer = DoLacnaAPIProductsImporter(token=self._token, shop_id=self._shop_id)
        mocked_client.assert_called_once_with(self._token)
        mock_client.get_categories.assert_called_once()
        importer.import_product(self._product)
        mock_client.import_product.assert_called_once_with(self._imported_product)

    @patch("product_harvester.importers._DoLacnaClient")
    def test_import_product_invalid_category(self, mocked_client):
        mock_client = mocked_client.return_value
        mock_client.get_categories.return_value = [_DoLacnaAPICategory(id=1, name="drink")]
        importer = DoLacnaAPIProductsImporter(token=self._token, shop_id=self._shop_id)
        mocked_client.assert_called_once_with(self._token)
        mock_client.get_categories.assert_called_once()
        with self.assertRaises(KeyError):
            importer.import_product(self._product)
        mock_client.import_product.assert_not_called()

    @patch("product_harvester.importers._DoLacnaClient")
    def test_import_product_failure(self, mocked_client):
        mock_client = mocked_client.return_value
        mock_client.import_product.side_effect = ValueError("Some error")
        mock_client.get_categories.return_value = [_DoLacnaAPICategory(id=2, name="jedlo")]
        importer = DoLacnaAPIProductsImporter(token=self._token, shop_id=self._shop_id)
        mocked_client.assert_called_once_with(self._token)
        mock_client.get_categories.assert_called_once()
        with self.assertRaises(ValueError):
            importer.import_product(self._product)
        mock_client.import_product.assert_called_once_with(self._imported_product)
