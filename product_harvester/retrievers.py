import os
from glob import glob


class ImageLinksRetriever:
    def retrieve_links(self) -> list[str]:
        raise NotImplementedError()


class LocalImageLinksRetriever(ImageLinksRetriever):
    def __init__(self, folder_path: str):
        self._folder_path = os.path.normpath(folder_path)

    def retrieve_links(self) -> list[str]:
        path_pattern = os.path.join(self._folder_path, "*")
        return glob(path_pattern)


class GoogleDriveImageLinksRetriever(ImageLinksRetriever):
    def retrieve_links(self) -> list[str]:
        # TODO
        raise NotImplementedError()
