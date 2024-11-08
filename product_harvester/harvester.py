import logging
from typing import Any

from product_harvester.processors import ImageProcessor, ProcessingError, ProcessingResult
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
    def track_errors(self, errors: list[HarvestError]):
        for error in errors:
            logging.error(msg=error.msg, extra=error.extra)


class ProductsHarvester:
    def __init__(
        self,
        retriever: ImageLinksRetriever,
        processor: ImageProcessor,
        error_tracker: ErrorTracker = ErrorLogger(),
    ):
        self._retriever = retriever
        self._processor = processor
        self._error_tracker = error_tracker

    def harvest(self) -> list[Product]:
        image_links = self._retrieve_image_links()
        result = self._process_images(image_links)
        return self._extract_products_and_track_errors(result)

    def _retrieve_image_links(self) -> list[str]:
        try:
            image_links = self._retriever.retrieve_image_links()
        except Exception as e:
            self._track_errors(
                [HarvestError("Failed to retrieve image links", {"detailed_info": str(e)})]
            )  # TODO: input
            return []
        return image_links

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

    def _track_processing_errors(self, processing_errors: list[ProcessingError]):
        errors = [
            HarvestError(error.msg, {"input": error.input, "detailed_info": error.detailed_msg})
            for error in processing_errors
        ]
        self._track_errors(errors)

    def _track_errors(self, errors: list[HarvestError]):
        if errors:
            self._error_tracker.track_errors(errors)
