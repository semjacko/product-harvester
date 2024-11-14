from typing import List
from unittest import TestCase
from unittest.mock import Mock, patch

from langchain_core.language_models.fake_chat_models import FakeListChatModelError, FakeMessagesListChatModel
from langchain_core.messages import BaseMessage
from pydantic import TypeAdapter

from product_harvester.processors import (
    _PriceTagProcessingResult,
    ImageProcessor,
    PriceTagImageProcessor,
    ProcessingResult,
)
from product_harvester.product import Product


class TestImageProcessor(TestCase):
    def test_process_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            ImageProcessor().process(["/image.png"])


class TestPriceTagImageProcessor(TestCase):
    class _TestProcessingError:
        def __init__(self, input_image_link: str, msg: str, detailed_msg: str):
            self.input_image_link = input_image_link
            self.msg = msg
            self.detailed_msg = detailed_msg

    def setUp(self):
        self._fake_model = FakeMessagesListChatModel(responses=[])
        self._processor = PriceTagImageProcessor(self._fake_model)

    def _assert_result(self, result: ProcessingResult, products: list[Product], errors: list[_TestProcessingError]):
        self.assertEqual(products, result.products)
        self.assertEqual(len(errors), len(result.errors))
        for result_error, want_error in zip(result.errors, errors):
            self.assertEqual(result_error.input["image_link"], want_error.input_image_link)
            self.assertEqual(want_error.msg, result_error.msg)
            self.assertIn(want_error.detailed_msg, result_error.detailed_msg)

    def test_process_success(self):
        # language=JSON
        mock_products = TypeAdapter(List[Product]).validate_json(
            """
            [
                {"name": "Banana", "price": 3.45, "qty": 1, "qty_unit": "kg", "barcode": "123", "tags": ["milk"]},
                {"name": "Bread", "price": 2.5, "qty": 3, "qty_unit": "pcs", "barcode": "abc", "brand": "Rajo"},
                {"name": "Milk", "price": 4.45, "qty": 1000, "qty_unit": "ml", "barcode": "1ac"}
            ]
            """,
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
                self._TestProcessingError(
                    input_image_link="/image1.jpg",
                    msg="Failed during parsing of extracted data from image",
                    detailed_msg="OutputParserException",
                ),
                self._TestProcessingError(
                    input_image_link="/image2.png",
                    msg="Failed during parsing of extracted data from image",
                    detailed_msg="OutputParserException",
                ),
            ],
        )

    def test_process_invalid_response_json_from_model(self):
        mock_valid_product = Product(name="Banana", price=3.45, qty=1, qty_unit="kg", barcode="abc")
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
            [
                self._TestProcessingError(
                    input_image_link="/image2.jpg",
                    msg="Failed during parsing of extracted data from image",
                    detailed_msg="OutputParserException",
                )
            ],
        )

    def test_process_incomplete_product_response_from_model(self):
        mock_valid_product = Product(name="Banana", price=3.45, qty=1, qty_unit="kg", barcode="123")
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
                self._TestProcessingError(
                    input_image_link="/image1.jpeg",
                    msg="Failed during parsing of extracted data from image",
                    detailed_msg="OutputParserException",
                ),
                self._TestProcessingError(
                    input_image_link="/image3.jpg",
                    msg="Failed during parsing of extracted data from image",
                    detailed_msg="OutputParserException",
                ),
            ],
        )

    def test_process_model_exception(self):
        self._fake_model = Mock()
        self._fake_model.side_effect = FakeListChatModelError()
        result = PriceTagImageProcessor(self._fake_model).process(image_links=["/image1.png"])
        self._assert_result(
            result,
            [],
            [
                self._TestProcessingError(
                    input_image_link="/image1.png",
                    msg="Failed during extracting data from image",
                    detailed_msg="FakeListChatModelError",
                )
            ],
        )

    def test_process_unknown_stage_exception(self):
        self._fake_model = Mock()
        self._fake_model.side_effect = FakeListChatModelError()

        # Patch instantiation of the object, so it will be created with description just for the 1st (prompt) stage
        mock_result = _PriceTagProcessingResult(["a"])
        with patch("product_harvester.processors._PriceTagProcessingResult", return_value=mock_result):
            result = PriceTagImageProcessor(self._fake_model).process(image_links=["/image1.png"])
            self._assert_result(
                result,
                [],
                [
                    self._TestProcessingError(
                        input_image_link="/image1.png",
                        msg="Unknown failure",
                        detailed_msg="FakeListChatModelError",
                    )
                ],
            )

    @staticmethod
    def _prepare_fake_responses(contents: list[str]):
        return [BaseMessage(content=content, type="str") for content in contents]
