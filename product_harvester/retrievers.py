import os
from glob import glob
from typing import Generator


class ImageLinksRetriever:
    def retrieve_image_links(self) -> Generator[str, None, None]:
        raise NotImplementedError()


class LocalImageLinksRetriever(ImageLinksRetriever):
    _image_extensions = (".jpg", ".jpeg", ".png")

    def __init__(self, folder_path: str):
        self._folder_path = os.path.normpath(folder_path)

    def retrieve_image_links(self) -> Generator[str, None, None]:
        yield from self._retrieve_image_paths()

    def _retrieve_image_paths(self) -> list[str]:
        return [
            file_path for file_path in self._retrieve_file_paths() if file_path.lower().endswith(self._image_extensions)
        ]

    def _retrieve_file_paths(self) -> list[str]:
        path_pattern = os.path.join(self._folder_path, "*")
        return glob(path_pattern)


class GoogleDriveImageLinksRetriever(ImageLinksRetriever):
    def retrieve_image_links(self) -> Generator[str, None, None]:
        # TODO
        raise NotImplementedError()
