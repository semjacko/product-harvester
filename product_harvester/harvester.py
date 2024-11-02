from product_harvester.processors import ImageProcessor, ProcessingError
from product_harvester.product import Product
from product_harvester.retrievers import ImageRetriever


class ProductsHarvester:
    def __init__(self, retriever: ImageRetriever, processor: ImageProcessor):
        self._retriever = retriever
        self._processor = processor

    def harvest(self) -> list[Product]:
        encoded_images = self._retriever.retrieve_images()
        if not encoded_images:
            return []
        result = self._processor.process(encoded_images)
        self._track_errors(result.errors)
        return result.products

    @staticmethod
    def _track_errors(errors: list[ProcessingError]):
        print(errors)  # TODO
