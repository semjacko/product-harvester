from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from starlette.responses import JSONResponse
from starlette.staticfiles import StaticFiles

from product_harvester.harvester import ProductsHarvester
from product_harvester.processors import PriceTagImageProcessor
from product_harvester.product import Product
from server.request import ProcessRequest
from server.retriever import Base64Retriever
from server.tracker import ErrorCollector

api_app = FastAPI(title="Price tag images processing API")


@api_app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError):
    errors = [{"error": f"{err['loc'][1]}: validation error", "detailed_info": err["msg"]} for err in exc.errors()]
    return JSONResponse(
        status_code=422,
        content={"message": "Validation Error", "detail": errors},
    )


@api_app.post("/process")
async def process(process_request: ProcessRequest) -> Product | None:
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
        detail = [
            {"error": error.msg, "detailed_info": _truncate(error.extra.get("detailed_info", ""))}
            for error in tracker.errors
        ]
        raise HTTPException(status_code=500, detail=detail)


def _truncate(s: str, length: int = 200) -> str:
    return s[:length] + "..." if len(s) > length else s


app = FastAPI(title="Price tag images data extractor")
app.mount("/api", api_app)
app.mount("/", StaticFiles(directory="ui", html=True), name="ui")
