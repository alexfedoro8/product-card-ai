"""Таблица характеристик и список того, что требует уточнения. Собирается кодом, не моделью."""

from __future__ import annotations

from app.core.normalize import capitalize
from app.schemas import ExtractedSpec, MissingField, ProductInput, SpecRow
from app.services.checklist import DeviceProfile, find_missing

PHOTO_FIELD = "Фото товара"
DESCRIPTION_FIELD = "Текстовое описание / паспорт"
MANUFACTURER_FIELD = "Производитель"


def build_spec_rows(
    product: ProductInput, specs: dict[str, str], accepted: list[ExtractedSpec]
) -> list[SpecRow]:
    """Характеристики из входа один в один + значения из описания, подтверждённые цитатой."""
    rows: list[SpecRow] = []
    if product.manufacturer and not any("производител" in k.lower() for k in specs):
        rows.append(SpecRow(name=MANUFACTURER_FIELD, value=product.manufacturer, source="входные данные"))
    rows += [SpecRow(name=k, value=v, source="входные данные") for k, v in specs.items()]

    known = {r.name.lower() for r in rows}
    for spec in accepted:
        name = capitalize(spec.name)
        if name.lower() not in known:
            known.add(name.lower())
            rows.append(SpecRow(name=name, value=spec.value, source="описание", quote=spec.source_quote))
    return rows


def build_missing(
    product: ProductInput,
    profile: DeviceProfile,
    rows: list[SpecRow],
    empty_fields: list[str],
    description: str,
) -> list[MissingField]:
    missing: list[MissingField] = []
    if not product.manufacturer and not any("производител" in r.name.lower() for r in rows):
        missing.append(MissingField(name=MANUFACTURER_FIELD, reason="нет во входных данных"))

    known_names = [r.name for r in rows] + empty_fields
    missing += [
        MissingField(name=name, reason="нет во входных данных") for name in find_missing(profile, known_names)
    ]
    missing += [MissingField(name=name, reason="поле передано пустым") for name in empty_fields]

    if not description:
        missing.append(MissingField(name=DESCRIPTION_FIELD, reason="не передано"))
    if not product.images:
        missing.append(
            MissingField(name=PHOTO_FIELD, reason="ссылки не переданы — запросить у производителя")
        )
    return missing
