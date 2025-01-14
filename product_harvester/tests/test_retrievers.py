from unittest import TestCase
from unittest.mock import patch, call, MagicMock

from product_harvester.retrievers import (
    ImagesRetriever,
    LocalImagesRetriever,
    GoogleDriveImagesRetriever,
    _GoogleDriveFileInfo,
    _GoogleDriveClient,
)


class TestImagesRetriever(TestCase):
    def test_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            ImagesRetriever().retrieve_images()


class TestLocalImagesRetriever(TestCase):
    @patch("product_harvester.retrievers.glob", return_value=[])
    def test_empty_path(self, mock_glob):
        retriever = LocalImagesRetriever("")
        mock_images = list(retriever.retrieve_images())
        mock_glob.assert_called_once_with("./*")
        self.assertEqual(mock_images, [])

    @patch("product_harvester.retrievers.glob", return_value=["/image.jpg"])
    def test_root_path(self, mock_glob):
        retriever = LocalImagesRetriever("/")
        mock_images = list(retriever.retrieve_images())
        mock_glob.assert_called_once_with("/*")
        self.assertEqual(mock_images, ["/image.jpg"])

    @patch("product_harvester.retrievers.glob", return_value=["./relative.png"])
    def test_relative_path(self, mock_glob):
        retriever = LocalImagesRetriever("./images")
        mock_images = list(retriever.retrieve_images())
        mock_glob.assert_called_once_with("images/*")
        self.assertEqual(mock_images, ["./relative.png"])

    @patch("product_harvester.retrievers.glob", return_value=[])
    def test_long_path(self, mock_glob):
        retriever = LocalImagesRetriever("/images/some/very/very/deep")
        mock_images = list(retriever.retrieve_images())
        mock_glob.assert_called_once_with("/images/some/very/very/deep/*")
        self.assertEqual(mock_images, [])

    @patch(
        "product_harvester.retrievers.glob",
        return_value=[
            "folder/img1.jpg",
            "folder/img2.Jpeg",
            "folder/note.txt",
            "folder/img3.PNG",
        ],
    )
    def test_non_image_in_middle(self, mock_glob):
        retriever = LocalImagesRetriever("folder")
        mock_images = list(retriever.retrieve_images())
        mock_glob.assert_called_once_with("folder/*")
        self.assertEqual(mock_images, ["folder/img1.jpg", "folder/img2.Jpeg", "folder/img3.PNG"])

    @patch("product_harvester.retrievers.glob", return_value=["some_image.png"])
    def test_error(self, mock_glob):
        mock_glob.side_effect = ValueError("Some error")
        retriever = LocalImagesRetriever("./images")
        with self.assertRaises(ValueError):
            list(retriever.retrieve_images())
        mock_glob.assert_called_once_with("images/*")


