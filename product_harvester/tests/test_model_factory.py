from unittest import TestCase
from unittest.mock import MagicMock

from langchain_core.rate_limiters import InMemoryRateLimiter

from product_harvester.model_factory import ModelFactory, ModelWithLimits, RateLimitedModelFactory, SingleModelFactory


class TestModelFactory(TestCase):
    def test_abstract_base_class(self):
        with self.assertRaises(TypeError):
            ModelFactory().get_model()


class TestSingleModelFactory(TestCase):
    def test_get_model(self):
        model = MagicMock()
        factory = SingleModelFactory(model)
        self.assertEqual(factory.get_model(), model)


class TestRateLimitedModelFactory(TestCase):
    def setUp(self):
        self.model1 = ModelWithLimits(model=MagicMock(), rpm=60, rpd=5)
        self.model2 = ModelWithLimits(model=MagicMock(), rpm=120, rpd=3)
        self.model3 = ModelWithLimits(model=MagicMock(), rpm=30, rpd=2)

    def test_initialization_sets_rate_limiters(self):
        RateLimitedModelFactory([self.model1, self.model2])
        self.assertIsInstance(self.model1.model.rate_limiter, InMemoryRateLimiter)
        self.assertIsInstance(self.model2.model.rate_limiter, InMemoryRateLimiter)
        self.assertEqual(self.model1.model.rate_limiter.requests_per_second, 1)
        self.assertEqual(self.model2.model.rate_limiter.requests_per_second, 2)

    def test_get_model(self):
        factory = RateLimitedModelFactory([self.model1, self.model2, self.model3])

        for i in range(10):
            if i >= 5:
                self.assertIsNone(factory.get_model())
            if i < 5:
                self.assertEqual(self.model1.model, factory.get_model())
            if i < 3:
                self.assertEqual(self.model2.model, factory.get_model())
            if i < 2:
                self.assertEqual(self.model3.model, factory.get_model())
