import base64
import os
from glob import glob


class ImageRetriever:
    def retrieve_images(self) -> list[str]:
        raise NotImplementedError()


class FakeImageRetriever(ImageRetriever):
    def __init__(self, retrieved_images: list[str]):
        self._retrieved_images = retrieved_images

    def retrieve_images(self) -> list[str]:
        return self._retrieved_images


class LocalImageRetriever(ImageRetriever):
    def __init__(self, folder_path: str):
        self._folder_path = os.path.normpath(folder_path)

    def retrieve_images(self) -> list[str]:
        paths = self._retrieve_paths()
        return [self._encode_image(path) for path in paths]

    def _retrieve_paths(self) -> list[str]:
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
