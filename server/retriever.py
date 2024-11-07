from product_harvester.retrievers import ImageLinksRetriever


class Base64Retriever(ImageLinksRetriever):

    def __init__(self, images_base64: list[str]):
        self._images_base64 = images_base64

    def retrieve_image_links(self) -> list[str]:
        return self._images_base64
