from abc import ABC, abstractmethod
from typing import Generator

from langchain_core.language_models import BaseChatModel
from langchain_core.rate_limiters import InMemoryRateLimiter


class ModelFactory(ABC):

    @abstractmethod
    def get_model(self) -> BaseChatModel: ...


class SingleModelFactory(ModelFactory):
    def __init__(self, model: BaseChatModel) -> None:
        self._model = model

    def get_model(self) -> BaseChatModel:
        return self._model


class ModelWithLimits:
    def __init__(self, model: BaseChatModel, rpm: int, rpd: int):
        self.model = model
        self.rpm = rpm
        self.rpd = rpd


class RateLimitedModelFactory(ModelFactory):
    def __init__(self, models: list[ModelWithLimits], rpd_subtractor: int = 1):
        self._models = models
        self._rpd_subtractor = rpd_subtractor
        for model_with_limits in self._models:
            model_with_limits.model.rate_limiter = InMemoryRateLimiter(requests_per_second=model_with_limits.rpm / 60)
        self._model_cycle = self._available_model_generator()

    def get_model(self) -> BaseChatModel | None:
        return next(self._model_cycle, None)

    def _available_model_generator(self) -> Generator[BaseChatModel | None, None, None]:
        while True:
            found = False
            for model_with_limits in self._models:
                if model_with_limits.rpd > 0:
                    model_with_limits.rpd -= self._rpd_subtractor
                    found = True
                    yield model_with_limits.model
            if not found:
                yield None
