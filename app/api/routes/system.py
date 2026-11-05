"""Служебные маршруты: состояние сервиса."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.core.config import configured_providers, get_settings
from app.core.errors import ConfigError

router = APIRouter(tags=["Служебное"])


def service_status() -> dict[str, Any]:
    """Какой провайдер и модель используются. Сам ключ никогда не выводится."""
    try:
        settings = get_settings()
    except ConfigError as exc:
        return {"provider": None, "model": None, "api_key_configured": False, "error": exc.message}
    return {
        "provider": settings.provider.title if settings.provider else None,
        "model": settings.model if settings.provider else None,
        "api_key_configured": settings.api_key_configured,
        "keys_found": configured_providers(),
    }


@router.get("/health", summary="Состояние сервиса")
def health() -> dict[str, Any]:
    return {"status": "ok", **service_status()}
