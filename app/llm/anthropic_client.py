"""Anthropic Claude через нативный Messages API."""

from __future__ import annotations

from typing import Any

from app.core.config import Settings
from app.llm.base import ChatMessage
from app.llm.errors import empty_response_error, translate_error


class AnthropicClient:
    def __init__(self, settings: Settings) -> None:
        import anthropic

        assert settings.provider is not None
        self._sdk = anthropic
        self.provider = settings.provider.title
        self.model = settings.model
        kwargs: dict[str, Any] = {"api_key": settings.api_key, "timeout": settings.timeout, "max_retries": 2}
        if settings.base_url:
            kwargs["base_url"] = settings.base_url
        self._client = anthropic.Anthropic(**kwargs)

    def complete(self, messages: list[ChatMessage], temperature: float) -> str:
        # В Messages API системный промпт передаётся отдельно от диалога.
        system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
        dialog = [m for m in messages if m["role"] != "system"]
        try:
            response = self._client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system,
                messages=dialog,  # type: ignore[arg-type]
                temperature=temperature,
            )
        except Exception as exc:  # noqa: BLE001
            raise translate_error(self._sdk, exc, self.model, self.provider) from exc

        text = "".join(getattr(block, "text", "") for block in response.content)
        if not text:
            raise empty_response_error()
        return text
