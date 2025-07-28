from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from starlette.responses import JSONResponse
from starlette.staticfiles import StaticFiles

from product_harvester.harvester import ProductsHarvester
from product_harvester.importers import ImportedProduct
from product_harvester.model_factory import SingleModelFactory
from product_harvester.processors import PriceTagImageProcessor
from server.error_collector import ErrorCollector
from server.products_collector import ProductsCollector
from server.request import ProcessRequest
from server.retriever import Base64Retriever

api_app = FastAPI(title="Product price images processing API")


@api_app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError):
    errors = [{"error": f"{err['loc'][1]}: validation error", "detailed_info": err["msg"]} for err in exc.errors()]
    return JSONResponse(
        status_code=422,
        content={"message": "Validation Error", "detail": errors},
    )


@api_app.post("/process/pricetag")
async def process_pricetag(process_request: ProcessRequest) -> ImportedProduct | None:
    """
    Processes a base64 image to extract a data of a single product.
    Returns a ImportedProduct instance or raises an HTTP 500 error if any processing error occurs.
    """
    error_collector = ErrorCollector()
    products_collector = ProductsCollector()
    harvester = _prepare_harvester(process_request, products_collector, error_collector)
    harvester.harvest()
    _raise_error_if_any(error_collector)
    if not products_collector.products:
        return None
    return products_collector.products[0]  # Return the first product from the list (since only one product is expected)


def _prepare_harvester(
    process_request: ProcessRequest, products_collector: ProductsCollector, error_collector: ErrorCollector
) -> ProductsHarvester:
    model = process_request.get_chat_model()
    retriever = Base64Retriever([process_request.image_base64])
    factory = SingleModelFactory(model)
    processor = PriceTagImageProcessor(factory)
    return ProductsHarvester(retriever, processor, products_collector, error_collector)


def _raise_error_if_any(error_collector: ErrorCollector):
    if error_collector.errors:
        detail = [
            {"error": error.msg, "detailed_info": _truncate(error.extra.get("detailed_info", ""))}
            for error in error_collector.errors
        ]
        raise HTTPException(status_code=500, detail=detail)


def _truncate(s: str, length: int = 200) -> str:
    return s[:length] + "..." if len(s) > length else s


app = FastAPI(title="Product price images data extractor")
app.mount("/api", api_app)
app.mount("/", StaticFiles(directory="ui", html=True), name="ui")
