from abc import ABC, abstractmethod
from pathlib import Path
from typing import Literal, Self

from pydantic import Field

from product_harvester.clients.usetri_api_client import UsetriAPIProduct, UsetriAPIProductDetail, UsetriClient
from product_harvester.image import Image
from product_harvester.product import Product


class ImportedProduct(Product):
    source_image: Image = Field(strict=True, default="")
    is_barcode_checked: bool = Field(strict=True, default=False)

    @classmethod
    def from_product(cls, product: Product, source_image: Image, is_barcode_checked: bool) -> Self:
        return ImportedProduct(**product.model_dump(), source_image=source_image, is_barcode_checked=is_barcode_checked)


class ProductsImporter(ABC):
    @abstractmethod
    def import_product(self, product: ImportedProduct): ...


class StdOutProductsImporter(ProductsImporter):
    def import_product(self, product: ImportedProduct):
        print(product)


class FileProductsImporter(ProductsImporter):
    def __init__(self, file_path: str):
        self._file_path = Path(file_path)
        self._file_path.write_text("")

    def import_product(self, product: ImportedProduct):
        with self._file_path.open("a", encoding="utf-8") as file:
            file.write(f"{product.model_dump_json()},\n")


class _UsetriAPIProductFactory(UsetriAPIProduct):

    @classmethod
    def from_imported_product(
        cls, product: ImportedProduct, category_id: int, shop_id: int | None = None
    ) -> UsetriAPIProduct:
        unit, amount = cls._convert_unit(product)
        return UsetriAPIProduct(
            product=UsetriAPIProductDetail(
                barcode=product.barcode,
                name=product.name,
                amount=amount,
                brand=product.brand,
                unit=unit,
                category_id=category_id,
                source_image=product.source_image.id,
                is_barcode_checked=product.is_barcode_checked,
            ),
            price=product.price,
            shop_id=shop_id if shop_id is not None else int(product.source_image.meta["shop_id"]),
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


class UsetriAPIProductsImporter(ProductsImporter):
    def __init__(self, client: UsetriClient, shop_id: int | None = None):
        self._shop_id = shop_id
        self._client = client
        self._category_to_id_mapping = self._make_category_to_id_mapping()

    @classmethod
    def from_api_token(cls, token: str, shop_id: int | None = None) -> Self:
        return UsetriAPIProductsImporter(UsetriClient(token), shop_id)

    def _make_category_to_id_mapping(self) -> dict[str, int]:
        categories = self._client.get_categories()
        return {category.name: category.id for category in categories}

    def import_product(self, product: ImportedProduct):
        try:
            category_id = self._category_to_id_mapping[product.category]
            imported_product = _UsetriAPIProductFactory.from_imported_product(
                product, category_id=category_id, shop_id=self._shop_id
            )
            self._client.import_product(imported_product)
        except Exception as e:
            raise e
