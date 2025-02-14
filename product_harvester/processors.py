import base64
from typing import NamedTuple

import cv2
import numpy as np
import requests
from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langchain_core.runnables.utils import Output
from langsmith import RunTree
from pyzbar.pyzbar import decode

from product_harvester.image import Image
from product_harvester.product import Product


class ProcessingError(Exception):
    def __init__(self, msg: str, detailed_msg: str = ""):
        self.msg = msg
        self.detailed_msg = detailed_msg


class PerImageProcessingResult(NamedTuple):
    input_image: Image
    output: Product | ProcessingError

    @property
    def is_error(self) -> bool:
        return isinstance(self.output, ProcessingError)


class ProcessingResult:
    def __init__(self, results: list[PerImageProcessingResult]):
        self._results = results

    @property
    def product_results(self) -> list[PerImageProcessingResult]:
        return [result for result in self._results if not result.is_error]

    @property
    def error_results(self) -> list[PerImageProcessingResult]:
        return [result for result in self._results if result.is_error]


class ImageProcessor:
    def process(self, images: list[Image]) -> ProcessingResult:
        raise NotImplementedError()


class _PriceTagProcessingResult(ProcessingResult):
    def __init__(self, chain_stage_descriptions: list[str]):
        super().__init__([])
        self._chain_stage_descriptions = chain_stage_descriptions

    def set_products_from_outputs(self, inputs: list[Image], outputs: list[Output]):
        if len(inputs) != len(outputs):
            raise ProcessingError(msg="Number of inputs and outputs do not match")
        self._results.extend(
            [
                PerImageProcessingResult(input_image=Image(id=input_image.id, data=input_image.data), output=output)
                for input_image, output in zip(inputs, outputs)
                if isinstance(output, Product)
            ]
        )

    def add_error_from_run_tree(self, run_tree: RunTree):
        for stage_index, stage in enumerate(run_tree.child_runs):
            if stage.error:
                msg = self._make_stage_error_msg(stage_index)
                err = ProcessingError(msg, stage.error)
                self._results.append(
                    PerImageProcessingResult(
                        input_image=Image(id=run_tree.inputs["image_id"], data=run_tree.inputs["image"]), output=err
                    )
                )

    def _make_stage_error_msg(self, stage_index: int) -> str:
        if stage_index >= len(self._chain_stage_descriptions):
            return "Unknown failure"
        return f"Failed during {self._chain_stage_descriptions[stage_index]}"


class _BarcodeReader:
    def __init__(self):
        self._current_image_data = ""

    def read_barcode(self, image_data: str) -> int | None:
        self._current_image_data = image_data
        image = self._load_image()
        barcodes = decode(image)
        return int(barcodes[0].data.decode("utf-8")) if barcodes else None

    def _load_image(self) -> np.ndarray:
        if self._is_base64_encoded():
            image_bytes = self._image_bytes_from_base64()
        elif self._is_url():
            image_bytes = self._image_bytes_from_url()
        else:
            image_bytes = self._image_bytes_from_path()
        image = self._load_image_from_bytes(image_bytes)
        return self._image_to_grayscale(image)

    def _is_base64_encoded(self) -> bool:
        return self._current_image_data.startswith("data:image/")

    def _image_bytes_from_base64(self) -> bytes:
        base64_data = self._current_image_data.split(",", 1)[1]
        return base64.b64decode(base64_data)

    def _is_url(self) -> bool:
        return self._current_image_data.startswith("http")

    def _image_bytes_from_url(self) -> bytes:
        response = requests.get(self._current_image_data)
        response.raise_for_status()
        return response.content

    def _image_bytes_from_path(self) -> bytes:
        with open(self._current_image_data, "rb") as image_file:
            return image_file.read()

    @staticmethod
    def _load_image_from_bytes(image_bytes) -> np.ndarray:
        arr = np.frombuffer(image_bytes, np.uint8)
        return cv2.imdecode(arr, cv2.IMREAD_COLOR)

    @staticmethod
    def _image_to_grayscale(image: np.ndarray) -> np.ndarray:
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


class PriceTagImageProcessor(ImageProcessor):
    _prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
Extract product data from the image of a product price tag.
As a category, use from these: {categories}.
{format_instructions}
""",
            ),
            (
                "user",
                [
                    {
                        "type": "image_url",
                        "image_url": {"url": "{image}"},
                    },
                    {"type": "text", "text": "process_image"},
                ],
            ),
        ]
    )
    _parser = PydanticOutputParser(pydantic_object=Product)

    def __init__(self, model: BaseChatModel, categories: list[str] | None = None, max_concurrency: int = 4):
        categories = categories if categories is not None else ["food", "drinks", "other"]
        self._model = model
        self._categories_instructions = ",".join(categories)
        self._max_concurrency = max_concurrency
        self._parser_format_instructions = self._parser.get_format_instructions()
        self._chain = self._prompt | self._model | self._parser
        self._chain_stage_descriptions = [
            "prompt preparation",
            "extracting data from image",
            "parsing of extracted data from image",
        ]
        self._barcode_reader = _BarcodeReader()

    def process(self, images: list[Image]) -> ProcessingResult:
        input_data = [self._make_input_data(image) for image in images]
        result = _PriceTagProcessingResult(self._chain_stage_descriptions)
        chain = self._chain.with_listeners(on_error=result.add_error_from_run_tree)
        outputs = chain.batch(input_data, RunnableConfig(max_concurrency=self._max_concurrency), return_exceptions=True)
        result.set_products_from_outputs(images, outputs)
        self._adjust_barcodes(result)
        return result

    def _make_input_data(self, image: Image) -> dict[str, str]:
        return {
            "image": image.data,
            "image_id": image.id,
            "format_instructions": self._parser_format_instructions,
            "categories": self._categories_instructions,
        }

    def _adjust_barcodes(self, result: _PriceTagProcessingResult):
        for product_result in result.product_results:
            self._adjust_barcode(product_result)

    def _adjust_barcode(self, result: PerImageProcessingResult):
        image_data = result.input_image.data
        product = result.output
        try:
            barcode = self._barcode_reader.read_barcode(image_data)
            if barcode:
                product.barcode = barcode
        except Exception:
            return
