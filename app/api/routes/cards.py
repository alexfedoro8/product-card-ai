"""Создание карточки."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_card_generator
from app.schemas import CardResponse, ErrorResponse, ProductInput
from app.services import CardGenerator

router = APIRouter(prefix="/api/v1", tags=["Карточки"])


@router.post(
    "/cards",
    response_model=CardResponse,
    summary="Создать черновик карточки товара",
    responses={
        422: {"model": ErrorResponse, "description": "Некорректный JSON или недостаточно данных"},
        502: {"model": ErrorResponse, "description": "Ошибка модели или провайдера"},
        503: {"model": ErrorResponse, "description": "Не задан API-ключ модели"},
        504: {"model": ErrorResponse, "description": "Модель не ответила вовремя"},
    },
)
def create_card(
    product: ProductInput,
    generator: Annotated[CardGenerator, Depends(get_card_generator)],
) -> CardResponse:
    # Обычная (не async) функция: FastAPI выполнит её в пуле потоков, синхронный SDK не блокирует сервер.
    return generator.generate(product)
