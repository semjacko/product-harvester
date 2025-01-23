import requests
from pydantic import TypeAdapter, BaseModel, Field
from typing import Literal, Self
from product_harvester.product import Product


class _DoLacnaAPIProductDetail(BaseModel):
    barcode: int = Field(strict=True, gt=0)
    name: str = Field(strict=True, min_length=1)
    amount: float = Field(strict=True, gt=0)
    brand: str = Field(strict=True, default="")
    unit: Literal["l", "kg", "pcs"] = Field()
    category_id: int = Field(strict=True, gt=0)


class _DoLacnaAPIProduct(BaseModel):
    product: _DoLacnaAPIProductDetail = Field(strict=True)
    price: float = Field(strict=True, gt=0)
    shop_id: int = Field(strict=True, gt=0)

    @classmethod
    def from_product(cls, product: Product, category_id: int, shop_id: int) -> Self:
        unit, amount = cls._convert_unit(product)
        return _DoLacnaAPIProduct(
            product=_DoLacnaAPIProductDetail(
                barcode=product.barcode,
                name=product.name,
                amount=amount,
                brand=product.brand,
                unit=unit,
                category_id=category_id,
            ),
            price=product.price,
            shop_id=shop_id,
        )

    @classmethod
    def _convert_unit(cls, product: Product) -> tuple[Literal["l", "kg", "pcs"], float]:
        match product.qty_unit:
            case "ml":
                return "l", product.qty / 1000
            case "g":
                return "kg", product.qty / 1000
            case _:
                return product.qty_unit, product.qty


class _DoLacnaAPICategory(BaseModel):
    id: int = Field(strict=True)
    name: str = Field(strict=True)


class _DoLacnaClient:
    _base_url: str = "https://dolacna-admin-api.default.offli.eu"
    _products_endpoint = f"{_base_url}/products"
    _categories_endpoint = f"{_base_url}/categories"

    def __init__(self, token: str):
        self._token = token
        self._session = requests.Session()

    def import_product(self, product: _DoLacnaAPIProduct):
        print("Import product client starting")
        data = product.model_dump()
        headers = {"user-id": self._token}
        response = self._session.post(self._products_endpoint, json=data, headers=headers)
        print(response.content)
        response.raise_for_status()

    def get_categories(self) -> list[_DoLacnaAPICategory]:
        response = self._session.get(self._categories_endpoint)
        response.raise_for_status()
        raw_categories = response.json().get("categories", [])
        return TypeAdapter(list[_DoLacnaAPICategory]).validate_python(raw_categories)