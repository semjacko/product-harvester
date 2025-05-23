from unittest import TestCase
from unittest.mock import patch, call

from product_harvester.clients.google_drive_client import GoogleDriveFileInfo
from product_harvester.image import Image
from product_harvester.retrievers import (
    ImagesRetriever,
    LocalImagesRetriever,
    GoogleDriveImagesRetriever,
)


class TestImagesRetriever(TestCase):
    def test_not_implemented(self):
        with self.assertRaises(TypeError):
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
        self.assertEqual(mock_images, [Image(id="/image.jpg", data="/image.jpg")])

    @patch("product_harvester.retrievers.glob", return_value=["./relative.png"])
    def test_relative_path(self, mock_glob):
        retriever = LocalImagesRetriever("./images")
        mock_images = list(retriever.retrieve_images())
        mock_glob.assert_called_once_with("images/*")
        self.assertEqual(mock_images, [Image(id="./relative.png", data="./relative.png")])

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
        self.assertEqual(
            mock_images,
            [
                Image(id="folder/img1.jpg", data="folder/img1.jpg"),
                Image(id="folder/img2.Jpeg", data="folder/img2.Jpeg"),
                Image(id="folder/img3.PNG", data="folder/img3.PNG"),
            ],
        )

    @patch("product_harvester.retrievers.glob", return_value=["some_image.png"])
    def test_error(self, mock_glob):
        mock_glob.side_effect = ValueError("Some error")
        retriever = LocalImagesRetriever("./images")
        with self.assertRaises(ValueError):
            list(retriever.retrieve_images())
        mock_glob.assert_called_once_with("images/*")


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

    @patch("product_harvester.retrievers.GoogleDriveClient")
    def test_simple(self, mocked_client):
        mock_client = mocked_client.return_value
        test_files = [
            GoogleDriveFileInfo(id="file_id_1", name="one", mime_type="image/png"),
            GoogleDriveFileInfo(id="file_id_2", name="two", mime_type="image/jpeg"),
        ]
        mock_client.get_image_files_info.return_value = iter(test_files)
        mock_client.download_file_content.side_effect = ["/some/binary", "/another/binary"]
        retriever = GoogleDriveImagesRetriever.from_client_config(self._test_client_config, self._test_folder_id)
        mocked_client.assert_called_once_with(self._test_client_config)
        self.assertEqual(
            list(retriever.retrieve_images()),
            [Image(id="file_id_1", data="/some/binary"), Image(id="file_id_2", data="/another/binary")],
        )
        mock_client.get_image_files_info.assert_called_once_with(self._test_folder_id)
        mock_client.download_file_content.assert_has_calls([call(test_file) for test_file in test_files])

    @patch("product_harvester.retrievers.GoogleDriveClient")
    def test_change_folder(self, mocked_client):
        mock_client = mocked_client.return_value
        test_file = GoogleDriveFileInfo(id="file_id_1", name="one", mime_type="image/png")
        mock_client.get_image_files_info.return_value = iter([test_file])
        mock_client.download_file_content.side_effect = ["/some/binary"]
        retriever = GoogleDriveImagesRetriever.from_client_config(self._test_client_config, self._test_folder_id)
        mocked_client.assert_called_once_with(self._test_client_config)
        retriever.set_folder("other_folder")
        self.assertEqual(list(retriever.retrieve_images()), [Image(id="file_id_1", data="/some/binary")])
        mock_client.get_image_files_info.assert_called_once_with("other_folder")
        mock_client.download_file_content.assert_called_once_with(test_file)

    @patch("product_harvester.retrievers.GoogleDriveClient")
    def test_failure(self, mocked_client):
        mock_client = mocked_client.return_value
        test_file = GoogleDriveFileInfo(id="file_id_1", name="one", mime_type="image/png")
        mock_client.get_image_files_info.return_value = iter([test_file])
        mock_client.download_file_content.side_effect = ValueError("Some error")
        retriever = GoogleDriveImagesRetriever.from_client_config(self._test_client_config, self._test_folder_id)
        mocked_client.assert_called_once_with(self._test_client_config)
        with self.assertRaisesRegex(ValueError, "Some error"):
            list(retriever.retrieve_images())
        mock_client.get_image_files_info.assert_called_once_with(self._test_folder_id)
        mock_client.download_file_content.assert_called_once_with(test_file)
