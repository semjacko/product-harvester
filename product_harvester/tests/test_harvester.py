from unittest import TestCase
from unittest.mock import call, Mock, patch, MagicMock

from product_harvester.harvester import ErrorLogger, ErrorTracker, HarvestError, ProductsHarvester, StdOutErrorTracker
from product_harvester.image import Image
from product_harvester.importers import ImportedProduct
from product_harvester.processors import ProcessingError, ProcessingResult, PerImageProcessingResult
from product_harvester.product import Product


class TestErrorTracker(TestCase):
    def test_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            ErrorTracker().track_errors([])


class TestStdOutErrorTracker(TestCase):

    @patch("builtins.print")
    def test_print_errors(self, print_mock):
        errs = [
            HarvestError("example message", {"info": "additional"}),
            HarvestError("error with no extra"),
            HarvestError("", {"extra": "only extra"}),
        ]
        StdOutErrorTracker().track_errors(errs)
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
        mock_images = [Image(id="image1", data="/image1.jpg"), Image(id="image2", data="/image2.png")]
        self._mock_retriever.retrieve_images.return_value = iter(mock_images)
        mock_products = [
            Product(name="Banana", qty=1.0, qty_unit="kg", price=1.99, barcode="456", category="jedlo"),
            Product(name="Milk", qty=500, qty_unit="ml", price=0.99, barcode="66053", category="voda"),
        ]
        self._mock_processor.process.return_value = ProcessingResult(
            results=[
                PerImageProcessingResult(input_image=input_image, output=mock_product, is_barcode_checked=True)
                for input_image, mock_product in zip(mock_images, mock_products)
            ]
        )

        self._harvester.harvest()

        self._mock_retriever.retrieve_images.assert_called_once()
        self._mock_processor.process.assert_called_once_with(mock_images)
        self._mock_tracker.track_errors.assert_not_called()
        want_calls = [
            call(ImportedProduct.from_product(mock_product, source_image_id=mock_image.id, is_barcode_checked=True))
            for mock_product, mock_image in zip(mock_products, mock_images)
        ]
        self._mock_importer.import_product.assert_has_calls(want_calls)

    def test_harvest_imports_products_and_tracks_errors(self):
        mock_images = [
            Image(id="image1", data="/image1.jpg"),
            Image(id="image2", data="/wat.jpeg"),
            Image(id="image3", data="/wtf.png"),
        ]
        self._mock_retriever.retrieve_images.return_value = iter(mock_images)
        mock_product = Product(name="Bread", qty=3, qty_unit="pcs", price=3.35, barcode="123", category="jedlo")
        self._mock_processor.process.return_value = ProcessingResult(
            results=[
                PerImageProcessingResult(input_image=mock_images[0], output=mock_product),
                PerImageProcessingResult(
                    input_image=mock_images[1],
                    output=ProcessingError("invalid image mocked error", "some detailed message"),
                ),
                PerImageProcessingResult(
                    input_image=mock_images[2],
                    output=ProcessingError("invalid JSON extracted mocked error", "other detailed message"),
                ),
            ]
        )

        self._harvester.harvest()

        self._mock_retriever.retrieve_images.assert_called_once()
        self._mock_processor.process.assert_called_once_with(mock_images)
        self._mock_tracker.track_errors.assert_called_once_with(
            [
                HarvestError(
                    "invalid image mocked error",
                    {"input": "image2", "detailed_info": "some detailed message"},
                ),
                HarvestError(
                    "invalid JSON extracted mocked error",
                    {"input": "image3", "detailed_info": "other detailed message"},
                ),
            ]
        )
        self._mock_importer.import_product.assert_called_once_with(
            ImportedProduct.from_product(mock_product, source_image_id="image1", is_barcode_checked=False)
        )

    def test_harvest_empty_retriever_result(self):
        self._mock_retriever.retrieve_images.return_value = iter([])

        self._harvester.harvest()

        self._mock_retriever.retrieve_images.assert_called_once()
        self._mock_processor.process.assert_not_called()
        self._mock_tracker.track_errors.assert_not_called()
        self._mock_importer.import_product.assert_not_called()

    def test_harvest_retriever_error(self):
        self._mock_retriever.retrieve_images.side_effect = ValueError("Something went wrong during retrieval")

        self._harvester.harvest()

        self._mock_retriever.retrieve_images.assert_called_once()
        self._mock_processor.process.assert_not_called()
        self._mock_tracker.track_errors.assert_called_once_with(
            [HarvestError("Failed to retrieve images", {"detailed_info": "Something went wrong during retrieval"})]
        )
        self._mock_importer.import_product.assert_not_called()

    def test_harvest_retriever_generator_error(self):
        valid_input_image = Image(id="image1", data="/image1.jpg")
        mock_images = MagicMock()
        mock_images.__next__.side_effect = [valid_input_image, ValueError("Some error")]
        self._mock_retriever.retrieve_images.return_value = mock_images
        mock_product = Product(name="Banana", qty=1.0, qty_unit="kg", price=1.99, barcode="456", category="jedlo")
        self._mock_processor.process.return_value = ProcessingResult(
            results=[
                PerImageProcessingResult(input_image=valid_input_image, output=mock_product, is_barcode_checked=True)
            ]
        )
        self._harvester.harvest()

        self._mock_retriever.retrieve_images.assert_called_once()
        self._mock_processor.process.assert_called_once_with([Image(id="image1", data="/image1.jpg")])
        self._mock_tracker.track_errors.assert_called_once_with(
            [HarvestError("Failed to retrieve image", {"detailed_info": "Some error"})]
        )
        self._mock_importer.import_product.assert_called_once_with(
            ImportedProduct.from_product(mock_product, source_image_id="image1", is_barcode_checked=True)
        )

    def test_harvest_processor_error(self):
        mock_images = [Image(id="image1", data="/image1.png"), Image(id="image2", data="/image2.jpeg")]
        self._mock_retriever.retrieve_images.return_value = iter(mock_images)
        self._mock_processor.process.side_effect = ValueError("Something went wrong during processing")

        self._harvester.harvest()

        self._mock_retriever.retrieve_images.assert_called_once()
        self._mock_processor.process.assert_called_once_with(mock_images)
        self._mock_tracker.track_errors.assert_called_once_with(
            [
                HarvestError(
                    "Failed to extract data from the images",
                    {
                        "input": ["image1", "image2"],
                        "detailed_info": "Something went wrong during processing",
                    },
                )
            ]
        )
        self._mock_importer.import_product.assert_not_called()

    def test_harvest_importer_error(self):
        mock_images = [Image(id="image1", data="/image1.jpg"), Image(id="image2", data="/image2.png")]
        self._mock_retriever.retrieve_images.return_value = iter(mock_images)
        mock_products = [
            Product(name="Banana", qty=1.0, qty_unit="kg", price=1.99, barcode="456", category="jedlo"),
            Product(name="Milk", qty=500, qty_unit="ml", price=0.99, barcode="66053", category="voda"),
        ]
        self._mock_processor.process.return_value = ProcessingResult(
            results=[
                PerImageProcessingResult(input_image=input_image, output=mock_product)
                for input_image, mock_product in zip(mock_images, mock_products)
            ]
        )
        self._mock_importer.import_product.side_effect = [ValueError("Some importing error"), None]

        self._harvester.harvest()

        self._mock_retriever.retrieve_images.assert_called_once()
        self._mock_processor.process.assert_called_once_with(mock_images)
        self._mock_tracker.track_errors.assert_called_once_with(
            [
                HarvestError(
                    "Failed to to import extracted product data",
                    {
                        "input": "image1",
                        "imported_product": {
                            "name": "Banana",
                            "qty": 1.0,
                            "qty_unit": "kg",
                            "price": 1.99,
                            "barcode": "456",
                            "brand": "",
                            "category": "jedlo",
                            "source_image_id": "image1",
                            "is_barcode_checked": False,
                        },
                        "detailed_info": "Some importing error",
                    },
                )
            ]
        )
        want_calls = [
            call(ImportedProduct.from_product(mock_product, source_image_id=mock_image.id, is_barcode_checked=False))
            for mock_product, mock_image in zip(mock_products, mock_images)
        ]
        self._mock_importer.import_product.assert_has_calls(want_calls)
