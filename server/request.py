import base64
from typing import Literal

from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, field_validator


class ProcessRequest(BaseModel):
    model: Literal["google", "openai"] = Field()
    api_key: str = Field(strict=True, min_length=1)
    image_base64: str = Field(strict=True, min_length=1)

    @field_validator("image_base64")
    @classmethod
    def ensure_base64_image(cls, v: list[str]):
        # TODO: Check if v is list[str]
        image_base64 = str(v)
        mime_type, data_base64 = image_base64.split(",")
        cls._ensure_image_mime_type(mime_type)
        try:
            base64.b64decode(data_base64, validate=True)
        except Exception:
            raise ValueError("Invalid base64-encoded image")
        return image_base64

    @classmethod
    def _ensure_image_mime_type(cls, mime_type: str):
        match mime_type:
            case "data:image/jpeg;base64" | "data:image/png;base64":
                pass
            case _:
                raise ValueError(f"Unsupported file type: {mime_type}")

    def get_chat_model(self) -> BaseChatModel:
        match self.model:
            case "google":
                return ChatGoogleGenerativeAI(model="gemini-1.5-pro", google_api_key=self.api_key)
            case "openai":
                return ChatOpenAI(model="gpt-4o", api_key=self.api_key)
            case _:
                raise NotImplementedError(f"Invalid model: {self.model}")
