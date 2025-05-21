from unittest import TestCase
from unittest.mock import patch

from product_harvester.clients.usetri_api_client import UsetriAPICategory, UsetriAPIProduct, UsetriAPIProductDetail
from product_harvester.image import Image
from product_harvester.importers import (
    ProductsImporter,
    UsetriAPIProductsImporter,
    StdOutProductsImporter,
    _UsetriAPIProductFactory,
    ImportedProduct,
)


class TestUsetriAPIProductFactory(TestCase):

    def test_from_product_convert_unit_ml_to_l(self):
        product = ImportedProduct(
            name="Milk",
            qty=1500,
            qty_unit="ml",
            price=1,
            barcode="123",
            brand="Rajo",
            category="voda",
            source_image=Image(id="source_image", data="whatever"),
            is_barcode_checked=True,
        )
        imported_product = _UsetriAPIProductFactory.from_imported_product(product, category_id=1, shop_id=1)
        want_imported_product = UsetriAPIProduct(
            product=UsetriAPIProductDetail(
                barcode=product.barcode,
                name=product.name,
                amount=1.5,
                brand=product.brand,
                unit="l",
                category_id=1,
                source_image=product.source_image.id,
                is_barcode_checked=True,
            ),
            price=product.price,
            shop_id=1,
        )
        self.assertEqual(imported_product, want_imported_product)

    def test_from_product_convert_unit_g_to_kg(self):
        product = ImportedProduct(
            name="Bananas",
            qty=2545,
            qty_unit="g",
            price=4.53,
            barcode="22",
            brand="Ban",
            category="jedlo",
            source_image=Image(id="some_source_image", data="whatever"),
            is_barcode_checked=False,
        )
        imported_product = _UsetriAPIProductFactory.from_imported_product(product, category_id=2, shop_id=4)
        want_imported_product = UsetriAPIProduct(
            product=UsetriAPIProductDetail(
                barcode=product.barcode,
                name=product.name,
                amount=2.545,
                brand=product.brand,
                unit="kg",
                category_id=2,
                source_image=product.source_image.id,
                is_barcode_checked=False,
            ),
            price=product.price,
            shop_id=4,
        )
        self.assertEqual(imported_product, want_imported_product)

    def test_from_product_convert_unit_pcs(self):
        product = ImportedProduct(
            name="Tools",
            qty=25,
            qty_unit="pcs",
            price=9.43,
            barcode="13",
            brand="Som",
            category="ostatné",
            source_image=Image(id="source_image", data="whatever"),
            is_barcode_checked=False,
        )
        imported_product = _UsetriAPIProductFactory.from_imported_product(product, category_id=3, shop_id=55)
        want_imported_product = UsetriAPIProduct(
            product=UsetriAPIProductDetail(
                barcode=product.barcode,
                name=product.name,
                amount=25,
                brand=product.brand,
                unit="pcs",
                category_id=3,
                source_image=product.source_image.id,
                is_barcode_checked=False,
            ),
            price=product.price,
            shop_id=55,
        )
        self.assertEqual(imported_product, want_imported_product)


class TestProductsImporter(TestCase):
    def test_process_not_implemented(self):
        product = ImportedProduct(
            name="Milk",
            qty=1500,
            qty_unit="ml",
            price=1,
            barcode="123",
            brand="Rajo",
            category="voda",
            source_image=Image(id="source_image", data="whatever"),
            is_barcode_checked=False,
        )
        with self.assertRaises(TypeError):
            ProductsImporter().import_product(product)


class TestStdOutProductsImporter(TestCase):
    def setUp(self):
        self._product = ImportedProduct(
            name="Bananas",
            qty=1.5,
            qty_unit="kg",
            price=1.45,
            brand="Clever",
            barcode="123",
            category="jedlo",
            source_image=Image(id="source_image", data="whatever"),
            is_barcode_checked=True,
        )

    @patch("builtins.print")
    def test_print_imported_product_success(self, print_mock):
        StdOutProductsImporter().import_product(self._product)
        print_mock.assert_called_once_with(self._product)


class TestUsetriAPIProductsImporter(TestCase):
    def setUp(self):
        self._token = "test_token"
        self._product = ImportedProduct(
            name="Bananas",
            qty=1.5,
            qty_unit="kg",
            price=1.45,
            brand="Clever",
            barcode="123",
            category="jedlo",
            source_image=Image(id="source_image", data="whatever"),
            is_barcode_checked=False,
        )
        self._category_id = 2
        self._shop_id = 12
        self._imported_product = _UsetriAPIProductFactory.from_imported_product(
            self._product, self._category_id, self._shop_id
        )

    @patch("product_harvester.importers.UsetriClient")
    def test_import_product_success(self, mocked_client):
        mock_client = mocked_client.return_value
        mock_client.get_categories.return_value = [
            UsetriAPICategory(id=1, name="drink"),
            UsetriAPICategory(id=2, name="jedlo"),
        ]
        importer = UsetriAPIProductsImporter.from_api_token(token=self._token, shop_id=self._shop_id)
        mocked_client.assert_called_once_with(self._token)
        mock_client.get_categories.assert_called_once()
        importer.import_product(self._product)
        mock_client.import_product.assert_called_once_with(self._imported_product)

    @patch("product_harvester.importers.UsetriClient")
    def test_import_product_invalid_category(self, mocked_client):
        mock_client = mocked_client.return_value
        mock_client.get_categories.return_value = [UsetriAPICategory(id=1, name="drink")]
        importer = UsetriAPIProductsImporter.from_api_token(token=self._token, shop_id=self._shop_id)
        mocked_client.assert_called_once_with(self._token)
        mock_client.get_categories.assert_called_once()
        with self.assertRaises(KeyError):
            importer.import_product(self._product)
        mock_client.import_product.assert_not_called()

    @patch("product_harvester.importers.UsetriClient")
    def test_import_product_failure(self, mocked_client):
        mock_client = mocked_client.return_value
        mock_client.import_product.side_effect = ValueError("Some error")
        mock_client.get_categories.return_value = [UsetriAPICategory(id=2, name="jedlo")]
        importer = UsetriAPIProductsImporter.from_api_token(token=self._token, shop_id=self._shop_id)
        mocked_client.assert_called_once_with(self._token)
        mock_client.get_categories.assert_called_once()
        with self.assertRaises(ValueError):
            importer.import_product(self._product)
        mock_client.import_product.assert_called_once_with(self._imported_product)
