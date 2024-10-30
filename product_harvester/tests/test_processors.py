from typing import List
from unittest import TestCase

from langchain_core.exceptions import OutputParserException
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import BaseMessage
from pydantic import TypeAdapter

from product_harvester.processors import PriceTagImageProcessor
from product_harvester.product import Product


class TestPriceTagImageProcessor(TestCase):
    def test_process_success(self):
        want_product = Product(name="Banana", price=3.45, qty=1, qty_unit="kg")
        responses = self._make_responses(want_product.model_dump_json())
        fake_model = FakeMessagesListChatModel(responses=responses)
        product = PriceTagImageProcessor(fake_model).process(encoded_image="<image>")
        self.assertEqual(want_product, product)

    def test_process_invalid_product_output_json(self):
        responses = self._make_responses("{wat")
        fake_model = FakeMessagesListChatModel(responses=responses)
        with self.assertRaises(OutputParserException):
            PriceTagImageProcessor(fake_model).process(encoded_image="<image>")

    def test_process_incomplete_product_output(self):
        # language=JSON
        responses = self._make_responses('{"name":"Banana"}')
        fake_model = FakeMessagesListChatModel(responses=responses)
        with self.assertRaises(OutputParserException):
            PriceTagImageProcessor(fake_model).process(encoded_image="<image>")

    def test_process_batch_success(self):
        # language=JSON
        want_products = TypeAdapter(List[Product]).validate_json(
            """
            [
                {"name": "Banana", "price": 3.45, "qty": 1, "qty_unit": "kg"},
                {"name": "Bread", "price": 2.5, "qty": 3, "qty_unit": "pcs"},
                {"name": "Milk", "price": 4.45, "qty": 1000, "qty_unit": "ml"}
            ]
            """
        )
        contents = [product.model_dump_json() for product in want_products]
        responses = self._make_responses(*contents)
        fake_model = FakeMessagesListChatModel(responses=responses)
        products = PriceTagImageProcessor(fake_model).process_batch(
            encoded_images=["<image1>", "<image2>", "<image3>"]
        )
        self.assertEqual(want_products, products)

    def test_process_batch_invalid_products_output_json(self):
        valid_product = Product(name="Banana", price=3.45, qty=1, qty_unit="kg")
        responses = self._make_responses(valid_product.model_dump_json(), "{wat")
        fake_model = FakeMessagesListChatModel(responses=responses)
        with self.assertRaises(OutputParserException):
            PriceTagImageProcessor(fake_model).process_batch(
                encoded_images=["<image1>", "<image2>"]
            )

    def test_process_batch_incomplete_product_output(self):
        valid_product = Product(name="Banana", price=3.45, qty=1, qty_unit="kg")
        # language=JSON
        responses = self._make_responses(
            '{"name":"Bread"}',
            valid_product.model_dump_json(),
        )
        fake_model = FakeMessagesListChatModel(responses=responses)
        with self.assertRaises(OutputParserException):
            PriceTagImageProcessor(fake_model).process_batch(
                encoded_images=["<image1>", "<image2>"]
            )

    @staticmethod
    def _make_responses(*contents: str) -> list[BaseMessage]:
        return [BaseMessage(content=content, type="str") for content in contents]
