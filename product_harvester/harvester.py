import logging
from abc import ABC, abstractmethod
from typing import Any, Generator

from product_harvester.image import Image
from product_harvester.importers import ProductsImporter, ImportedProduct
from product_harvester.processors import ProcessingResult, ImageProcessor, PerImageProcessingResult
from product_harvester.retrievers import ImagesRetriever


class HarvestError(Exception):
    def __init__(self, msg: str, extra: dict[str, Any] = None):
        self.msg = msg
        self.extra = extra

    def __eq__(self, other):
        return isinstance(other, HarvestError) and self.msg == other.msg and self.extra == other.extra


class ErrorTracker(ABC):
    @abstractmethod
    def track_errors(self, errors: list[HarvestError]): ...


class StdOutErrorTracker(ErrorTracker):
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
            product_results = self._extract_products_and_track_errors(result)
            self._override_results_with_input_meta(product_results)
            self._import_products(product_results)

    def _generate_image_batches(self, batch_size: int = 8) -> Generator[list[Image], None, None]:
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

    def _make_images_batch(self, generator: Generator[Image, None, None], batch_size: int = 8) -> list[Image]:
        batch: list[Image] = []
        for i in range(batch_size):
            try:
                batch.append(next(generator))
            except StopIteration:
                break
            except Exception as e:
                self._track_errors([HarvestError("Failed to retrieve image", {"detailed_info": str(e)})])
        return batch

    def _process_images(self, images: list[Image]) -> ProcessingResult | None:
        if not images:
            return None
        try:
            result = self._processor.process(images)
        except Exception as e:
            image_ids = [image.id for image in images]
            self._track_errors(
                [HarvestError("Failed to extract data from the images", {"input": image_ids, "detailed_info": str(e)})]
            )
            return None
        return result

    def _extract_products_and_track_errors(self, result: ProcessingResult | None) -> list[PerImageProcessingResult]:
        if not result:
            return []
        self._track_processing_errors(result.error_results)
        return result.product_results

    @staticmethod
    def _override_results_with_input_meta(product_results: list[PerImageProcessingResult]):
        for result in product_results:
            result.input_image.meta.adjust_product(result.output)

    def _import_products(self, product_results: list[PerImageProcessingResult]):
        for result in product_results:
            self._import_product(result)

    def _import_product(self, product_result: PerImageProcessingResult):
        imported_product = ImportedProduct.from_product(
            product=product_result.output,
            source_image=product_result.input_image,
            is_barcode_checked=product_result.is_barcode_checked,
        )
        try:
            self._importer.import_product(imported_product)
        except Exception as e:
            self._track_errors(
                [
                    HarvestError(
                        "Failed to to import extracted product data",
                        {
                            "input": product_result.input_image.id,
                            "imported_product": imported_product.model_dump(),
                            "detailed_info": str(e),
                        },
                    )
                ]
            )

    def _track_processing_errors(self, error_results: list[PerImageProcessingResult]):
        errors = [
            HarvestError(
                result.output.msg, {"input": result.input_image.id, "detailed_info": result.output.detailed_msg}
            )
            for result in error_results
        ]
        self._track_errors(errors)

    def _track_errors(self, errors: list[HarvestError]):
        if errors:
            self._error_tracker.track_errors(errors)
