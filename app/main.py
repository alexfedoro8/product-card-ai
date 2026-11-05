"""Точка входа: фабрика FastAPI-приложения.

uv run uvicorn app.main:app --reload
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.errors import register_exception_handlers
from app.api.routes import cards, images, pages, system
from app.core.config import STATIC_DIR, UPLOAD_DIR

DESCRIPTION = (
    "Создаёт черновик карточки товара для B2B-магазина контрольно-измерительных приборов: "
    "SEO-заголовок и описание, характеристики, поисковые запросы, коммерческий блок. "
    "Технические значения берутся только из входных данных; отсутствующие помечаются «данных нет».\n\n"
    "Панель для ручного ввода: [/](/)"
)


def create_app() -> FastAPI:
    app = FastAPI(title="AI-помощник карточек товаров КИП", version="0.2.0", description=DESCRIPTION)

    UPLOAD_DIR.mkdir(exist_ok=True)
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

    for module in (pages, cards, images, system):
        app.include_router(module.router)
    register_exception_handlers(app)
    return app


app = create_app()
