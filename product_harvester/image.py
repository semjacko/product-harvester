from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

from product_harvester.product import Product


class ImageMeta(ABC):
    def __init__(self, metadata: dict[str, Any]):
        self._metadata = metadata

    def __getitem__(self, item) -> Any | None:
        return self._metadata.get(item)

    @abstractmethod
    def adjust_product(self, product: Product) -> None: ...


class NoImageMeta(ImageMeta):
    def __init__(self):
        super().__init__({})

    def adjust_product(self, product: Product) -> None:
        pass


class Image(BaseModel):
    id: str
    data: str
    meta: ImageMeta = NoImageMeta()

    class Config:
        arbitrary_types_allowed = True
