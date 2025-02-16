from typing import Literal, Self

from pydantic import Field

from product_harvester.clients.dolacna_api_client import DoLacnaAPIProduct, DoLacnaAPIProductDetail, DoLacnaClient
from product_harvester.product import Product


class ImportedProduct(Product):
    source_image_id: str = Field(strict=True, default="")

    @classmethod
    def from_product(cls, product: Product, source_image_id: str) -> Self:
        return ImportedProduct(**product.model_dump(), source_image_id=source_image_id)


class ProductsImporter:
    def import_product(self, product: ImportedProduct):
        raise NotImplementedError()


class StdOutProductsImporter(ProductsImporter):
    def import_product(self, product: ImportedProduct):
        print(product)


class _DoLacnaAPIProductFactory(DoLacnaAPIProduct):

    @classmethod
    def from_imported_product(cls, product: ImportedProduct, category_id: int, shop_id: int) -> DoLacnaAPIProduct:
        unit, amount = cls._convert_unit(product)
        return DoLacnaAPIProduct(
            product=DoLacnaAPIProductDetail(
                barcode=product.barcode,
                name=product.name,
                amount=amount,
                brand=product.brand,
                unit=unit,
                category_id=category_id,
                source_image=product.source_image_id,
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


class DoLacnaAPIProductsImporter(ProductsImporter):
    def __init__(self, client: DoLacnaClient, shop_id: int):
        self._shop_id = shop_id
        self._client = client
        self._category_to_id_mapping = self._make_category_to_id_mapping()

    @classmethod
    def from_api_token(cls, token: str, shop_id: int) -> Self:
        return DoLacnaAPIProductsImporter(DoLacnaClient(token), shop_id)

    def _make_category_to_id_mapping(self) -> dict[str, int]:
        categories = self._client.get_categories()
        return {category.name: category.id for category in categories}

    def import_product(self, product: ImportedProduct):
        try:
            category_id = self._category_to_id_mapping[product.category]
            imported_product = _DoLacnaAPIProductFactory.from_imported_product(
                product, category_id=category_id, shop_id=self._shop_id
            )
            self._client.import_product(imported_product)
        except Exception as e:
            raise e
