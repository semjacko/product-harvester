from typing import Literal

from pydantic import BaseModel, Field


class Product(BaseModel):
    name: str = Field(description="The name of the product", strict=True, min_length=1)
    qty: float = Field(description="Quantity of the product", strict=True, gt=0)
    qty_unit: Literal["l", "ml", "kg", "g", "pcs"] = Field(
        description="The unit of the quantity (l, ml, kg, g, pcs)"
    )
    price: float = Field(description="Price of the product", strict=True, gt=0)
