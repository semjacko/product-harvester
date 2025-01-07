import base64
import io
import os
from glob import glob
from typing import Generator, Any, NamedTuple

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import Resource, build
from googleapiclient.http import MediaIoBaseDownload


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


class _GoogleDriveFileInfo(NamedTuple):
    id: str
    mime_type: str


class _GoogleDriveClient:
    _scopes = [
        "https://www.googleapis.com/auth/drive.metadata.readonly",
        "https://www.googleapis.com/auth/drive.readonly",
    ]

    def __init__(self, client_config: dict[str, Any]):
        self._client_config = client_config
        self._credentials: Credentials | None = None
        self._files_service: Resource | None = None

    def _ensure_credentials(self):
        if self._has_valid_credentials():
            return
        elif self._can_refresh_credentials():
            self._credentials.refresh(Request())
        else:
            self._load_credentials_from_consent_screen()
        self._files_service = build("drive", "v3", credentials=self._credentials).files()

    def _has_valid_credentials(self) -> bool:
        return self._credentials and self._credentials.valid

    def _can_refresh_credentials(self) -> bool:
        return self._credentials and self._credentials.expired and self._credentials.refresh_token

    def _load_credentials_from_consent_screen(self):
        flow = InstalledAppFlow.from_client_config(self._client_config, self._scopes)
        self._credentials = flow.run_local_server(port=0)

    def get_image_files_info(self, folder_id: str) -> Generator[_GoogleDriveFileInfo, None, None]:
        query = f"'{folder_id}' in parents and mimeType contains 'image/'"
        files, page_offset_token = self._get_image_files_batch(query)
        while page_offset_token:
            yield from files
            files, page_offset_token = self._get_image_files_batch(query, page_offset_token)
        yield from files

    def _get_image_files_batch(
        self,
        query: str,
        page_offset_token: str | None = None,
        batch_size: int = 8,
    ) -> tuple[list[_GoogleDriveFileInfo], str | None]:
        self._ensure_credentials()
        request = self._files_service.list(
            pageSize=batch_size, q=query, fields="nextPageToken, files(id, mimeType)", pageToken=page_offset_token
        )
        result = request.execute()
        files = [
            _GoogleDriveFileInfo(id=file.get("id", ""), mime_type=file.get("mimeType", "")) for file in result["files"]
        ]
        return files, result.get("nextPageToken", None)

    def download_file_content(self, file: _GoogleDriveFileInfo) -> str:
        self._ensure_credentials()
        request = self._files_service.get_media(fileId=file.id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        content = base64.b64encode(fh.getvalue()).decode("utf-8")
        return f"data:{file.mime_type};base64,{content}"


class GoogleDriveImageLinksRetriever(ImageLinksRetriever):

    def __init__(self, client_config: dict[str, Any], folder_id: str):
        self._client = _GoogleDriveClient(client_config)
        self._folder_id = folder_id

    def set_folder(self, folder_id: str):
        self._folder_id = folder_id

    def retrieve_image_links(self) -> Generator[str, None, None]:
        for file in self._client.get_image_files_info(self._folder_id):
            yield self._client.download_file_content(file)
