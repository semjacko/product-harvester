from typing import Any
from unittest import TestCase
from unittest.mock import call, Mock, patch

from product_harvester.harvester import ErrorLogger, ErrorTracker, HarvestError, ProductsHarvester, ErrorPrinter
from product_harvester.processors import ProcessingError, ProcessingResult
from product_harvester.product import Product


class TestErrorTracker(TestCase):
    def test_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            ErrorTracker().track_errors([])


class TestErrorPrinter(TestCase):

    @patch("builtins.print")
    def test_print_errors(self, print_mock):
        errs = [
            HarvestError("example message", {"info": "additional"}),
            HarvestError("error with no extra"),
            HarvestError("", {"extra": "only extra"}),
        ]
        ErrorPrinter().track_errors(errs)
        print_mock.assert_has_calls([call(err) for err in errs])


class TestErrorLogger(TestCase):
    def setUp(self):
        self._logger = ErrorLogger()
        self._logger._logger = Mock()

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
        self._mock_importer = Mock()
        self._mock_tracker = Mock()
        self._harvester = ProductsHarvester(
            self._mock_retriever, self._mock_processor, self._mock_importer, self._mock_tracker
        )

    def test_harvest_imports_products(self):
        mock_image_links = ["/image1.jpg", "/image2.png"]
        self._mock_retriever.retrieve_image_links.return_value = self._yield_from(mock_image_links)
        mock_products = [
            Product(name="Banana", qty=1.0, qty_unit="kg", price=1.99, barcode=456, category="jedlo"),
            Product(name="Milk", qty=500, qty_unit="ml", price=0.99, barcode=66053, category="voda"),
        ]
        self._mock_processor.process.return_value = ProcessingResult(mock_products, [])

        self._harvester.harvest()

        self._mock_retriever.retrieve_image_links.assert_called_once()
        self._mock_processor.process.assert_called_once_with(mock_image_links)
        self._mock_tracker.track_errors.assert_not_called()
        want_calls = [call(mock_product) for mock_product in mock_products]
        self._mock_importer.import_product.assert_has_calls(want_calls)

    def test_harvest_imports_products_and_tracks_errors(self):
        mock_image_links = ["/image1.jpg", "/wat.jpeg", "/wtf.png"]
        self._mock_retriever.retrieve_image_links.return_value = self._yield_from(mock_image_links)
        mock_products = [Product(name="Bread", qty=3, qty_unit="pcs", price=3.35, barcode=123, category="jedlo")]
        self._mock_processor.process.return_value = ProcessingResult(
            mock_products,
            [
                ProcessingError({"link": "/wat.jpeg"}, "invalid image mocked error", "some detailed message"),
                ProcessingError({"link": "/wtf.png"}, "invalid JSON extracted mocked error", "other detailed message"),
            ],
        )

        self._harvester.harvest()

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
        want_calls = [call(mock_product) for mock_product in mock_products]
        self._mock_importer.import_product.assert_has_calls(want_calls)

    def test_harvest_empty_retriever_result(self):
        self._mock_retriever.retrieve_image_links.return_value = self._yield_from([])

        self._harvester.harvest()

        self._mock_retriever.retrieve_image_links.assert_called_once()
        self._mock_processor.process.assert_not_called()
        self._mock_tracker.track_errors.assert_not_called()
        self._mock_importer.import_product.assert_not_called()

    def test_harvest_retriever_error(self):
        self._mock_retriever.retrieve_image_links.side_effect = ValueError("Something went wrong during retrieval")

        self._harvester.harvest()

        self._mock_retriever.retrieve_image_links.assert_called_once()
        self._mock_processor.process.assert_not_called()
        self._mock_tracker.track_errors.assert_called_once_with(
            [HarvestError("Failed to retrieve image links", {"detailed_info": "Something went wrong during retrieval"})]
        )
        self._mock_importer.import_product.assert_not_called()

    def test_harvest_processor_error(self):
        mock_image_links = ["/image1.png", "/image2.jpeg"]
        self._mock_retriever.retrieve_image_links.return_value = self._yield_from(mock_image_links)
        self._mock_processor.process.side_effect = ValueError("Something went wrong during processing")

        self._harvester.harvest()

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
        self._mock_importer.import_product.assert_not_called()

    @staticmethod
    def _yield_from(l: list[Any]):
        yield from l
