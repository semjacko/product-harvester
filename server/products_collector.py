from product_harvester.importer import ProductsImporter, ImportedProduct
from product_harvester.product import Product


class ProductsCollector(ProductsImporter):
    def __init__(self):
        self.products: list[Product] = []

    def import_product(self, product: ImportedProduct):
        self.products.append(
            Product(
                name=product.product.name,
                qty=product.product.amount,
                qty_unit=product.product.unit,
                price=product.price,
                barcode=product.product.barcode,
                brand=product.product.brand,
                category=str(product.product.category_id),  # TODO
            )
        )
