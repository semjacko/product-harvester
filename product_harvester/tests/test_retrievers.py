from unittest import TestCase
from unittest.mock import patch, call

from product_harvester.retrievers import (
    ImageLinksRetriever,
    LocalImageLinksRetriever,
    GoogleDriveImageLinksRetriever,
    _GoogleDriveFileInfo,
)


class TestImageLinksRetriever(TestCase):
    def test_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            ImageLinksRetriever().retrieve_image_links()


class TestLocalImageLinksRetriever(TestCase):
    @patch("product_harvester.retrievers.glob", return_value=[])
    def test_empty_path(self, mock_glob):
        retriever = LocalImageLinksRetriever("")
        image_links = list(retriever.retrieve_image_links())
        mock_glob.assert_called_once_with("./*")
        self.assertEqual(image_links, [])

    @patch("product_harvester.retrievers.glob", return_value=["/image.jpg"])
    def test_root_path(self, mock_glob):
        retriever = LocalImageLinksRetriever("/")
        image_links = list(retriever.retrieve_image_links())
        mock_glob.assert_called_once_with("/*")
        self.assertEqual(image_links, ["/image.jpg"])

    @patch("product_harvester.retrievers.glob", return_value=["./relative.png"])
    def test_relative_path(self, mock_glob):
        retriever = LocalImageLinksRetriever("./images")
        image_links = list(retriever.retrieve_image_links())
        mock_glob.assert_called_once_with("images/*")
        self.assertEqual(image_links, ["./relative.png"])

    @patch("product_harvester.retrievers.glob", return_value=[])
    def test_long_path(self, mock_glob):
        retriever = LocalImageLinksRetriever("/images/some/very/very/deep")
        image_links = list(retriever.retrieve_image_links())
        mock_glob.assert_called_once_with("/images/some/very/very/deep/*")
        self.assertEqual(image_links, [])

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
        retriever = LocalImageLinksRetriever("folder")
        image_links = list(retriever.retrieve_image_links())
        mock_glob.assert_called_once_with("folder/*")
        self.assertEqual(image_links, ["folder/img1.jpg", "folder/img2.Jpeg", "folder/img3.PNG"])

    @patch("product_harvester.retrievers.glob", return_value=["some_image.png"])
    def test_error(self, mock_glob):
        mock_glob.side_effect = ValueError("Some error")
        retriever = LocalImageLinksRetriever("./images")
        with self.assertRaises(ValueError):
            list(retriever.retrieve_image_links())
        mock_glob.assert_called_once_with("images/*")


class TestGoogleDriveImageLinksRetriever(TestCase):
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
        retriever = GoogleDriveImageLinksRetriever(self._test_client_config, self._test_folder_id)
        self.assertEqual(list(retriever.retrieve_image_links()), test_contents)
        mock_client.get_image_files_info.assert_called_once_with(self._test_folder_id)
        mock_client.download_file_content.assert_has_calls([call(test_file) for test_file in test_files])

    @patch("product_harvester.retrievers._GoogleDriveClient")
    def test_change_folder(self, mocked_client):
        mock_client = mocked_client.return_value
        test_file = _GoogleDriveFileInfo(id="file_id_1", mime_type="image/png")
        mock_client.get_image_files_info.return_value = iter([test_file])
        test_contents = ["/some/binary"]
        mock_client.download_file_content.side_effect = test_contents
        retriever = GoogleDriveImageLinksRetriever(self._test_client_config, self._test_folder_id)
        retriever.set_folder("other_folder")
        self.assertEqual(list(retriever.retrieve_image_links()), test_contents)
        mock_client.get_image_files_info.assert_called_once_with("other_folder")
        mock_client.download_file_content.assert_called_once_with(test_file)

    @patch("product_harvester.retrievers._GoogleDriveClient")
    def test_failure(self, mocked_client):
        mock_client = mocked_client.return_value
        test_file = _GoogleDriveFileInfo(id="file_id_1", mime_type="image/png")
        mock_client.get_image_files_info.return_value = iter([test_file])
        mock_client.download_file_content.side_effect = ValueError("Some error")
        retriever = GoogleDriveImageLinksRetriever(self._test_client_config, self._test_folder_id)
        with self.assertRaisesRegex(ValueError, "Some error"):
            list(retriever.retrieve_image_links())
        mock_client.get_image_files_info.assert_called_once_with(self._test_folder_id)
        mock_client.download_file_content.assert_called_once_with(test_file)
