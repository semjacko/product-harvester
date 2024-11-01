from typing import List
from unittest import TestCase

from langchain_core.exceptions import OutputParserException
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import BaseMessage
from pydantic import TypeAdapter

from product_harvester.processors import ImageProcessor, PriceTagImageProcessor
from product_harvester.product import Product


class TestImageProcessor(TestCase):
    def test_process_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            ImageProcessor().process("<image>")

    def test_process_batch_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            ImageProcessor().process_batch(["<image1>", "<image2>"])


class TestPriceTagImageProcessor(TestCase):
    def test_process_success(self):
        mock_product = Product(name="Banana", price=3.45, qty=1, qty_unit="kg")
        mock_responses = self._make_mock_responses(mock_product.model_dump_json())
        fake_model = FakeMessagesListChatModel(responses=mock_responses)
        product = PriceTagImageProcessor(fake_model).process(encoded_image="<image>")
        self.assertEqual(product, mock_product)

    def test_process_invalid_product_output_json(self):
        mock_responses = self._make_mock_responses("{wat")
        fake_model = FakeMessagesListChatModel(responses=mock_responses)
        product = PriceTagImageProcessor(fake_model).process(encoded_image="<image>")
        self.assertIsNone(product)

    def test_process_incomplete_product_output(self):
        # language=JSON
        mock_responses = self._make_mock_responses('{"name":"Banana"}')
        fake_model = FakeMessagesListChatModel(responses=mock_responses)
        product = PriceTagImageProcessor(fake_model).process(encoded_image="<image>")
        self.assertIsNone(product)

    def test_process_batch_success(self):
        # language=JSON
        mock_products = TypeAdapter(List[Product]).validate_json(
            """
            [
                {"name": "Banana", "price": 3.45, "qty": 1, "qty_unit": "kg"},
                {"name": "Bread", "price": 2.5, "qty": 3, "qty_unit": "pcs"},
                {"name": "Milk", "price": 4.45, "qty": 1000, "qty_unit": "ml"}
            ]
            """
        )
        contents = [product.model_dump_json() for product in mock_products]
        mock_responses = self._make_mock_responses(*contents)
        fake_model = FakeMessagesListChatModel(responses=mock_responses)
        products = PriceTagImageProcessor(fake_model).process_batch(
            encoded_images=["<image1>", "<image2>", "<image3>"]
        )
        self.assertEqual(products, mock_products)

    def test_process_batch_invalid_products_output_json(self):
        mock_valid_product = Product(name="Banana", price=3.45, qty=1, qty_unit="kg")
        mock_responses = self._make_mock_responses(
            mock_valid_product.model_dump_json(), "{wat"
        )
        fake_model = FakeMessagesListChatModel(responses=mock_responses)
        products = PriceTagImageProcessor(fake_model).process_batch(
            encoded_images=["<image1>", "<image2>"]
        )
        self.assertEqual(products, [mock_valid_product])

    def test_process_batch_incomplete_product_output(self):
        mock_valid_product = Product(name="Banana", price=3.45, qty=1, qty_unit="kg")
        # language=JSON
        mock_responses = self._make_mock_responses(
            '{"name":"Bread"}',
            mock_valid_product.model_dump_json(),
        )
        fake_model = FakeMessagesListChatModel(responses=mock_responses)
        products = PriceTagImageProcessor(fake_model).process_batch(
            encoded_images=["<image1>", "<image2>"]
        )
        self.assertEqual(products, [mock_valid_product])

    @staticmethod
    def _make_mock_responses(*contents: str) -> list[BaseMessage]:
        return [BaseMessage(content=content, type="str") for content in contents]
