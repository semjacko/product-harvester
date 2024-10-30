from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig, RunnableSerializable

from product_harvester.product import Product


class ImageProcessor:
    def process(self, encoded_image: str) -> Product:
        raise NotImplementedError()

    def process_batch(self, encoded_image: list[str]) -> list[Product]:
        raise NotImplementedError()


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
                        "image_url": {"url": "data:image/jpeg;base64,{image_data}"},
                    },
                    {"type": "text", "text": "process_image"},
                ],
            ),
        ]
    )
    _parser = PydanticOutputParser(pydantic_object=Product)

    def __init__(self, model: BaseChatModel):
        self._model = model

    def process(self, encoded_image: str) -> Product:
        chain = self._prepare_chain()
        input_data = self._make_input_data(encoded_image)
        product = chain.invoke(input_data)
        return product

    def process_batch(self, encoded_images: list[str]) -> list[Product]:
        chain = self._prepare_chain()
        input_data = [
            self._make_input_data(encoded_image) for encoded_image in encoded_images
        ]
        products = chain.batch(input_data, RunnableConfig(max_concurrency=4))
        return products

    def _prepare_chain(self) -> RunnableSerializable[dict, Any]:
        return self._prompt | self._model | self._parser

    def _make_input_data(self, encoded_image: str) -> dict[str, str]:
        return {
            "image_data": encoded_image,
            "format_instructions": self._parser.get_format_instructions(),
        }
