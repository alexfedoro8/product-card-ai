"""Контракт клиента модели. Любая реализация взаимозаменяема (OpenRouter, Claude, заглушка в тестах)."""

from __future__ import annotations

from typing import Protocol

ChatMessage = dict[str, str]  # {"role": "system" | "user" | "assistant", "content": "..."}


class LLMClient(Protocol):
    model: str

    def complete(self, messages: list[ChatMessage], temperature: float) -> str:
        """Возвращает текст ответа модели или выбрасывает LLMError с понятным сообщением."""
        ...
