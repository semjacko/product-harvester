from typing import List
from unittest import TestCase
from unittest.mock import Mock, patch, MagicMock, mock_open

import numpy as np
from langchain_core.language_models import BaseChatModel
from langchain_core.language_models.fake_chat_models import FakeListChatModelError, FakeMessagesListChatModel
from langchain_core.messages import BaseMessage
from pydantic import TypeAdapter

from product_harvester.image import Image
from product_harvester.processors import (
    _PriceTagProcessingResult,
    ImageProcessor,
    PriceTagImageProcessor,
    ProcessingResult,
    _BarcodeReader,
)
from product_harvester.product import Product


class TestImageProcessor(TestCase):
    def test_process_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            ImageProcessor().process([Image(id="image", data="/image.png")])


class TestPriceTagImageProcessor(TestCase):
    class _TestProcessingError:
        def __init__(self, input_image: str, msg: str, detailed_msg: str):
            self.input_image = input_image
            self.msg = msg
            self.detailed_msg = detailed_msg

    def _assert_result(self, result: ProcessingResult, products: list[Product], errors: list[_TestProcessingError]):
        self.assertEqual(products, result.products)
        self.assertEqual(len(errors), len(result.errors))
        for result_error, want_error in zip(result.errors, errors):
            self.assertEqual(result_error.input["image"], want_error.input_image)
            self.assertEqual(want_error.msg, result_error.msg)
            self.assertIn(want_error.detailed_msg, result_error.detailed_msg)

    def test_process_success(self):
        # TODO: Assert data flow (inputs) between chain stages
        # language=JSON
        mock_products = TypeAdapter(List[Product]).validate_json(
            """[
    {"name": "Banana", "price": 3.45, "qty": 1, "qty_unit": "kg", "barcode": 123, "category": "fruit"},
    {"name": "Bread", "price": 2.5, "qty": 3, "qty_unit": "pcs", "barcode": 345, "brand": "Rajo", "category": "fruit"},
    {"name": "Milk", "price": 4.45, "qty": 1000, "qty_unit": "ml", "barcode": 567, "category": "milk"}
            ]""",
        )
        responses = [product.model_dump_json() for product in mock_products]
        fake_model = self._prepare_fake_model_with_responses(responses)
        processor = self._prepare_processor(fake_model)
        result = processor.process(
            images=[
                Image(id="image1", data="/image1.jpg"),
                Image(id="image2", data="/image2.jpg"),
                Image(id="image3", data="/image3.jpg"),
            ]
        )
        self._assert_result(result, mock_products, [])

    def test_process_success_adjust_barcode(self):
        mock_product = Product(name="Banana", price=3.45, qty=1, qty_unit="kg", barcode=123, category="fruit")
        fake_model = self._prepare_fake_model_with_responses([mock_product.model_dump_json()])
        processor = self._prepare_processor(fake_model)
        processor._barcode_reader.read_barcode.return_value = 45678
        result = processor.process(images=[Image(id="image1", data="/image1.jpg")])
        mock_product.barcode = 45678
        self._assert_result(result, [mock_product], [])

    def test_process_adjust_barcode_failure(self):
        mock_product = Product(name="Banana", price=3.45, qty=1, qty_unit="kg", barcode=123, category="fruit")
        fake_model = self._prepare_fake_model_with_responses([mock_product.model_dump_json()])
        processor = self._prepare_processor(fake_model)
        processor._barcode_reader.read_barcode.side_effect = ValueError("wat")
        result = processor.process(images=[Image(id="image1", data="/image1.jpg")])
        self._assert_result(result, [mock_product], [])

    def test_process_empty_response_from_model(self):
        fake_model = self._prepare_fake_model_with_responses([""] * 2)
        processor = self._prepare_processor(fake_model)
        result = processor.process(
            images=[Image(id="image1", data="/image1.jpg"), Image(id="image2", data="/image2.png")]
        )
        self._assert_result(
            result,
            [],
            [
                self._TestProcessingError(
                    input_image="/image1.jpg",
                    msg="Failed during parsing of extracted data from image",
                    detailed_msg="OutputParserException",
                ),
                self._TestProcessingError(
                    input_image="/image2.png",
                    msg="Failed during parsing of extracted data from image",
                    detailed_msg="OutputParserException",
                ),
            ],
        )

    def test_process_invalid_response_json_from_model(self):
        mock_valid_product = Product(name="Banana", price=3.45, qty=1, qty_unit="kg", barcode=123, category="fruit")
        fake_model = self._prepare_fake_model_with_responses(
            [
                mock_valid_product.model_dump_json(),
                "{wat",
            ]
        )
        processor = self._prepare_processor(fake_model)
        result = processor.process(
            images=[Image(id="image1", data="/image1.jpg"), Image(id="image2", data="/image2.jpg")]
        )
        self._assert_result(
            result,
            [mock_valid_product],
            [
                self._TestProcessingError(
                    input_image="/image2.jpg",
                    msg="Failed during parsing of extracted data from image",
                    detailed_msg="OutputParserException",
                )
            ],
        )

    def test_process_incomplete_product_response_from_model(self):
        mock_valid_product = Product(name="Banana", price=3.45, qty=1, qty_unit="kg", barcode=123, category="fruit")
        # language=JSON
        fake_model = self._prepare_fake_model_with_responses(
            [
                '{"name":"Bread", "price":3.45}',
                mock_valid_product.model_dump_json(),
                '{"qty":2, "qty_unit":"pcs"}',
            ]
        )
        processor = self._prepare_processor(fake_model)
        result = processor.process(
            images=[
                Image(id="image1", data="/image1.jpeg"),
                Image(id="image2", data="/image2.jpg"),
                Image(id="image3", data="/image3.jpg"),
            ]
        )
        self._assert_result(
            result,
            [mock_valid_product],
            [
                self._TestProcessingError(
                    input_image="/image1.jpeg",
                    msg="Failed during parsing of extracted data from image",
                    detailed_msg="OutputParserException",
                ),
                self._TestProcessingError(
                    input_image="/image3.jpg",
                    msg="Failed during parsing of extracted data from image",
                    detailed_msg="OutputParserException",
                ),
            ],
        )

    def test_process_model_exception(self):
        fake_model = Mock()
        fake_model.side_effect = FakeListChatModelError()
        processor = self._prepare_processor(fake_model)
        result = processor.process(images=[Image(id="image1", data="/image1.png")])
        self._assert_result(
            result,
            [],
            [
                self._TestProcessingError(
                    input_image="/image1.png",
                    msg="Failed during extracting data from image",
                    detailed_msg="FakeListChatModelError",
                )
            ],
        )

    def test_process_unknown_stage_exception(self):
        fake_model = Mock()
        fake_model.side_effect = FakeListChatModelError()
        processor = PriceTagImageProcessor(fake_model, max_concurrency=1)

        # Patch instantiation of the object, so it will be created with description just for the 1st (prompt) stage
        mock_result = _PriceTagProcessingResult(["a"])
        with patch("product_harvester.processors._PriceTagProcessingResult", return_value=mock_result):
            result = processor.process(images=[Image(id="image1", data="/image1.png")])
            self._assert_result(
                result,
                [],
                [
                    self._TestProcessingError(
                        input_image="/image1.png",
                        msg="Unknown failure",
                        detailed_msg="FakeListChatModelError",
                    )
                ],
            )

    @staticmethod
    def _prepare_fake_model_with_responses(responses: list[str]):
        return FakeMessagesListChatModel(
            responses=[BaseMessage(content=response, type="str") for response in responses]
        )

    @staticmethod
    def _prepare_processor(model: BaseChatModel) -> PriceTagImageProcessor:
        processor = PriceTagImageProcessor(model, max_concurrency=1)
        processor._barcode_reader = Mock()
        processor._barcode_reader.read_barcode.return_value = None
        return processor