class TestGoogleDriveClient(TestCase):

    def setUp(self):
        self._client_config = {"installed": {"client_id": "test_client_id", "client_secret": "test_secret"}}
        self._client = _GoogleDriveClient(self._client_config)
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

    @patch("product_harvester.retrievers.Request")
    @patch("product_harvester.retrievers.build")
    def test_ensure_credentials_refresh(self, mock_build, mock_request):
        mock_build.return_value.files.return_value = self._mock_files_service
        self._client._credentials = MagicMock(valid=False, expired=True, refresh_token="token")
        with patch.object(self._client._credentials, "refresh") as mock_refresh:
            self._client.ensure_credentials()
            mock_refresh.assert_called_once_with(mock_request())
        self.assertEqual(self._client._files_service, self._mock_files_service)

    @patch("product_harvester.retrievers.InstalledAppFlow")
    @patch("product_harvester.retrievers.build")
    def test_ensure_credentials_from_consent_screen(self, mock_build, mock_flow):
        mock_build.return_value.files.return_value = self._mock_files_service
        mock_instance = mock_flow.from_client_config.return_value
        mock_instance.run_local_server.return_value = self._valid_credentials
        self._client.ensure_credentials()
        self.assertEqual(self._client._credentials, self._valid_credentials)
        mock_flow.from_client_config.assert_called_with(self._client_config, _GoogleDriveClient._scopes)
        mock_instance.run_local_server.assert_called_once_with(port=0)
        self.assertEqual(self._client._files_service, self._mock_files_service)

    @patch("product_harvester.retrievers.InstalledAppFlow")
    @patch("product_harvester.retrievers.build")
    def test_get_image_files_info(self, mock_build, mock_flow):
        mock_build.return_value.files.return_value = self._mock_files_service
        mock_instance = mock_flow.from_client_config.return_value
        mock_instance.run_local_server.return_value = self._valid_credentials
        result = list(self._client.get_image_files_info("test_folder_id"))
        self.assertEqual(
            result,
            [
                _GoogleDriveFileInfo(id="1", mime_type="image/png"),
                _GoogleDriveFileInfo(id="2", mime_type="image/jpeg"),
                _GoogleDriveFileInfo(id="3", mime_type="image/jpeg"),
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

    @patch("product_harvester.retrievers.io.BytesIO")
    @patch("product_harvester.retrievers.MediaIoBaseDownload")
    @patch("product_harvester.retrievers.Request")
    @patch("product_harvester.retrievers.build")
    def test_download_file_content(self, mock_build, mock_request, mock_media_download, mock_bytes_io):
        mock_build.return_value.files.return_value = self._mock_files_service
        self._client._credentials = MagicMock(valid=False, expired=True, refresh_token="token")
        mock_file = _GoogleDriveFileInfo(id="1", mime_type="image/png")
        mock_media_download.return_value.next_chunk.return_value = (None, True)
        mock_bytes_io.return_value.getvalue.return_value = b"test_data"
        with patch.object(self._client._credentials, "refresh") as mock_refresh:
            content = self._client.download_file_content(mock_file)
            mock_refresh.assert_called_once_with(mock_request())
        self.assertEqual(content, "data:image/png;base64,dGVzdF9kYXRh")
        self._mock_files_service.assert_has_calls([call.get_media(fileId="1")])
        mock_media_download.assert_called_once_with(mock_bytes_io.return_value, self._mock_files_service.get_media())
        mock_bytes_io.assert_called_once()


class TestGoogleDriveImagesRetriever(TestCase):
    def setUp(self):
        self._test_client_config = {
            "installed": {
                "client_id": "client_abc",
                "project_id": "some",
                "client_secret": "very-secret",
                "redirect_uris": ["http://localhost"],
            }
        }
        self._test_folder_id = "abc"

    @patch("product_harvester.retrievers._GoogleDriveClient")
    def test_simple(self, mocked_client):
        mock_client = mocked_client.return_value
        test_files = [
            _GoogleDriveFileInfo(id="file_id_1", mime_type="image/png"),
            _GoogleDriveFileInfo(id="file_id_2", mime_type="image/jpeg"),
        ]
        mock_client.get_image_files_info.return_value = iter(test_files)
        test_contents = ["/some/binary", "/another/binary"]
        mock_client.download_file_content.side_effect = test_contents
        retriever = GoogleDriveImagesRetriever(self._test_client_config, self._test_folder_id)
        mocked_client.assert_called_once_with(self._test_client_config)
        self.assertEqual(list(retriever.retrieve_images()), test_contents)
        mock_client.get_image_files_info.assert_called_once_with(self._test_folder_id)
        mock_client.download_file_content.assert_has_calls([call(test_file) for test_file in test_files])

    @patch("product_harvester.retrievers._GoogleDriveClient")
    def test_change_folder(self, mocked_client):
        mock_client = mocked_client.return_value
        test_file = _GoogleDriveFileInfo(id="file_id_1", mime_type="image/png")
        mock_client.get_image_files_info.return_value = iter([test_file])
        test_contents = ["/some/binary"]
        mock_client.download_file_content.side_effect = test_contents
        retriever = GoogleDriveImagesRetriever(self._test_client_config, self._test_folder_id)
        mocked_client.assert_called_once_with(self._test_client_config)
        retriever.set_folder("other_folder")
        self.assertEqual(list(retriever.retrieve_images()), test_contents)
        mock_client.get_image_files_info.assert_called_once_with("other_folder")
        mock_client.download_file_content.assert_called_once_with(test_file)

    @patch("product_harvester.retrievers._GoogleDriveClient")
    def test_failure(self, mocked_client):
        mock_client = mocked_client.return_value
        test_file = _GoogleDriveFileInfo(id="file_id_1", mime_type="image/png")
        mock_client.get_image_files_info.return_value = iter([test_file])
        mock_client.download_file_content.side_effect = ValueError("Some error")
        retriever = GoogleDriveImagesRetriever(self._test_client_config, self._test_folder_id)
        mocked_client.assert_called_once_with(self._test_client_config)
        with self.assertRaisesRegex(ValueError, "Some error"):
            list(retriever.retrieve_images())
        mock_client.get_image_files_info.assert_called_once_with(self._test_folder_id)
        mock_client.download_file_content.assert_called_once_with(test_file)
