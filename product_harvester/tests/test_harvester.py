from unittest import TestCase
from unittest.mock import Mock

from product_harvester.harvester import ProductsHarvester
from product_harvester.processors import SimpleProcessingResult
from product_harvester.product import Product


class TestProductsHarvester(TestCase):
    def setUp(self):
        self._mock_retriever = Mock()
        self._mock_processor = Mock()
        self._harvester = ProductsHarvester(self._mock_retriever, self._mock_processor)

    def test_harvest_returns_products(self):
        mock_images = ["<encoded_image1>", "<encoded_image2>"]
        self._mock_retriever.retrieve_images.return_value = mock_images
        mock_products = [
            Product(name="Banana", qty=1.0, qty_unit="kg", price=1.99),
            Product(name="Milk", qty=500, qty_unit="ml", price=0.99),
        ]
        self._mock_processor.process.return_value = SimpleProcessingResult(mock_products, [])

        products = self._harvester.harvest()

        self._mock_retriever.retrieve_images.assert_called_once()
        self._mock_processor.process.assert_called_once_with(mock_images)
        self.assertEqual(products, mock_products)

    def test_harvest_empty_retriever_result(self):
        self._mock_retriever.retrieve_images.return_value = []

        result = self._harvester.harvest()

        self._mock_retriever.retrieve_images.assert_called_once()
        self._mock_processor.process.assert_not_called()
        self.assertEqual(result, [])