class TestBarcodeReader(TestCase):

    @patch("product_harvester.processors.decode")
    @patch("product_harvester.processors.cv2.imdecode")
    @patch("product_harvester.processors.base64.b64decode", return_value=b"test_data")
    def test_read_barcode_from_base64(self, mock_bas64_decode, mock_imdecode, mock_decode):
        mock_imdecode.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_barcode = MagicMock()
        mock_barcode.data.decode.return_value = "123456"
        mock_decode.return_value = [mock_barcode]
        barcode = _BarcodeReader().read_barcode("data:image/png;base64,test_base64_image")
        self.assertEqual(barcode, 123456)
        mock_bas64_decode.assert_called_once_with("test_base64_image")
        mock_imdecode.assert_called_once()
        mock_decode.assert_called_once()

    @patch("product_harvester.processors.decode")
    @patch("product_harvester.processors.cv2.imdecode")
    @patch("product_harvester.processors.requests.get")
    def test_read_barcode_from_url(self, mock_requests_get, mock_imdecode, mock_decode):
        mock_response = MagicMock()
        mock_response.content = b"test_data"
        mock_requests_get.return_value = mock_response
        mock_imdecode.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_barcode = MagicMock()
        mock_barcode.data.decode.return_value = "789012"
        mock_decode.return_value = [mock_barcode]
        barcode = _BarcodeReader().read_barcode("https://example.com/image.png")
        self.assertEqual(barcode, 789012)
        mock_requests_get.assert_called_once_with("https://example.com/image.png")
        mock_imdecode.assert_called_once()
        mock_decode.assert_called_once()

    @patch("product_harvester.processors.decode")
    @patch("product_harvester.processors.cv2.imdecode")
    @patch("builtins.open", new_callable=mock_open, read_data=b"fake_image_bytes")
    def test_read_barcode_from_file(self, _mock_open, mock_imdecode, mock_decode):
        mock_imdecode.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_barcode = MagicMock()
        mock_barcode.data.decode.return_value = "654321"
        mock_decode.return_value = [mock_barcode, "asddf123"]
        barcode = _BarcodeReader().read_barcode("/path/to/image.png")
        self.assertEqual(barcode, 654321)
        _mock_open.assert_called_once_with("/path/to/image.png", "rb")
        mock_imdecode.assert_called_once()
        mock_decode.assert_called_once()

    @patch("product_harvester.processors.decode")
    @patch("product_harvester.processors.cv2.imdecode")
    @patch("product_harvester.processors.base64.b64decode", return_value=b"test_data")
    def test_read_barcode_empty(self, mock_bas64_decode, mock_imdecode, mock_decode):
        mock_imdecode.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_decode.return_value = []
        barcode = _BarcodeReader().read_barcode("data:image/png;base64,test_base64_image")
        self.assertIsNone(barcode)
        mock_bas64_decode.assert_called_once_with("test_base64_image")
        mock_imdecode.assert_called_once()
        mock_decode.assert_called_once()

    @patch("product_harvester.processors.decode")
    @patch("product_harvester.processors.cv2.imdecode")
    @patch("product_harvester.processors.base64.b64decode", return_value=b"test_data")
    def test_read_barcode_non_numeric(self, mock_bas64_decode, mock_imdecode, mock_decode):
        mock_imdecode.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_barcode = MagicMock()
        mock_barcode.data.decode.return_value = "123asd456"
        mock_decode.return_value = [mock_barcode]
        with self.assertRaises(ValueError):
            _BarcodeReader().read_barcode("data:image/png;base64,test_base64_image")
        mock_bas64_decode.assert_called_once_with("test_base64_image")
        mock_imdecode.assert_called_once()
        mock_decode.assert_called_once()
