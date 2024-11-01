import base64
from unittest import TestCase
from unittest.mock import mock_open, patch

from product_harvester.retrievers import (
    GoogleDriveImageRetriever,
    ImageRetriever,
    LocalImageRetriever,
)

_MOCK_IMAGE_DATA = b"mock_image_data"
_MOCK_ENCODED_IMAGE = base64.b64encode(_MOCK_IMAGE_DATA).decode("utf-8")


class TestImageRetriever(TestCase):
    def test_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            ImageRetriever().retrieve_images()


class TestLocalImageRetriever(TestCase):
    @patch("product_harvester.retrievers.glob", return_value=[])
    def test_empty_path(self, mock_glob):
        retriever = LocalImageRetriever("")
        images = retriever.retrieve_images()
        mock_glob.assert_called_once_with("./*")
        self.assertEqual(images, [])

    @patch("builtins.open", new_callable=mock_open, read_data=_MOCK_IMAGE_DATA)
    @patch("product_harvester.retrievers.glob", return_value=["/image.jpg"])
    def test_root_path(self, mock_glob, mock_builtin_open):
        retriever = LocalImageRetriever("/")
        images = retriever.retrieve_images()
        mock_glob.assert_called_once_with("/*")
        mock_builtin_open.assert_called_once_with("/image.jpg", "rb")
        self.assertEqual(images, [_MOCK_ENCODED_IMAGE])

    @patch("builtins.open", new_callable=mock_open, read_data=_MOCK_IMAGE_DATA)
    @patch("product_harvester.retrievers.glob", return_value=["./relative.png"])
    def test_relative_path(self, mock_glob, mock_builtin_open):
        retriever = LocalImageRetriever("./images")
        images = retriever.retrieve_images()
        mock_glob.assert_called_once_with("images/*")
        mock_builtin_open.assert_called_once_with("./relative.png", "rb")
        self.assertEqual(images, [_MOCK_ENCODED_IMAGE])

    @patch("product_harvester.retrievers.glob", return_value=[])
    def test_long_path(self, mock_glob):
        retriever = LocalImageRetriever("/images/some/very/very/deep")
        images = retriever.retrieve_images()
        mock_glob.assert_called_once_with("/images/some/very/very/deep/*")
        self.assertEqual(images, [])

    @patch("builtins.open", new_callable=mock_open, read_data=_MOCK_IMAGE_DATA)
    @patch(
        "product_harvester.retrievers.glob",
        return_value=[
            "folder/img1.jpg",
            "folder/img2.Jpeg",
            "folder/note.txt",
            "folder/img3.PNG",
        ],
    )
    def test_non_image_in_middle(self, mock_glob, mock_builtin_open):
        retriever = LocalImageRetriever("folder")
        images = retriever.retrieve_images()
        mock_glob.assert_called_once_with("folder/*")
        mock_builtin_open.assert_any_call("folder/img1.jpg", "rb")
        mock_builtin_open.assert_any_call("folder/img2.Jpeg", "rb")
        mock_builtin_open.assert_any_call("folder/img3.PNG", "rb")
        self.assertEqual(images, [_MOCK_ENCODED_IMAGE] * 3)

    @patch("builtins.open", new_callable=mock_open)
    @patch("product_harvester.retrievers.glob", return_value=["some_image.png"])
    def test_error(self, mock_glob, mock_builtin_open):
        mock_builtin_open.side_effect = (IOError("File could not be opened"),)
        retriever = LocalImageRetriever("./images")
        with self.assertRaises(IOError):
            retriever.retrieve_images()
        mock_glob.assert_called_once_with("images/*")
        mock_builtin_open.assert_called_once_with("some_image.png", "rb")


class TestGoogleDriveImageRetriever(TestCase):
    def test_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            GoogleDriveImageRetriever().retrieve_images()
