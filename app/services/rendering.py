"""Markdown-версия карточки для вставки в CMS или документ."""

from __future__ import annotations

from typing import Protocol

from app.schemas import CardResponse
from app.services.specs import DESCRIPTION_FIELD, PHOTO_FIELD

NO_DATA = "данных нет"


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


class CardRenderer(Protocol):
    """Формат выдачи карточки. Новый формат (HTML, XML для CMS) — новый класс с методом render()."""

    def render(self, card: CardResponse) -> str: ...


class MarkdownRenderer:
    def render(self, card: CardResponse) -> str:
        return render_markdown(card)


def render_markdown(card: CardResponse) -> str:
    lines: list[str] = [f"# {card.seo_title}", ""]

    if card.images:
        lines += [f"![{_cell(card.name)}]({url})" for url in card.images]
    else:
        lines.append(f"*Фото товара: {NO_DATA} — запросить у производителя.*")
    lines.append("")

    lines += ["## Описание", "", card.seo_description, ""]

    lines += ["## Характеристики", "", "| Характеристика | Значение |", "|---|---|"]
    for row in card.key_specs:
        mark = " ¹" if row.source == "описание" else ""
        lines.append(f"| {_cell(row.name)} | {_cell(row.value)}{mark} |")
    gap_names = [m.name for m in card.missing_fields if m.name != PHOTO_FIELD]
    for name in gap_names:
        if name != DESCRIPTION_FIELD:
            lines.append(f"| {_cell(name)} | *{NO_DATA}* |")
    if any(r.source == "описание" for r in card.key_specs):
        lines += ["", "¹ значение взято из текстового описания товара"]
    lines.append("")

    if card.missing_fields:
        lines += ["## Требует уточнения", ""]
        lines += [f"- **{m.name}** — {m.reason}" for m in card.missing_fields]
        lines.append("")

    lines += ["## Для менеджера: кому подходит и какие задачи решает", "", card.commercial_block, ""]

    lines += ["## Поисковые запросы", ""]
    lines += [f"- {q}" for q in card.search_queries]
    lines.append("")

    quality = card.data_quality
    lines += ["## Оценка введённых данных", "", f"**{quality.label}.**", ""]
    for req in quality.requirements:
        mark = "✓" if req.ok else "✗"
        hint = f" — {req.hint}" if req.hint else ""
        lines.append(f"- {mark} {req.name}: {req.value}{hint}")
    if quality.how_to_improve:
        lines += ["", "**Как улучшить карточку:**", ""]
        lines += [f"- {tip}" for tip in quality.how_to_improve]
    if card.warnings:
        lines += ["", "**Замечания проверки текста — проверьте вручную:**", ""]
        lines += [f"- {w}" for w in card.warnings]
    lines.append("")

    lines.append(
        f"<sub>SEO-заголовок: {card.seo_title_length}/70 · описание: "
        f"{card.seo_description_length} симв. (норма 800–1200) · "
        f"тип: {card.meta.device_type} · модель: {card.meta.model} · попыток: {card.meta.attempts}</sub>"
    )
    return "\n".join(lines) + "\n"
