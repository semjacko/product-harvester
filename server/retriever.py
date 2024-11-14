from typing import Generator

from product_harvester.retrievers import ImageLinksRetriever


class Base64Retriever(ImageLinksRetriever):

    def __init__(self, images_base64: list[str]):
        self._images_base64 = images_base64

    def retrieve_image_links(self) -> Generator[str, None, None]:
        yield from self._images_base64
