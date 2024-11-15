import logging
from typing import Any, Generator

from product_harvester.importer import ProductsImporter, ImportedProduct
from product_harvester.processors import ProcessingError, ProcessingResult, ImageProcessor
from product_harvester.product import Product
from product_harvester.retrievers import ImageLinksRetriever


class HarvestError(Exception):
    def __init__(self, msg: str, extra: dict[str, Any] = None):
        self.msg = msg
        self.extra = extra

    def __eq__(self, other):
        return isinstance(other, HarvestError) and self.msg == other.msg and self.extra == other.extra


class ErrorTracker:
    def track_errors(self, errors: list[HarvestError]):
        raise NotImplementedError()


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
        retriever: ImageLinksRetriever,
        processor: ImageProcessor,
        importer: ProductsImporter,
        error_tracker: ErrorTracker = ErrorLogger(),
    ):
        self._retriever = retriever
        self._processor = processor
        self._importer = importer
        self._error_tracker = error_tracker

    def harvest(self):
        for image_links_batch in self._generate_image_link_batches():
            result = self._process_images(image_links_batch)
            products = self._extract_products_and_track_errors(result)
            self._import_products(products)

    def _generate_image_link_batches(self, batch_size: int = 8) -> Generator[list[str], None, None]:
        try:
            image_links_generator = self._retriever.retrieve_image_links()
        except Exception as e:
            self._track_errors([HarvestError("Failed to retrieve image links", {"detailed_info": str(e)})])
            return
        while True:
            batch = self._make_image_links_batch(image_links_generator, batch_size)
            yield batch
            if len(batch) < batch_size:
                return

    def _make_image_links_batch(self, generator: Generator[str, None, None], batch_size: int = 8) -> list[str]:
        batch: list[str] = []
        for i in range(batch_size):
            try:
                batch.append(next(generator))
            except StopIteration:
                break
            except Exception as e:
                self._track_errors(
                    [HarvestError("Failed to retrieve image link", {"detailed_info": str(e)})]
                )  # TODO: input
        return batch

    def _process_images(self, image_links: list[str]) -> ProcessingResult | None:
        if not image_links:
            return None
        try:
            result = self._processor.process(image_links)
        except Exception as e:
            self._track_errors(
                [
                    HarvestError(
                        "Failed to extract data from the images", {"input": image_links, "detailed_info": str(e)}
                    )
                ]
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
            shop_id = 1  # TODO
            imported_product = ImportedProduct.from_product(product, shop_id)
            self._importer.import_product(imported_product)
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
