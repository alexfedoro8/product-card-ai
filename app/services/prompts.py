"""Сборка сообщений для модели из шаблонов в папке prompts/."""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path

from app.core.config import PROMPTS_DIR
from app.llm.base import ChatMessage
from app.schemas import ProductInput


class PromptBuilder:
    def __init__(self, prompts_dir: Path = PROMPTS_DIR) -> None:
        self.prompts_dir = prompts_dir

    @cache  # noqa: B019 — экземпляров единицы, шаблоны читаем с диска один раз
    def template(self, name: str) -> str:
        return (self.prompts_dir / f"{name}.md").read_text(encoding="utf-8")

    @staticmethod
    def fill(template: str, **values: str) -> str:
        for key, value in values.items():
            template = template.replace("{{" + key + "}}", value)
        return template

    def initial_messages(
        self,
        product: ProductInput,
        specs: dict[str, str],
        description: str,
        device_type: str,
        missing: list[str],
    ) -> list[ChatMessage]:
        payload = {
            "name": product.name,
            "manufacturer": product.manufacturer,
            "category": product.category,
            "specs": specs,
            "description": description or None,
        }
        user = self.fill(
            self.template("user"),
            device_type=device_type,
            product_json=json.dumps(payload, ensure_ascii=False, indent=2),
            missing_fields="\n".join(f"- {m}" for m in missing) or "- (все основные поля есть)",
        )
        return [
            {"role": "system", "content": self.template("system")},
            {"role": "user", "content": user},
        ]

    def retry_message(self, issues: list[str]) -> ChatMessage:
        content = self.fill(self.template("retry"), issues="\n".join(f"- {i}" for i in issues))
        return {"role": "user", "content": content}
