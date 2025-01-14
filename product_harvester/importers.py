from typing import Literal, Self, ClassVar

import requests
from pydantic import BaseModel, Field

from product_harvester.product import Product


class ProductsImporter:
    def import_product(self, product: Product):
        raise NotImplementedError()


class StdOutProductsImporter(ProductsImporter):
    def import_product(self, product: Product):
        print(product)


class _DoLacnaAPIProductDetail(BaseModel):
    barcode: int = Field(strict=True, gt=0)
    name: str = Field(strict=True, min_length=1)
    amount: float = Field(strict=True, gt=0)
    brand: str = Field(strict=True, default="")
    unit: Literal["l", "kg", "pcs"] = Field()
    category_id: int = Field(strict=True, gt=0)


class _DoLacnaAPIProduct(BaseModel):
    _category_id_mapping: ClassVar = {
        "voda": 1,
        "jedlo": 2,
        "ostatné": 3,
    }

    product: _DoLacnaAPIProductDetail = Field(strict=True)
    price: float = Field(strict=True, gt=0)
    shop_id: int = Field(strict=True, gt=0)

    @classmethod
    def from_product(cls, product: Product, shop_id: int) -> Self:
        unit, amount = cls._convert_unit(product)
        return _DoLacnaAPIProduct(
            product=_DoLacnaAPIProductDetail(
                barcode=product.barcode,
                name=product.name,
                amount=amount,
                brand=product.brand,
                unit=unit,
                category_id=cls._convert_category_to_id(product.category),
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

    @classmethod
    def _convert_category_to_id(cls, category: str) -> int:
        return cls._category_id_mapping.get(category, 0)


class _DoLacnaClient:
    _base_url: str = "https://dolacna-admin-api.default.offli.eu"
    _import_endpoint = f"{_base_url}/products"

    def __init__(self, token: str):
        self._token = token
        self._session = requests.Session()

    def import_product(self, product: _DoLacnaAPIProduct):
        data = product.model_dump()
        headers = {"user-id": self._token}
        response = self._session.post(self._import_endpoint, json=data, headers=headers)
        response.raise_for_status()


class DoLacnaAPIProductsImporter(ProductsImporter):
    def __init__(self, token: str, shop_id: int):
        self._shop_id = shop_id
        self._client = _DoLacnaClient(token)

    def import_product(self, product: Product):
        try:
            imported_product = _DoLacnaAPIProduct.from_product(product, shop_id=self._shop_id)
            self._client.import_product(imported_product)
        except Exception as e:
            raise e
