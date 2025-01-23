from langchain_google_genai import ChatGoogleGenerativeAI

from product_harvester.dolacna_client import _DoLacnaClient
from product_harvester.harvester import ErrorLogger, ProductsHarvester
from product_harvester.importers import DoLacnaAPIProductsImporter
from product_harvester.processors import PriceTagImageProcessor
from product_harvester.retrievers import LocalImagesRetriever

if __name__ == "__main__":
    # TODO enum / static const
    lidl_id = 1
    billa_id = 2
    kaufland_id = 3
    tesco_id = 4

    shop_id = kaufland_id
    shop_folder = "kaufland"
    dolacna_user_token = "addUserToken"
    dolacna_client = _DoLacnaClient(dolacna_user_token)
    print("Starting project")

    categories = dolacna_client.get_categories()
    print(f"Categories retrieved. Count: {len(categories)}")

    retriever = LocalImagesRetriever(f"./test_images/{shop_folder}")
    # retriever = GoogleDriveImagesRetriever(client_config, folder_id)

    processor = PriceTagImageProcessor(ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key="addGoogleApiKey"), categories)

    importer = DoLacnaAPIProductsImporter(dolacna_client, categories, billa_id)
    # importer = ProductsCollector()

    logger = ErrorLogger()

    harvester = ProductsHarvester(retriever, processor, importer, logger)
    harvester.harvest()

    # print(importer.products)