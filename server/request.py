import base64
from typing import Any, Literal

from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, field_validator


class ProcessRequest(BaseModel):
    model: Literal["google", "openai"] = Field()
    api_key: str = Field(..., min_length=1, description="API key for the selected model")
    image_base64: str = Field(..., min_length=1, description="Base64-encoded image")

    @field_validator("image_base64")
    @classmethod
    def ensure_base64_image(cls, v: Any) -> str:
        """
        Validates that `image_base64` is a correctly formatted base64-encoded image.
        Ensures it has an accepted MIME type and decodes without error.
        """
        if not isinstance(v, str):
            raise ValueError("Image must be a base64-encoded string")
        mime_type, data_base64 = v.split(",", 1)
        cls._ensure_image_mime_type(mime_type)
        try:
            base64.b64decode(data_base64, validate=True)
        except Exception as e:
            raise ValueError(f"Image validation failed: {str(e)}")
        return v

    @classmethod
    def _ensure_image_mime_type(cls, mime_type: str):
        """
        Ensures that the MIME type in the base64 string is one of the allowed types.
        """
        if mime_type not in {"data:image/jpeg;base64", "data:image/png;base64"}:
            raise ValueError(f"Unsupported file type: {mime_type}. Only JPEG and PNG are supported.")

    def get_chat_model(self) -> BaseChatModel:
        """
        Returns an instance of the chat model based on the specified `model` value.
        """
        match self.model:
            case "google":
                return ChatGoogleGenerativeAI(model="gemini-1.5-pro", google_api_key=self.api_key)
            case "openai":
                return ChatOpenAI(model="gpt-4o", api_key=self.api_key)
            case _:
                raise ValueError(f"Unsupported model: {self.model}")
