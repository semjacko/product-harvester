[![codecov](https://codecov.io/gh/semjacko/product-harvester/graph/badge.svg?token=2891N9XPTH)](https://codecov.io/gh/semjacko/product-harvester)

# Product Harvester
Product Harvester is a tool designed for extracting key product information from price tag images.
It extracts data such as product name, price, quantity, barcode...

# Architecture
Product Harvester is modular and consists of 4 key components, each providing a simple and interchangeable interface:
  - **ImageLinksRetriever** - Responsible for generating image links that serve as inputs for further processing.
  - **ImageProcessor** - Utilizes LLMs to analyze and extract structured product data (e.g., name, price, barcode) 
  from batches of price tag images.
  - **ProductsImporter** - Handles importing of extracted data through an API (or directly into the database).
  - **ErrorTracker** - Tracks (or logs) the errors encountered throughout the harvesting process.

This design allows components to be easily replaced with existing solutions or custom adapters to suit specific needs.

![image](https://github.com/user-attachments/assets/e8f3ed9d-6c16-43b4-8d73-6ef84ffc4804)

# Example usage
```python
from langchain_google_genai import ChatGoogleGenerativeAI

from product_harvester.harvester import ProductsHarvester
from product_harvester.importers import DoLacnaAPIProductsImporter
from product_harvester.processors import PriceTagImageProcessor
from product_harvester.retrievers import LocalImageLinksRetriever

retriever = LocalImageLinksRetriever("./path/to/images")
processor = PriceTagImageProcessor(ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key="<api_key>"))
importer = DoLacnaAPIProductsImporter(token="<api_token>", shop_id=1)
harvester = ProductsHarvester(retriever, processor, importer)

harvester.harvest() # Will extract the data from price tag images and import them via specific API.
```

## Example server
A simple example of a [server](server/server.py) that demonstrates how to use **Product Harvester** to extract
structured data from uploaded image files can be found in the [server folder](server).
It implements its own custom adapters for each component except **ImageProcessor** (for which it utilizes existing
**PriceTagImageProcessor**):
  - **ImageLinksRetriever** - implemented by [Base64Retriever](server/retriever.py)
  - **ProductsImporter** -> implemented by [ProductsCollector](server/products_collector.py)
  - **ErrorTracker** -> implemented by [ErrorCollector](server/error_collector.py)
