"""Настройки из переменных окружения или файла .env (он в .gitignore).

Провайдер LLM выбирается автоматически по тому, какой ключ задан,
либо явно через LLM_PROVIDER. Модель и адрес API можно переопределить.
Новый провайдер добавляется одной записью в PROVIDERS.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.core.errors import ConfigError

PROJECT_ROOT = Path(__file__).resolve().parents[2]
APP_DIR = PROJECT_ROOT / "app"
PROMPTS_DIR = PROJECT_ROOT / "prompts"
EXAMPLES_DIR = PROJECT_ROOT / "examples"
UPLOAD_DIR = PROJECT_ROOT / "uploads"
TEMPLATES_DIR = APP_DIR / "templates"
STATIC_DIR = APP_DIR / "static"


@dataclass(frozen=True)
class Provider:
    id: str
    title: str
    key_env: str
    base_url: str | None  # None — адрес SDK по умолчанию
    default_model: str
    kind: str  # вид API: "openai" — OpenAI-совместимый, "anthropic" — нативный API Claude


# Порядок важен: при нескольких ключах выбирается первый из списка.
PROVIDERS: dict[str, Provider] = {
    p.id: p
    for p in (
        Provider(
            "openrouter",
            "OpenRouter",
            "OPENROUTER_API_KEY",
            "https://openrouter.ai/api/v1",
            "openai/gpt-4o-mini",
            "openai",
        ),
        Provider("openai", "OpenAI", "OPENAI_API_KEY", None, "gpt-4o-mini", "openai"),
        Provider(
            "deepseek", "DeepSeek", "DEEPSEEK_API_KEY", "https://api.deepseek.com", "deepseek-chat", "openai"
        ),
        Provider("anthropic", "Anthropic Claude", "ANTHROPIC_API_KEY", None, "claude-haiku-5-5", "anthropic"),
    )
}


@dataclass(frozen=True)
class Settings:
    provider: Provider | None
    api_key: str
    base_url: str | None
    model: str
    temperature: float = 0.3
    timeout: float = 60
    max_attempts: int = 3
    max_image_bytes: int = 10 * 1024 * 1024

    @property
    def api_key_configured(self) -> bool:
        return self.provider is not None and bool(self.api_key)


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:  # python-dotenv не обязателен, если переменные заданы в окружении
        return
    load_dotenv(PROJECT_ROOT / ".env")


def _env(name: str) -> str:
    return os.getenv(name, "").strip()


def resolve_provider() -> Provider | None:
    explicit = _env("LLM_PROVIDER").lower()
    if explicit:
        if explicit not in PROVIDERS:
            raise ConfigError(f"Неизвестный LLM_PROVIDER «{explicit}». Допустимо: {', '.join(PROVIDERS)}.")
        return PROVIDERS[explicit]
    return next((p for p in PROVIDERS.values() if _env(p.key_env)), None)


def configured_providers() -> list[str]:
    return [p.id for p in PROVIDERS.values() if _env(p.key_env)]


@lru_cache
def get_settings() -> Settings:
    _load_dotenv()
    provider = resolve_provider()
    return Settings(
        provider=provider,
        api_key=_env(provider.key_env) if provider else "",
        base_url=_env("LLM_BASE_URL") or (provider.base_url if provider else None),
        model=_env("LLM_MODEL") or (provider.default_model if provider else "—"),
        temperature=float(_env("LLM_TEMPERATURE") or 0.3),
        timeout=float(_env("LLM_TIMEOUT") or 60),
        max_attempts=int(_env("LLM_MAX_ATTEMPTS") or 3),
    )
