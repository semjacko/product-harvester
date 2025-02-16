from unittest import TestCase
from unittest.mock import Mock, patch

import requests

from product_harvester.clients.dolacna_api_client import (
    DoLacnaClient,
    DoLacnaAPICategory,
    DoLacnaAPIProduct,
    DoLacnaAPIProductDetail,
)


class TestDoLacnaClient(TestCase):
    def setUp(self):
        self._token = "test_token"
        self._client = DoLacnaClient(token=self._token)
        self._imported_product = DoLacnaAPIProduct(
            product=DoLacnaAPIProductDetail(
                barcode=123,
                name="Bananas",
                amount=1.5,
                brand="Clever",
                unit="kg",
                category_id=3,
                source_image="image1",
                is_barcode_checked=True,
            ),
            price=1.45,
            shop_id=12,
        )
        self._imported_product_json = self._imported_product.model_dump()
        self._mock_response = Mock()

    @patch("product_harvester.clients.dolacna_api_client.requests.Session.post")
    def test_import_product_success(self, mock_post):
        self._mock_response.raise_for_status.return_value = None
        mock_post.return_value = self._mock_response
        self._client.import_product(self._imported_product)
        mock_post.assert_called_once_with(
            DoLacnaClient._products_endpoint, json=self._imported_product_json, headers={"user-id": self._token}
        )
        self._mock_response.raise_for_status.assert_called_once()

    @patch("product_harvester.clients.dolacna_api_client.requests.Session.post")
    def test_import_product_invalid_token(self, mock_post):
        self._mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("401 Unauthorized")
        mock_post.return_value = self._mock_response
        with self.assertRaises(requests.exceptions.HTTPError):
            self._client.import_product(self._imported_product)
        mock_post.assert_called_once_with(
            DoLacnaClient._products_endpoint, json=self._imported_product_json, headers={"user-id": self._token}
        )

    @patch("product_harvester.clients.dolacna_api_client.requests.Session.get")
    def test_get_categories_success(self, mock_get):
        self._mock_response.raise_for_status.return_value = None
        self._mock_response.json.return_value = {"categories": [{"id": 1, "name": "food"}, {"id": 2, "name": "drink"}]}
        mock_get.return_value = self._mock_response
        for i in range(2):  # Loop to validate caching
            categories = self._client.get_categories()
            want_categories = [DoLacnaAPICategory(id=1, name="food"), DoLacnaAPICategory(id=2, name="drink")]
            self.assertEqual(categories, want_categories)
        mock_get.assert_called_once_with(DoLacnaClient._categories_endpoint)

    @patch("product_harvester.clients.dolacna_api_client.requests.Session.get")
    def test_get_categories_empty_response(self, mock_get):
        self._mock_response.raise_for_status.return_value = None
        self._mock_response.json.return_value = {}
        mock_get.return_value = self._mock_response
        categories = self._client.get_categories()
        self.assertEqual(categories, [])
        mock_get.assert_called_once_with(DoLacnaClient._categories_endpoint)

    @patch("product_harvester.clients.dolacna_api_client.requests.Session.get")
    def test_get_categories_failure(self, mock_get):
        self._mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("401 Unauthorized")
        mock_get.return_value = self._mock_response
        with self.assertRaises(requests.exceptions.HTTPError):
            self._client.get_categories()
        mock_get.assert_called_once_with(DoLacnaClient._categories_endpoint)

    def tearDown(self):
        self._client._session.close()
