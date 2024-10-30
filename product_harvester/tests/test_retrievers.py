from typing import Any
from unittest import TestCase
from unittest.mock import patch

from product_harvester.retrievers import (
    GoogleDriveImageRetriever,
    ImageRetriever,
    LocalImageRetriever,
)


def _patch_encode_image():
    return patch(
        "product_harvester.retrievers.LocalImageRetriever._encode_image",
        side_effect=_identity_side_effect,
    )


def _identity_side_effect(input_value: Any) -> Any:
    return input_value


class TestImageRetriever(TestCase):
    def test_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            ImageRetriever().retrieve_images()


class TestLocalImageRetriever(TestCase):
    @patch("product_harvester.retrievers.glob", return_value=[])
    def test_empty_path(self, mock_glob):
        retriever = LocalImageRetriever("")
        with _patch_encode_image():
            images = retriever.retrieve_images()
        mock_glob.assert_called_with("./*")
        self.assertEqual(images, [])

    @patch("product_harvester.retrievers.glob", return_value=["/image.jpg"])
    def test_root_path(self, mock_glob):
        retriever = LocalImageRetriever("/")
        with _patch_encode_image():
            images = retriever.retrieve_images()
        mock_glob.assert_called_with("/*")
        self.assertEqual(images, ["/image.jpg"])

    @patch(
        "product_harvester.retrievers.glob",
        return_value=["images/img1.jpg", "images/img2.jpg"],
    )
    def test_without_slash(self, mock_glob):
        retriever = LocalImageRetriever("images")
        with _patch_encode_image():
            images = retriever.retrieve_images()
        mock_glob.assert_called_with("images/*")
        self.assertEqual(images, ["images/img1.jpg", "images/img2.jpg"])

    @patch("product_harvester.retrievers.glob", return_value=["./relative.png"])
    def test_relative_path(self, mock_glob):
        retriever = LocalImageRetriever("./images")
        with _patch_encode_image():
            images = retriever.retrieve_images()
        mock_glob.assert_called_with("images/*")
        self.assertEqual(images, ["./relative.png"])

    @patch("product_harvester.retrievers.glob", return_value=[])
    def test_long_path(self, mock_glob):
        retriever = LocalImageRetriever("/images/some/very/very/deep")
        with _patch_encode_image():
            images = retriever.retrieve_images()
        mock_glob.assert_called_with("/images/some/very/very/deep/*")
        self.assertEqual(images, [])


class TestGoogleDriveImageRetriever(TestCase):
    def test_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            GoogleDriveImageRetriever().retrieve_images()
