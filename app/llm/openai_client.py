"""OpenRouter, OpenAI, DeepSeek — один клиент на OpenAI-совместимом API (меняется только base_url)."""

from __future__ import annotations

from typing import Any

from app.core.config import Settings
from app.llm.base import ChatMessage
from app.llm.errors import empty_response_error, translate_error


class OpenAICompatibleClient:
    def __init__(self, settings: Settings) -> None:
        import openai  # импорт здесь, чтобы ядро и тесты работали без SDK

        assert settings.provider is not None
        self._sdk = openai
        self.provider = settings.provider.title
        self.model = settings.model
        # Повторы при таймаутах, 429 и 5xx с экспоненциальной паузой делает сам SDK.
        self._client = openai.OpenAI(
            api_key=settings.api_key,
            base_url=settings.base_url,
            timeout=settings.timeout,
            max_retries=2,
            default_headers={"X-Title": "product-card-ai"},  # подпись приложения в OpenRouter
        )

    def complete(self, messages: list[ChatMessage], temperature: float) -> str:
        try:
            try:
                response = self._create(messages, temperature, json_mode=True)
            except self._sdk.BadRequestError:
                # Не все модели поддерживают response_format — повторяем без него.
                response = self._create(messages, temperature, json_mode=False)
        except Exception as exc:  # noqa: BLE001
            raise translate_error(self._sdk, exc, self.model, self.provider) from exc

        choices = getattr(response, "choices", None) or []
        content = choices[0].message.content if choices else None
        if not content:
            raise empty_response_error()
        return str(content)

    def _create(self, messages: list[ChatMessage], temperature: float, json_mode: bool) -> Any:
        kwargs: dict[str, Any] = {"model": self.model, "messages": messages, "temperature": temperature}
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        return self._client.chat.completions.create(**kwargs)
