from typing import Literal

import requests
from pydantic import BaseModel, Field, TypeAdapter


class DoLacnaAPIProductDetail(BaseModel):
    barcode: int = Field(strict=True, gt=0)
    name: str = Field(strict=True, min_length=1)
    amount: float = Field(strict=True, gt=0)
    brand: str = Field(strict=True, default="")
    unit: Literal["l", "kg", "pcs"] = Field()
    category_id: int = Field(strict=True, gt=0)


class DoLacnaAPIProduct(BaseModel):
    product: DoLacnaAPIProductDetail = Field(strict=True)
    price: float = Field(strict=True, gt=0)
    shop_id: int = Field(strict=True, gt=0)


class DoLacnaAPICategory(BaseModel):
    id: int = Field(strict=True)
    name: str = Field(strict=True)


class DoLacnaClient:
    _base_url: str = "https://dolacna-admin-api.default.offli.eu"
    _products_endpoint = f"{_base_url}/products"
    _categories_endpoint = f"{_base_url}/categories"

    def __init__(self, token: str):
        self._token = token
        self._session = requests.Session()
        self._cached_categories: list[DoLacnaAPICategory] = []

    def import_product(self, product: DoLacnaAPIProduct):
        data = product.model_dump()
        headers = {"user-id": self._token}
        response = self._session.post(self._products_endpoint, json=data, headers=headers)
        response.raise_for_status()

    def get_categories(self) -> list[DoLacnaAPICategory]:
        if not self._cached_categories:
            self._cached_categories = self._get_categories()
        return self._cached_categories

    def _get_categories(self) -> list[DoLacnaAPICategory]:
        response = self._session.get(self._categories_endpoint)
        response.raise_for_status()
        raw_categories = response.json().get("categories", [])
        return TypeAdapter(list[DoLacnaAPICategory]).validate_python(raw_categories)
