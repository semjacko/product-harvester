from unittest import TestCase
from unittest.mock import patch

from product_harvester.retrievers import (
    GoogleDriveImageLinksRetriever,
    ImageLinksRetriever,
    LocalImageLinksRetriever,
)


class TestImageLinksRetriever(TestCase):
    def test_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            ImageLinksRetriever().retrieve_image_links()


class TestLocalImageLinksRetriever(TestCase):
    @patch("product_harvester.retrievers.glob", return_value=[])
    def test_empty_path(self, mock_glob):
        retriever = LocalImageLinksRetriever("")
        image_links = retriever.retrieve_image_links()
        mock_glob.assert_called_once_with("./*")
        self.assertEqual(image_links, [])

    @patch("product_harvester.retrievers.glob", return_value=["/image.jpg"])
    def test_root_path(self, mock_glob):
        retriever = LocalImageLinksRetriever("/")
        image_links = retriever.retrieve_image_links()
        mock_glob.assert_called_once_with("/*")
        self.assertEqual(image_links, ["/image.jpg"])

    @patch("product_harvester.retrievers.glob", return_value=["./relative.png"])
    def test_relative_path(self, mock_glob):
        retriever = LocalImageLinksRetriever("./images")
        image_links = retriever.retrieve_image_links()
        mock_glob.assert_called_once_with("images/*")
        self.assertEqual(image_links, ["./relative.png"])

    @patch("product_harvester.retrievers.glob", return_value=[])
    def test_long_path(self, mock_glob):
        retriever = LocalImageLinksRetriever("/images/some/very/very/deep")
        image_links = retriever.retrieve_image_links()
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
        image_links = retriever.retrieve_image_links()
        mock_glob.assert_called_once_with("folder/*")
        self.assertEqual(image_links, ["folder/img1.jpg", "folder/img2.Jpeg", "folder/img3.PNG"])

    @patch("product_harvester.retrievers.glob", return_value=["some_image.png"])
    def test_error(self, mock_glob):
        mock_glob.side_effect = ValueError("Some error")
        retriever = LocalImageLinksRetriever("./images")
        with self.assertRaises(ValueError):
            retriever.retrieve_image_links()
        mock_glob.assert_called_once_with("images/*")


class TestGoogleDriveImageLinksRetriever(TestCase):
    def test_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            GoogleDriveImageLinksRetriever().retrieve_image_links()
