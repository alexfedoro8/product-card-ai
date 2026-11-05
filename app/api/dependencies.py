"""Сборка зависимостей для маршрутов (FastAPI Depends).

Маршруты получают готовые объекты и не знают, как они создаются. В тестах любую
зависимость можно подменить через app.dependency_overrides.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from app.core.config import UPLOAD_DIR, Settings, get_settings
from app.llm import LazyLLMClient, LLMClient
from app.services import CardGenerator, ImageStorage, LocalImageStorage

SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_llm_client(settings: SettingsDep) -> LLMClient:
    # Прокси: настоящий клиент создаётся при первом запросе к модели,
    # поэтому ошибки входных данных (422) проверяются раньше, чем наличие ключа (503).
    return LazyLLMClient(settings)


def get_card_generator(
    settings: SettingsDep, client: Annotated[LLMClient, Depends(get_llm_client)]
) -> CardGenerator:
    return CardGenerator(client, max_attempts=settings.max_attempts, temperature=settings.temperature)


@lru_cache
def get_image_storage() -> ImageStorage:
    return LocalImageStorage(UPLOAD_DIR, max_bytes=get_settings().max_image_bytes)
