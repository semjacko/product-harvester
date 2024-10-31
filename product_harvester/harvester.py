from product_harvester.processors import ImageProcessor
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
        products = self._processor.process_batch(encoded_images)
        return products
