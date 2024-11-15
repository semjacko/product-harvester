from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langchain_core.runnables.utils import Output
from langsmith import RunTree

from product_harvester.product import Product


class ProcessingError(Exception):
    def __init__(self, input: dict, msg: str, detailed_msg: str):
        self.input = input
        self.msg = msg
        self.detailed_msg = detailed_msg


class ProcessingResult:
    def __init__(self, products: list[Product], errors: list[ProcessingError]):
        self._products = products
        self._errors = errors

    @property
    def products(self) -> list[Product]:
        return self._products

    @property
    def errors(self) -> list[ProcessingError]:
        return self._errors


class ImageProcessor:
    def process(self, image_links: list[str]) -> ProcessingResult:
        raise NotImplementedError()


class _PriceTagProcessingResult(ProcessingResult):
    def __init__(self, chain_stage_descriptions: list[str]):
        super().__init__([], [])
        self._chain_stage_descriptions = chain_stage_descriptions

    def set_products_from_outputs(self, outputs: list[Output]):
        self._products = [product for product in outputs if isinstance(product, Product)]

    def add_error_from_run_tree(self, run_tree: RunTree):
        for stage_index, stage in enumerate(run_tree.child_runs):
            if stage.error:
                msg = self._make_stage_error_msg(stage_index)
                self._errors.append(ProcessingError(run_tree.inputs, msg, stage.error))

    def _make_stage_error_msg(self, stage_index: int) -> str:
        if stage_index >= len(self._chain_stage_descriptions):
            return "Unknown failure"
        return f"Failed during {self._chain_stage_descriptions[stage_index]}"


class PriceTagImageProcessor(ImageProcessor):
    _prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
Extract product data from the image of a product price tag.
As a category, use from these: "voda", "jedlo", "ostatné".
{format_instructions}
""",
            ),
            (
                "user",
                [
                    {
                        "type": "image_url",
                        "image_url": {"url": "{image_link}"},
                    },
                    {"type": "text", "text": "process_image"},
                ],
            ),
        ]
    )
    _parser = PydanticOutputParser(pydantic_object=Product)

    def __init__(self, model: BaseChatModel, max_concurrency: int = 4):
        self._model = model
        self._max_concurrency = max_concurrency
        self._chain = self._prompt | self._model | self._parser
        self._chain_stage_descriptions = [
            "prompt preparation",
            "extracting data from image",
            "parsing of extracted data from image",
        ]

    def process(self, image_links: list[str]) -> ProcessingResult:
        input_data = [self._make_input_data(image_link) for image_link in image_links]
        result = _PriceTagProcessingResult(self._chain_stage_descriptions)
        chain = self._chain.with_listeners(on_error=result.add_error_from_run_tree)
        outputs = chain.batch(input_data, RunnableConfig(max_concurrency=self._max_concurrency), return_exceptions=True)
        result.set_products_from_outputs(outputs)
        return result

    def _make_input_data(self, image_link: str) -> dict[str, str]:
        return {
            "image_link": image_link,
            "format_instructions": self._parser.get_format_instructions(),
        }
