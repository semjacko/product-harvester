from unittest import TestCase
from unittest.mock import patch

from product_harvester.retrievers import LocalImageLinksRetriever


class TestLocalImageLinksRetriever(TestCase):
    @patch("product_harvester.retrievers.glob", return_value=[])
    def test_empty_path(self, mock_glob):
        retriever = LocalImageLinksRetriever("")
        result = retriever.retrieve_links()
        mock_glob.assert_called_with("./*")
        self.assertEqual(result, [])

    @patch("product_harvester.retrievers.glob", return_value=["/image.jpg"])
    def test_root_path(self, mock_glob):
        retriever = LocalImageLinksRetriever("/")
        result = retriever.retrieve_links()
        mock_glob.assert_called_with("/*")
        self.assertEqual(result, ["/image.jpg"])

    @patch(
        "product_harvester.retrievers.glob",
        return_value=["images/img1.jpg", "images/img2.jpg"],
    )
    def test_without_slash(self, mock_glob):
        retriever = LocalImageLinksRetriever("images")
        result = retriever.retrieve_links()
        mock_glob.assert_called_with("images/*")
        self.assertEqual(result, ["images/img1.jpg", "images/img2.jpg"])

    @patch("product_harvester.retrievers.glob", return_value=["./relative.png"])
    def test_relative_path(self, mock_glob):
        retriever = LocalImageLinksRetriever("./images")
        result = retriever.retrieve_links()
        mock_glob.assert_called_with("images/*")
        self.assertEqual(result, ["./relative.png"])

    @patch("product_harvester.retrievers.glob", return_value=[])
    def test_long_path(self, mock_glob):
        retriever = LocalImageLinksRetriever("/images/some/very/very/deep")
        result = retriever.retrieve_links()
        mock_glob.assert_called_with("/images/some/very/very/deep/*")
        self.assertEqual(result, [])
