from typing import Generator

from product_harvester.retrievers import ImagesRetriever


class Base64Retriever(ImagesRetriever):

    def __init__(self, images_base64: list[str]):
        self._images_base64 = images_base64

    def retrieve_images(self) -> Generator[str, None, None]:
        yield from self._images_base64
