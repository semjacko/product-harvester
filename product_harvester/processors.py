from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langchain_core.runnables.utils import Output
from langsmith import RunTree

from product_harvester.product import Product


class ProcessingError(Exception):
    def __init__(self, input: dict, error: str):
        self.input = input
        self.error = error


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
    def __init__(self):
        super().__init__([], [])

    def set_products_from_outputs(self, outputs: list[Output]):
        self._products = [product for product in outputs if isinstance(product, Product)]

    def add_error_from_run_tree(self, run_tree: RunTree):
        self._errors.append(ProcessingError(run_tree.inputs, run_tree.error))


class PriceTagImageProcessor(ImageProcessor):
    _prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
From the image of a product price tag, extract the product's name, price, quantity, and unit of quantity.
Example quantity units are: l, ml, g, kg, pcs.
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

    def __init__(self, model: BaseChatModel):
        self._model = model

    def process(self, image_links: list[str]) -> ProcessingResult:
        input_data = [self._make_input_data(image_link) for image_link in image_links]
        result = _PriceTagProcessingResult()
        chain = self._prompt | self._model | self._parser
        chain = chain.with_listeners(on_error=result.add_error_from_run_tree)
        outputs = chain.batch(input_data, RunnableConfig(max_concurrency=4), return_exceptions=True)
        result.set_products_from_outputs(outputs)
        return result

    def _make_input_data(self, image_link: str) -> dict[str, str]:
        return {
            "image_link": image_link,
            "format_instructions": self._parser.get_format_instructions(),
        }
