from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class Product(BaseModel):
    name: str = Field(strict=True, min_length=1)
    qty: float = Field(strict=True, gt=0)
    qty_unit: Literal["l", "ml", "kg", "g", "pcs"] = Field()
    price: float = Field(strict=True, gt=0)
    barcode: Optional[str] = Field(default="")
    brand: Optional[str] = Field(strict=True, default="")
    category: str = Field(strict=True, min_length=1)

    @field_validator("barcode", mode="before")
    @classmethod
    def coerce_and_validate_barcode(cls, value):
        if not value:
            return ""
        if isinstance(value, int):
            if value < 0:
                raise ValueError("Invalid value")
            return str(value)
        if isinstance(value, str):
            if not value.isdigit():
                raise ValueError("Invalid value")
            return value
        raise ValueError("Invalid type")
