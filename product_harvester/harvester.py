import logging
from typing import Any, Generator

from product_harvester.importers import ProductsImporter
from product_harvester.processors import ProcessingError, ProcessingResult, ImageProcessor
from product_harvester.product import Product
from product_harvester.retrievers import ImagesRetriever


class HarvestError(Exception):
    def __init__(self, msg: str, extra: dict[str, Any] = None):
        self.msg = msg
        self.extra = extra

    def __eq__(self, other):
        return isinstance(other, HarvestError) and self.msg == other.msg and self.extra == other.extra


class ErrorTracker:
    def track_errors(self, errors: list[HarvestError]):
        raise NotImplementedError()


class ErrorPrinter(ErrorTracker):
    def track_errors(self, errors: list[HarvestError]):
        for error in errors:
            print(error)


class ErrorLogger(ErrorTracker):
    def __init__(self):
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s: %(asctime)s %(message)s"))
        self._logger = logging.getLogger()
        self._logger.handlers = [handler]
        self._logger.setLevel(logging.DEBUG)

    def track_errors(self, errors: list[HarvestError]):
        for error in errors:
            self._logger.error(msg=error.msg, extra=error.extra)


class ProductsHarvester:
    def __init__(
        self,
        retriever: ImagesRetriever,
        processor: ImageProcessor,
        importer: ProductsImporter,
        error_tracker: ErrorTracker = ErrorLogger(),
    ):
        self._retriever = retriever
        self._processor = processor
        self._importer = importer
        self._error_tracker = error_tracker

    def harvest(self):
        for images_batch in self._generate_image_batches():
            result = self._process_images(images_batch)
            products = self._extract_products_and_track_errors(result)
            self._import_products(products)

    def _generate_image_batches(self, batch_size: int = 8) -> Generator[list[str], None, None]:
        try:
            images_generator = self._retriever.retrieve_images()
        except Exception as e:
            self._track_errors([HarvestError("Failed to retrieve images", {"detailed_info": str(e)})])
            return
        while True:
            batch = self._make_images_batch(images_generator, batch_size)
            yield batch
            if len(batch) < batch_size:
                return

    def _make_images_batch(self, generator: Generator[str, None, None], batch_size: int = 8) -> list[str]:
        batch: list[str] = []
        for i in range(batch_size):
            try:
                batch.append(next(generator))
            except StopIteration:
                break
            except Exception as e:
                self._track_errors([HarvestError("Failed to retrieve image", {"detailed_info": str(e)})])  # TODO: input
        return batch

    def _process_images(self, images: list[str]) -> ProcessingResult | None:
        if not images:
            return None
        try:
            result = self._processor.process(images)
        except Exception as e:
            self._track_errors(
                [HarvestError("Failed to extract data from the images", {"input": images, "detailed_info": str(e)})]
            )
            return None
        return result

    def _extract_products_and_track_errors(self, result: ProcessingResult | None) -> list[Product]:
        if not result:
            return []
        self._track_processing_errors(result.errors)
        return result.products

    def _import_products(self, products: list[Product]):
        for product in products:
            self._import_product(product)

    def _import_product(self, product: Product):
        try:
            self._importer.import_product(product)
        except Exception as e:
            self._track_errors(
                [
                    HarvestError(
                        "Failed to to import extracted product data", {"input": product, "detailed_info": str(e)}
                    )
                ]
            )

    def _track_processing_errors(self, processing_errors: list[ProcessingError]):
        errors = [
            HarvestError(error.msg, {"input": error.input, "detailed_info": error.detailed_msg})
            for error in processing_errors
        ]
        self._track_errors(errors)

    def _track_errors(self, errors: list[HarvestError]):
        if errors:
            self._error_tracker.track_errors(errors)
