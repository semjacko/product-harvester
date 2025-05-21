from typing import Literal, Optional

import requests
from pydantic import BaseModel, TypeAdapter


class UsetriAPIProductDetail(BaseModel):
    barcode: str
    name: str
    amount: float
    brand: Optional[str]
    unit: Literal["l", "kg", "pcs"]
    category_id: int
    source_image: str
    is_barcode_checked: bool


class UsetriAPIProduct(BaseModel):
    product: UsetriAPIProductDetail
    price: float
    shop_id: int


class UsetriAPICategory(BaseModel):
    id: int
    name: str


class UsetriClient:
    _base_url: str = "https://usetri-api.livelypond-189c8f13.polandcentral.azurecontainerapps.io"
    _products_endpoint = f"{_base_url}/products"
    _categories_endpoint = f"{_base_url}/categories"

    def __init__(self, token: str):
        self._token = token
        self._session = requests.Session()
        self._cached_categories: list[UsetriAPICategory] = []

    def import_product(self, product: UsetriAPIProduct):
        data = product.model_dump()
        headers = {"user-id": self._token}
        response = self._session.post(self._products_endpoint, json=data, headers=headers)
        response.raise_for_status()

    def get_categories(self) -> list[UsetriAPICategory]:
        if not self._cached_categories:
            self._cached_categories = self._get_categories()
        return self._cached_categories

    def _get_categories(self) -> list[UsetriAPICategory]:
        response = self._session.get(self._categories_endpoint)
        response.raise_for_status()
        raw_categories = response.json().get("categories", [])
        return TypeAdapter(list[UsetriAPICategory]).validate_python(raw_categories)
