import unittest
import warnings

import pytest

from tradingagents.llm_clients.base_client import BaseLLMClient
from tradingagents.llm_clients.factory import create_llm_client
from tradingagents.llm_clients.model_catalog import get_known_models
from tradingagents.llm_clients.validators import validate_model


class DummyLLMClient(BaseLLMClient):
    def __init__(self, provider: str, model: str):
        self.provider = provider
        super().__init__(model)

    def get_llm(self):
        self.warn_if_unknown_model()
        return object()

    def validate_model(self) -> bool:
        return validate_model(self.provider, self.model)


@pytest.mark.unit
class ModelValidationTests(unittest.TestCase):
    def test_cli_catalog_models_are_all_validator_approved(self):
        for provider, models in get_known_models().items():
            for model in models:
                with self.subTest(provider=provider, model=model):
                    self.assertTrue(validate_model(provider, model))

    def test_unknown_model_emits_warning_for_strict_provider(self):
        client = DummyLLMClient("deepseek", "not-a-real-deepseek-model")

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            client.get_llm()

        self.assertEqual(len(caught), 1)
        self.assertIn("not-a-real-deepseek-model", str(caught[0].message))
        self.assertIn("deepseek", str(caught[0].message))

    def test_unknown_provider_accepts_custom_models_without_warning(self):
        client = DummyLLMClient("private-deepseek-gateway", "custom-model-name")

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            client.get_llm()

        self.assertEqual(caught, [])

    def test_factory_supports_deepseek_only(self):
        client = create_llm_client("deepseek", "deepseek-v4-flash")
        self.assertEqual(client.provider, "deepseek")

        with self.assertRaisesRegex(ValueError, "DeepSeek only"):
            create_llm_client("openai", "gpt-5.4")
