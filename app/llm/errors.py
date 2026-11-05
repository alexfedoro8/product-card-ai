"""Перевод исключений SDK в LLMError с понятным пользователю сообщением.

Исключения SDK OpenAI и Anthropic называются одинаково, поэтому перевод общий.
"""

from __future__ import annotations

from types import ModuleType

from app.core.errors import LLMError


def translate_error(sdk: ModuleType, exc: Exception, model: str, provider: str) -> LLMError:
    if isinstance(exc, LLMError):
        return exc
    if isinstance(exc, sdk.AuthenticationError):
        return LLMError(f"Неверный API-ключ {provider} (401). Проверьте ключ в .env.", code="llm_auth")
    if isinstance(exc, sdk.PermissionDeniedError):
        return LLMError(
            f"Доступ к API {provider} запрещён (403). Проверьте ключ и регион.", code="llm_forbidden"
        )
    if isinstance(exc, sdk.NotFoundError):
        return LLMError(
            f"Модель «{model}» не найдена у {provider}. Проверьте LLM_MODEL.", code="llm_model_not_found"
        )
    if isinstance(exc, sdk.RateLimitError):
        return LLMError(
            f"Превышен лимит запросов к {provider} (429). Повторите позже.", code="llm_rate_limit"
        )
    if isinstance(exc, sdk.APITimeoutError):
        return LLMError("Модель не ответила вовремя. Повторите запрос.", code="llm_timeout", http_status=504)
    if isinstance(exc, sdk.APIConnectionError):
        return LLMError(
            f"Нет соединения с API {provider}. Проверьте интернет и LLM_BASE_URL.", code="llm_connection"
        )
    if isinstance(exc, sdk.APIStatusError):
        if exc.status_code == 402:
            return LLMError(f"Недостаточно средств на балансе {provider} (402).", code="llm_payment")
        return LLMError(f"Ошибка API {provider} ({exc.status_code}). Повторите позже.", code="llm_api_error")
    return LLMError(f"Непредвиденная ошибка при обращении к модели: {exc}", code="llm_unknown")


def empty_response_error() -> LLMError:
    return LLMError("Модель вернула пустой ответ. Повторите запрос.", code="llm_empty_response")
