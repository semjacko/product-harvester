import base64
import os
from glob import glob


class ImageRetriever:
    def retrieve_images(self) -> list[str]:
        raise NotImplementedError()


class LocalImageRetriever(ImageRetriever):
    _image_extensions = (".jpg", ".jpeg", ".png")

    def __init__(self, folder_path: str):
        self._folder_path = os.path.normpath(folder_path)

    def retrieve_images(self) -> list[str]:
        paths = self._retrieve_image_paths()
        return [self._encode_image(path) for path in paths]

    def _retrieve_image_paths(self) -> list[str]:
        return [
            file_path
            for file_path in self._retrieve_file_paths()
            if file_path.lower().endswith(self._image_extensions)
        ]

    def _retrieve_file_paths(self) -> list[str]:
        path_pattern = os.path.join(self._folder_path, "*")
        return glob(path_pattern)

    @staticmethod
    def _encode_image(path: str) -> str:
        with open(path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")


class GoogleDriveImageRetriever(ImageRetriever):
    def retrieve_images(self) -> list[str]:
        # TODO
        raise NotImplementedError()
