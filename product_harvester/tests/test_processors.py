from typing import List
from unittest import TestCase
from unittest.mock import Mock

from langchain_core.language_models.fake_chat_models import FakeListChatModelError, FakeMessagesListChatModel
from langchain_core.messages import BaseMessage
from pydantic import TypeAdapter

from product_harvester.processors import ImageProcessor, PriceTagImageProcessor, ProcessingResult
from product_harvester.product import Product


class TestImageProcessor(TestCase):
    def test_process_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            ImageProcessor().process(["/image.png"])


class TestPriceTagImageProcessor(TestCase):
    class _TestProcessingError:
        def __init__(self, input_image_link: str, error: str):
            self.input_image_link = input_image_link
            self.error = error

    def setUp(self):
        self._fake_model = FakeMessagesListChatModel(responses=[])
        self._processor = PriceTagImageProcessor(self._fake_model)

    def _assert_result(self, result: ProcessingResult, products: list[Product], errors: list[_TestProcessingError]):
        self.assertEqual(products, result.products)
        self.assertEqual(len(errors), len(result.errors))
        for result_error, want_error in zip(result.errors, errors):
            self.assertIn(want_error.error, result_error.error)
            self.assertEqual(result_error.input["image_link"], want_error.input_image_link)

    def test_process_success(self):
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
        self._fake_model.responses = self._prepare_fake_responses(contents)
        result = self._processor.process(image_links=["/image1.jpg", "/image2.png", "/image3.jpg"])
        self._assert_result(result, mock_products, [])

    def test_process_empty_response_from_model(self):
        self._fake_model.responses = self._prepare_fake_responses([""] * 2)
        result = self._processor.process(image_links=["/image1.jpg", "/image2.png"])
        self._assert_result(
            result,
            [],
            [
                self._TestProcessingError(input_image_link="/image1.jpg", error="OutputParserException"),
                self._TestProcessingError(input_image_link="/image2.png", error="OutputParserException"),
            ],
        )

    def test_process_invalid_response_json_from_model(self):
        mock_valid_product = Product(name="Banana", price=3.45, qty=1, qty_unit="kg")
        self._fake_model.responses = self._prepare_fake_responses(
            [
                mock_valid_product.model_dump_json(),
                "{wat",
            ]
        )
        result = PriceTagImageProcessor(self._fake_model).process(image_links=["/image1.jpg", "/image2.jpg"])
        self._assert_result(
            result,
            [mock_valid_product],
            [self._TestProcessingError(input_image_link="/image2.jpg", error="OutputParserException")],
        )

    def test_process_incomplete_product_response_from_model(self):
        mock_valid_product = Product(name="Banana", price=3.45, qty=1, qty_unit="kg")
        # language=JSON
        self._fake_model.responses = self._prepare_fake_responses(
            [
                '{"name":"Bread", "price":3.45}',
                mock_valid_product.model_dump_json(),
                '{"qty":2, "qty_unit":"pcs"}',
            ]
        )
        result = PriceTagImageProcessor(self._fake_model).process(
            image_links=["/image1.jpeg", "/image2.jpg", "/image3.jpg"]
        )
        self._assert_result(
            result,
            [mock_valid_product],
            [
                self._TestProcessingError(input_image_link="/image1.jpeg", error="OutputParserException"),
                self._TestProcessingError(input_image_link="/image3.jpg", error="OutputParserException"),
            ],
        )

    def test_process_model_exception(self):
        self._fake_model = Mock()
        self._fake_model.side_effect = FakeListChatModelError()
        result = PriceTagImageProcessor(self._fake_model).process(image_links=["/image1.png"])
        self._assert_result(
            result,
            [],
            [self._TestProcessingError(input_image_link="/image1.png", error="FakeListChatModelError")],
        )

    @staticmethod
    def _prepare_fake_responses(contents: list[str]):
        return [BaseMessage(content=content, type="str") for content in contents]
