from product_harvester.dolacna_client import _DoLacnaClient, _DoLacnaAPIProduct, _DoLacnaAPICategory
from product_harvester.product import Product


class ProductsImporter:
    def import_product(self, product: Product):
        raise NotImplementedError()


class StdOutProductsImporter(ProductsImporter):
    def import_product(self, product: Product):
        print(product)


class DoLacnaAPIProductsImporter(ProductsImporter):
    def __init__(self, dolacna_client: _DoLacnaClient, categories: list[_DoLacnaAPICategory],  shop_id: int):
        self._shop_id = shop_id
        self._client = dolacna_client
        self._categories = categories
        self._category_to_id_mapping = self._make_category_to_id_mapping()

    def _make_category_to_id_mapping(self) -> dict[str, int]:
        return {category.name: category.id for category in self._categories}

    def import_product(self, product: Product):
        try:
            print(f"Import product starting: {product}")
            category_id = self._category_to_id_mapping[product.category]
            print(f"category of product: {category_id} -> name: {product.category}")
            imported_product = _DoLacnaAPIProduct.from_product(product, category_id=category_id, shop_id=self._shop_id)
            self._client.import_product(imported_product)
        except Exception as e:
            raise e
