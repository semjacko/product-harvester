from typing import Literal

from pydantic import BaseModel, Field


class Product(BaseModel):
    name: str = Field(strict=True, min_length=1)
    qty: float = Field(strict=True, gt=0)
    qty_unit: Literal["l", "ml", "kg", "g", "pcs"] = Field()
    price: float = Field(strict=True, gt=0)
    barcode: int = Field(strict=True, gt=-1, default=0)
    brand: str = Field(strict=True, default="")
    category: str = Field(strict=True, min_length=1)
