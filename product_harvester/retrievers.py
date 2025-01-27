import os
from glob import glob
from typing import Generator, Any, Self

from product_harvester.clients.google_drive_client import GoogleDriveClient


class ImagesRetriever:
    def retrieve_images(self) -> Generator[str, None, None]:
        raise NotImplementedError()


class LocalImagesRetriever(ImagesRetriever):
    _image_extensions = (".jpg", ".jpeg", ".png")

    def __init__(self, folder_path: str):
        self._folder_path = os.path.normpath(folder_path)

    def retrieve_images(self) -> Generator[str, None, None]:
        yield from self._retrieve_image_paths()

    def _retrieve_image_paths(self) -> list[str]:
        return [
            file_path for file_path in self._retrieve_file_paths() if file_path.lower().endswith(self._image_extensions)
        ]

    def _retrieve_file_paths(self) -> list[str]:
        path_pattern = os.path.join(self._folder_path, "*")
        return glob(path_pattern)


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
            yield self._client.download_file_content(file)
