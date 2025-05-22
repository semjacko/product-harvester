import ntpath
import os
from abc import ABC, abstractmethod
from glob import glob
from typing import Generator, Any, Self

from product_harvester.clients.google_drive_client import GoogleDriveClient
from product_harvester.image import Image, ImageMeta
from product_harvester.product import Product


class ImagesRetriever(ABC):
    @abstractmethod
    def retrieve_images(self) -> Generator[Image, None, None]: ...


class LocalImagesRetriever(ImagesRetriever):
    _image_extensions = (".jpg", ".jpeg", ".png")

    def __init__(self, folder_path: str):
        self._folder_path = os.path.normpath(folder_path)

    def retrieve_images(self) -> Generator[Image, None, None]:
        yield from [Image(id=image_path, data=image_path) for image_path in self._retrieve_image_paths()]

    def _retrieve_image_paths(self) -> list[str]:
        return [
            file_path for file_path in self._retrieve_file_paths() if file_path.lower().endswith(self._image_extensions)
        ]

    def _retrieve_file_paths(self) -> list[str]:
        path_pattern = os.path.join(self._folder_path, "*")
        return glob(path_pattern)


class _ImageMeta(ImageMeta):
    def __init__(self, formatted_meta: str):
        parts = formatted_meta.split("_")
        if len(parts) == 3:
            shop_id = parts[0]
            self.barcode = parts[1]
            date = parts[2]
        else:
            raise ValueError("Meta format is incorrect. Expected 'shopId_barcode_date'.")
        super().__init__({"shop_id": shop_id, "date": date})

    def adjust_product(self, product: Product) -> None:
        product.barcode = self.barcode


class LocalImagesRetrieverWithMeta(LocalImagesRetriever):
    def retrieve_images(self) -> Generator[Image, None, None]:
        for image in super().retrieve_images():
            image_name = self._extract_image_name(image.id)
            image.meta = _ImageMeta(image_name)
            yield image

    @staticmethod
    def _extract_image_name(path: str) -> str:
        return ntpath.basename(path)


class GoogleDriveImagesRetriever(ImagesRetriever):

    def __init__(self, client: GoogleDriveClient, folder_id: str):
        self._client = client
        self._folder_id = folder_id

    @classmethod
    def from_client_config(cls, client_config: dict[str, Any], folder_id: str) -> Self:
        return GoogleDriveImagesRetriever(GoogleDriveClient(client_config), folder_id)

    def set_folder(self, folder_id: str):
        self._folder_id = folder_id

    def retrieve_images(self) -> Generator[str, None, None]:
        for file in self._client.get_image_files_info(self._folder_id):
            data = self._client.download_file_content(file)
            yield Image(id=file.id, data=data)
