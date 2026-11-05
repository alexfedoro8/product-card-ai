"""Загрузка фото товара файлом."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.api.dependencies import get_image_storage
from app.schemas import ErrorResponse
from app.services import ImageStorage

router = APIRouter(prefix="/api/v1", tags=["Карточки"])


@router.post(
    "/images",
    summary="Загрузить фото товара файлом",
    description=(
        "Тело запроса — сам файл изображения (JPEG, PNG, WebP или GIF, до 10 МБ). "
        "Возвращает ссылку, которую можно передать в поле `images` карточки."
    ),
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {"application/octet-stream": {"schema": {"type": "string", "format": "binary"}}},
        }
    },
    responses={
        413: {"model": ErrorResponse, "description": "Файл больше 10 МБ"},
        415: {"model": ErrorResponse, "description": "Не изображение"},
    },
)
async def upload_image(
    request: Request, storage: Annotated[ImageStorage, Depends(get_image_storage)]
) -> dict[str, str]:
    name = storage.save(await request.body())
    return {"url": str(request.url_for("uploads", path=name))}
