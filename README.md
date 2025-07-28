[![codecov](https://codecov.io/gh/semjacko/product-harvester/graph/badge.svg?token=2891N9XPTH)](https://codecov.io/gh/semjacko/product-harvester)

# Product Harvester
Product Harvester is a tool designed to extract key product information from price tag images, such as product name, 
price, quantity, barcode...   
It can be used for automated bulk processing of price tag images stored either locally or on Google Drive (depending 
on the selected `ImagesRetriever` implementation). The extracted structured data can be imported via API or printed 
to the standard output (depending on the selected `ProductsImporter` implementation).

![example](https://github.com/user-attachments/assets/a53dd834-f706-48d3-9a88-406f8f5f7d1e)


# Architecture
Product Harvester is modular and consists of 4 key components, each providing a simple and interchangeable interface:
  - `ImagesRetriever` - Responsible for generating images (links or base64 encoded) that serve as inputs 
  for further processing.
  - `ImageProcessor` - Utilizes LLMs to analyze and extract structured product data (e.g., name, price, barcode) 
  from batches of price tag images.
  - `ProductsImporter` - Handles importing of extracted data through an API (or directly into the database).
  - `ErrorTracker` - Tracks (or logs) the errors encountered throughout the harvesting process.

This design allows components to be easily replaced with existing solutions or custom strategies (or adapters) 
to suit specific needs.

![architecture](https://github.com/user-attachments/assets/65d142c8-855b-4f25-939d-80e62d2ae897)


# Usage
## Step 1: Install Dependencies
Ensure you have **Python 3.10** (or higher).
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt 
```

## Step 2: Run example script
```python
from langchain_google_genai import ChatGoogleGenerativeAI

from product_harvester.harvester import ProductsHarvester, StdOutErrorTracker
from product_harvester.importers import StdOutProductsImporter
from product_harvester.model_factory import SingleModelFactory
from product_harvester.processors import PriceTagImageProcessor
from product_harvester.retrievers import LocalImagesRetriever

retriever = LocalImagesRetriever("./path/to/images/folder")
model_factory = SingleModelFactory(ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key="<api_key>"))
processor = PriceTagImageProcessor(model_factory)
printer = StdOutProductsImporter()
logger = StdOutErrorTracker()
harvester = ProductsHarvester(retriever, processor, importer=printer, error_tracker=logger)

harvester.harvest()
```

## Example server
A simple example of a [server](server/server.py) that demonstrates how to use **Product Harvester** to extract
structured data from uploaded image files can be found in the [server folder](server).
It implements its own custom strategies for each component except `ImageProcessor` (for which it utilizes existing
[PriceTagImageProcessor](product_harvester/processors.py)):
  - `ImagesRetriever` -> implemented by [Base64Retriever](server/retriever.py)
  - `ProductsImporter` -> implemented by [ProductsCollector](server/products_collector.py)
  - `ErrorTracker` -> implemented by [ErrorCollector](server/error_collector.py)
