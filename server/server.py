from fastapi import FastAPI, HTTPException
from starlette.staticfiles import StaticFiles

from product_harvester.harvester import ProductsHarvester
from product_harvester.processors import PriceTagImageProcessor
from product_harvester.product import Product
from server.request import ProcessRequest
from server.retriever import Base64Retriever
from server.tracker import ErrorCollector

api_app = FastAPI(title="Price tag images processing API")


@api_app.post("/process")
def process(process_request: ProcessRequest) -> Product | None:
    """
    Processes a base64 image to extract a data of a single product.
    Returns a Product instance or raises an HTTP 500 error if any processing error occurs.
    """
    tracker = ErrorCollector()
    harvester = _prepare_harvester(process_request, tracker)
    products = harvester.harvest()
    _raise_error_if_any(tracker)
    if not products:
        return None
    return products[0]  # Return the first product from the list (since only one product is expected)


def _prepare_harvester(process_request: ProcessRequest, tracker: ErrorCollector) -> ProductsHarvester:
    model = process_request.get_chat_model()
    retriever = Base64Retriever([process_request.image_base64])
    processor = PriceTagImageProcessor(model)
    return ProductsHarvester(retriever, processor, tracker)


def _raise_error_if_any(tracker: ErrorCollector):
    if tracker.errors:
        error_msgs = "\n".join(_truncate(error.msg) for error in tracker.errors)
        raise HTTPException(status_code=500, detail=f"Processing errors occurred: {error_msgs}")


def _truncate(s: str, length: int = 200) -> str:
    return s[:length] + "..." if len(s) > length else s


app = FastAPI(title="Price tag images data extractor")
app.mount("/api", api_app)
app.mount("/", StaticFiles(directory="ui", html=True), name="ui")
