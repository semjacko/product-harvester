from typing import Any
from unittest import TestCase
from unittest.mock import call, MagicMock, Mock

from product_harvester.harvester import ErrorLogger, ErrorTracker, HarvestError, ProductsHarvester
from product_harvester.processors import ProcessingError, ProcessingResult
from product_harvester.product import Product


class TestErrorTracker(TestCase):
    def test_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            ErrorTracker().track_errors([])


class TestErrorLogger(TestCase):
    def setUp(self):
        self._logger = ErrorLogger()
        self._logger._logger = MagicMock()

    def test_empty(self):
        self._logger.track_errors([])
        self._logger._logger.assert_not_called()

    def test_one_error(self):
        self._logger.track_errors([HarvestError("some message", {"info": "additional info"})])
        self._logger._logger.error.assert_called_once_with(msg="some message", extra={"info": "additional info"})

    def test_multiple_errors(self):
        self._logger.track_errors(
            [
                HarvestError("some message", {"info": "additional info"}),
                HarvestError("error with no extra"),
                HarvestError("", {"extra": "only extra"}),
            ]
        )
        self._logger._logger.error.assert_has_calls(
            [
                call(msg="some message", extra={"info": "additional info"}),
                call(msg="error with no extra", extra=None),
                call(msg="", extra={"extra": "only extra"}),
            ]
        )


class TestProductsHarvester(TestCase):
    def setUp(self):
        self._mock_retriever = Mock()
        self._mock_processor = Mock()
        self._mock_tracker = Mock()
        self._harvester = ProductsHarvester(self._mock_retriever, self._mock_processor, self._mock_tracker)

    def test_harvest_returns_products(self):
        mock_image_links = ["/image1.jpg", "/image2.png"]
        self._mock_retriever.retrieve_image_links.return_value = self._yield_from(mock_image_links)
        mock_products = [
            Product(name="Banana", qty=1.0, qty_unit="kg", price=1.99, barcode=456, category="fruit"),
            Product(name="Milk", qty=500, qty_unit="ml", price=0.99, barcode=66053, category="milk"),
        ]
        self._mock_processor.process.return_value = ProcessingResult(mock_products, [])

        products = self._harvester.harvest()

        self._mock_retriever.retrieve_image_links.assert_called_once()
        self._mock_processor.process.assert_called_once_with(mock_image_links)
        self._mock_tracker.track_errors.assert_not_called()
        self.assertEqual(products, mock_products)

    def test_harvest_returns_product_and_errors(self):
        mock_image_links = ["/image1.jpg", "/wat.jpeg", "/wtf.png"]
        self._mock_retriever.retrieve_image_links.return_value = self._yield_from(mock_image_links)
        mock_products = [Product(name="Bread", qty=3, qty_unit="pcs", price=3.35, barcode=123, category="food")]
        self._mock_processor.process.return_value = ProcessingResult(
            mock_products,
            [
                ProcessingError({"link": "/wat.jpeg"}, "invalid image mocked error", "some detailed message"),
                ProcessingError({"link": "/wtf.png"}, "invalid JSON extracted mocked error", "other detailed message"),
            ],
        )

        products = self._harvester.harvest()

        self._mock_retriever.retrieve_image_links.assert_called_once()
        self._mock_processor.process.assert_called_once_with(mock_image_links)
        self._mock_tracker.track_errors.assert_called_once_with(
            [
                HarvestError(
                    "invalid image mocked error",
                    {
                        "input": {"link": "/wat.jpeg"},
                        "detailed_info": "some detailed message",
                    },
                ),
                HarvestError(
                    "invalid JSON extracted mocked error",
                    {"input": {"link": "/wtf.png"}, "detailed_info": "other detailed message"},
                ),
            ]
        )
        self.assertEqual(products, mock_products)

    def test_harvest_empty_retriever_result(self):
        self._mock_retriever.retrieve_image_links.return_value = self._yield_from([])

        result = self._harvester.harvest()

        self._mock_retriever.retrieve_image_links.assert_called_once()
        self._mock_processor.process.assert_not_called()
        self._mock_tracker.track_errors.assert_not_called()
        self.assertEqual(result, [])

    def test_harvest_retriever_error(self):
        self._mock_retriever.retrieve_image_links.side_effect = ValueError("Something went wrong during retrieval")

        result = self._harvester.harvest()

        self._mock_retriever.retrieve_image_links.assert_called_once()
        self._mock_processor.process.assert_not_called()
        self._mock_tracker.track_errors.assert_called_once_with(
            [HarvestError("Failed to retrieve image links", {"detailed_info": "Something went wrong during retrieval"})]
        )
        self.assertEqual(result, [])

    def test_harvest_processor_error(self):
        mock_image_links = ["/image1.png", "/image2.jpeg"]
        self._mock_retriever.retrieve_image_links.return_value = self._yield_from(mock_image_links)
        self._mock_processor.process.side_effect = ValueError("Something went wrong during processing")

        result = self._harvester.harvest()

        self._mock_retriever.retrieve_image_links.assert_called_once()
        self._mock_processor.process.assert_called_once_with(mock_image_links)
        self._mock_tracker.track_errors.assert_called_once_with(
            [
                HarvestError(
                    "Failed to extract data from the images",
                    {
                        "input": ["/image1.png", "/image2.jpeg"],
                        "detailed_info": "Something went wrong during processing",
                    },
                )
            ]
        )
        self.assertEqual(result, [])

    @staticmethod
    def _yield_from(l: list[Any]):
        yield from l
