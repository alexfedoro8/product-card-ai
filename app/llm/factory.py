"""Фабрика клиентов LLM с реестром «вид API → класс клиента».

Новый вид API подключается вызовом register_client(), без правок остального кода.
"""

from __future__ import annotations

from collections.abc import Callable

from app.core.config import Settings
from app.core.errors import ConfigError
from app.llm.anthropic_client import AnthropicClient
from app.llm.base import ChatMessage, LLMClient
from app.llm.openai_client import OpenAICompatibleClient

ClientFactory = Callable[[Settings], LLMClient]

_REGISTRY: dict[str, ClientFactory] = {
    "openai": OpenAICompatibleClient,
    "anthropic": AnthropicClient,
}


def register_client(kind: str, factory: ClientFactory) -> None:
    _REGISTRY[kind] = factory


def create_client(settings: Settings) -> LLMClient:
    """Клиент для провайдера, выбранного в настройках."""
    if not settings.api_key_configured or settings.provider is None:
        raise ConfigError(
            "Не задан API-ключ модели. Скопируйте .env.example в .env и укажите один из ключей: "
            "OPENROUTER_API_KEY, OPENAI_API_KEY, DEEPSEEK_API_KEY или ANTHROPIC_API_KEY.",
            code="llm_not_configured",
        )
    factory = _REGISTRY.get(settings.provider.kind)
    if factory is None:
        raise ConfigError(f"Для вида API «{settings.provider.kind}» не зарегистрирован клиент.")
    return factory(settings)


class LazyLLMClient:
    """Прокси: создаёт настоящий клиент при первом запросе к модели.

    Так ошибки входных данных (422) проверяются раньше, чем отсутствие ключа (503),
    а сборка зависимостей не обращается к SDK заранее.
    """

    def __init__(self, settings: Settings, factory: Callable[[Settings], LLMClient] = create_client) -> None:
        self._settings = settings
        self._factory = factory
        self._client: LLMClient | None = None
        self.model = settings.model

    def complete(self, messages: list[ChatMessage], temperature: float) -> str:
        if self._client is None:
            self._client = self._factory(self._settings)
        return self._client.complete(messages, temperature)
