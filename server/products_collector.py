from product_harvester.importers import ProductsImporter, ImportedProduct


class ProductsCollector(ProductsImporter):
    def __init__(self):
        self.products: list[ImportedProduct] = []

    def import_product(self, product: ImportedProduct):
        self.products.append(product)
