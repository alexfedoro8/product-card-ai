"""Ответ модели. Проверяется кодом до того, как попадёт в карточку."""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ExtractedSpec(BaseModel):
    """Характеристика, которую модель нашла в тексте описания, с дословной цитатой."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    name: str
    value: str
    source_quote: str = ""


class LLMDraft(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    seo_title: str
    seo_description: str
    search_queries: list[str]
    commercial_block: str
    extracted_specs: list[ExtractedSpec] = Field(default_factory=list)

    @field_validator("seo_description")
    @classmethod
    def normalize_list_markers(cls, text: str) -> str:
        """Маркеры списка «•», «*», «–», «—» приводим к единому «- »."""
        lines = [re.sub(r"^\s*[•*–—]\s+", "- ", line.rstrip()) for line in text.splitlines()]
        return "\n".join(lines).strip()

    @field_validator("search_queries")
    @classmethod
    def dedupe_queries(cls, queries: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for query in queries:
            q = " ".join(str(query).split())
            if q and q.lower() not in seen:
                seen.add(q.lower())
                result.append(q)
        return result
