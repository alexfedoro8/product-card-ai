"""Иерархия ошибок приложения.

Каждая ошибка знает свой код и HTTP-статус, поэтому API обрабатывает их одним
обработчиком, а CLI — одним except. Новая ошибка = новый подкласс, без правок обработчиков.
"""

from __future__ import annotations


class AppError(Exception):
    """Базовая ошибка с понятным пользователю сообщением."""

    code = "app_error"
    http_status = 500

    def __init__(self, message: str, *, code: str | None = None, http_status: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        if http_status:
            self.http_status = http_status


class ConfigError(AppError):
    """Неверная настройка: нет ключа, неизвестный провайдер."""

    code = "config_error"
    http_status = 503


class LLMError(AppError):
    """Ошибка обращения к модели или неподходящий ответ модели."""

    code = "llm_error"
    http_status = 502


class ImageError(AppError):
    """Загруженный файл не подходит как фото товара."""

    code = "image_error"
    http_status = 415
