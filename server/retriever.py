from typing import Generator

from product_harvester.image import Image
from product_harvester.retrievers import ImagesRetriever


class Base64Retriever(ImagesRetriever):

    def __init__(self, images_base64: list[str]):
        self._images = [
            Image(id=f"uploaded_image{i}", data=image_data) for i, image_data in enumerate(images_base64, start=1)
        ]

    def retrieve_images(self) -> Generator[Image, None, None]:
        yield from self._images
