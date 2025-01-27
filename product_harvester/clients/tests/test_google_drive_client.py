from unittest import TestCase
from unittest.mock import MagicMock, call, patch

from product_harvester.clients.google_drive_client import GoogleDriveClient, GoogleDriveFileInfo


class TestGoogleDriveClient(TestCase):

    def setUp(self):
        self._client_config = {"installed": {"client_id": "test_client_id", "client_secret": "test_secret"}}
        self._client = GoogleDriveClient(self._client_config)
        self._valid_credentials = MagicMock(valid=True)
        self._mock_files_service = MagicMock()
        self._mock_files_service.list.return_value.execute.side_effect = [
            {
                "files": [{"id": "1", "mimeType": "image/png"}, {"id": "2", "mimeType": "image/jpeg"}],
                "nextPageToken": "some_token",
            },
            {
                "files": [{"id": "3", "mimeType": "image/jpeg"}],
                "nextPageToken": None,
            },
        ]

    def test_ensure_credentials_already_valid(self):
        self._client._credentials = self._valid_credentials
        self._client.ensure_credentials()
        # Credentials were manually overridden with MagicMock, therefore files_services should not be initialized
        self.assertIsNone(self._client._files_service)

    @patch("product_harvester.clients.google_drive_client.Request")
    @patch("product_harvester.clients.google_drive_client.build")
    def test_ensure_credentials_refresh(self, mock_build, mock_request):
        mock_build.return_value.files.return_value = self._mock_files_service
        self._client._credentials = MagicMock(valid=False, expired=True, refresh_token="token")
        with patch.object(self._client._credentials, "refresh") as mock_refresh:
            self._client.ensure_credentials()
            mock_refresh.assert_called_once_with(mock_request())
        self.assertEqual(self._client._files_service, self._mock_files_service)

    @patch("product_harvester.clients.google_drive_client.InstalledAppFlow")
    @patch("product_harvester.clients.google_drive_client.build")
    def test_ensure_credentials_from_consent_screen(self, mock_build, mock_flow):
        mock_build.return_value.files.return_value = self._mock_files_service
        mock_instance = mock_flow.from_client_config.return_value
        mock_instance.run_local_server.return_value = self._valid_credentials
        self._client.ensure_credentials()
        self.assertEqual(self._client._credentials, self._valid_credentials)
        mock_flow.from_client_config.assert_called_with(self._client_config, GoogleDriveClient._scopes)
        mock_instance.run_local_server.assert_called_once_with(port=0)
        self.assertEqual(self._client._files_service, self._mock_files_service)

    @patch("product_harvester.clients.google_drive_client.InstalledAppFlow")
    @patch("product_harvester.clients.google_drive_client.build")
    def test_get_image_files_info(self, mock_build, mock_flow):
        mock_build.return_value.files.return_value = self._mock_files_service
        mock_instance = mock_flow.from_client_config.return_value
        mock_instance.run_local_server.return_value = self._valid_credentials
        result = list(self._client.get_image_files_info("test_folder_id"))
        self.assertEqual(
            result,
            [
                GoogleDriveFileInfo(id="1", mime_type="image/png"),
                GoogleDriveFileInfo(id="2", mime_type="image/jpeg"),
                GoogleDriveFileInfo(id="3", mime_type="image/jpeg"),
            ],
        )
        self._mock_files_service.assert_has_calls(
            [
                call.list(
                    pageSize=8,
                    q="'test_folder_id' in parents and mimeType contains 'image/'",
                    fields="nextPageToken, files(id, mimeType)",
                    pageToken=None,
                ),
                call.list().execute(),
                call.list(
                    pageSize=8,
                    q="'test_folder_id' in parents and mimeType contains 'image/'",
                    fields="nextPageToken, files(id, mimeType)",
                    pageToken="some_token",
                ),
                call.list().execute(),
            ]
        )

    @patch("product_harvester.clients.google_drive_client.io.BytesIO")
    @patch("product_harvester.clients.google_drive_client.MediaIoBaseDownload")
    @patch("product_harvester.clients.google_drive_client.Request")
    @patch("product_harvester.clients.google_drive_client.build")
    def test_download_file_content(self, mock_build, mock_request, mock_media_download, mock_bytes_io):
        mock_build.return_value.files.return_value = self._mock_files_service
        self._client._credentials = MagicMock(valid=False, expired=True, refresh_token="token")
        mock_file = GoogleDriveFileInfo(id="1", mime_type="image/png")
        mock_media_download.return_value.next_chunk.return_value = (None, True)
        mock_bytes_io.return_value.getvalue.return_value = b"test_data"
        with patch.object(self._client._credentials, "refresh") as mock_refresh:
            content = self._client.download_file_content(mock_file)
            mock_refresh.assert_called_once_with(mock_request())
        self.assertEqual(content, "data:image/png;base64,dGVzdF9kYXRh")
        self._mock_files_service.assert_has_calls([call.get_media(fileId="1")])
        mock_media_download.assert_called_once_with(mock_bytes_io.return_value, self._mock_files_service.get_media())
        mock_bytes_io.assert_called_once()
