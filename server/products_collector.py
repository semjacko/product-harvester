from product_harvester.importers import ProductsImporter
from product_harvester.product import Product


class ProductsCollector(ProductsImporter):
    def __init__(self):
        self.products: list[Product] = []

    def import_product(self, product: Product):
        self.products.append(product)
