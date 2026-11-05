"""Чек-лист обязательных характеристик по типу прибора.

Нужен, чтобы сервис сам сообщал, каких данных не хватает для полноценной
B2B-карточки, а не надеялся, что это заметит модель.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class RequiredField:
    name: str
    synonyms: tuple[str, ...]

    def matches(self, spec_name: str) -> bool:
        normalized = _norm(spec_name)
        return any(syn in normalized for syn in self.synonyms)


@dataclass(frozen=True)
class DeviceProfile:
    id: str
    title: str
    keywords: tuple[str, ...]
    fields: tuple[RequiredField, ...]


def _norm(text: str) -> str:
    return " ".join(text.lower().replace("ё", "е").split())


RANGE = RequiredField("Диапазон измерений", ("диапазон", "предел", "шкала"))
ACCURACY = RequiredField("Класс точности / погрешность", ("класс точн", "точност", "погрешн"))
CONNECTION = RequiredField("Присоединение", ("присоедин", "резьб"))
PROTECTION = RequiredField("Степень защиты (IP)", ("ip", "степень защит", "пылевлаг"))
MEDIUM_TEMP = RequiredField(
    "Температура измеряемой среды",
    ("температура измеряем", "температура сред", "температура рабоч"),
)
OUTPUT = RequiredField("Выходной сигнал", ("выходн", "сигнал", "интерфейс"))
POWER = RequiredField("Напряжение питания", ("питан",))
REGISTRY = RequiredField("Номер в Госреестре СИ", ("госреестр", "реестр", "регистрационный номер"))
VERIFICATION = RequiredField("Межповерочный интервал", ("межповероч", "мпи", "интервал поверк"))

PROFILES: tuple[DeviceProfile, ...] = (
    DeviceProfile(
        id="pressure_transmitter",
        title="Датчик (преобразователь) давления",
        keywords=("датчик давления", "преобразователь давления", "датчик избыточного"),
        fields=(
            RANGE,
            ACCURACY,
            OUTPUT,
            POWER,
            CONNECTION,
            RequiredField("Электрическое подключение", ("электрич", "разъем", "кабел", "подключен")),
            PROTECTION,
            MEDIUM_TEMP,
            REGISTRY,
            VERIFICATION,
        ),
    ),
    DeviceProfile(
        id="pressure_gauge",
        title="Манометр",
        keywords=("манометр", "мановакуумметр", "вакуумметр", "напоромер", "тягомер"),
        fields=(
            RANGE,
            ACCURACY,
            RequiredField("Диаметр корпуса", ("диаметр",)),
            CONNECTION,
            RequiredField("Расположение штуцера", ("расположен", "штуцер")),
            RequiredField("Материал корпуса", ("материал",)),
            PROTECTION,
            MEDIUM_TEMP,
            REGISTRY,
            VERIFICATION,
        ),
    ),
    DeviceProfile(
        id="thermometer",
        title="Термометр / датчик температуры",
        keywords=("термометр", "термопреобразовател", "термопар", "датчик температуры"),
        fields=(
            RANGE,
            ACCURACY,
            RequiredField("Длина погружной части", ("длина", "погруж")),
            CONNECTION,
            PROTECTION,
            REGISTRY,
            VERIFICATION,
        ),
    ),
    DeviceProfile(
        id="flowmeter",
        title="Расходомер / счётчик",
        keywords=("расходомер", "счетчик", "расхода"),
        fields=(
            RequiredField("Диаметр условного прохода (DN)", ("ду", "dn", "условн", "номинальный диаметр")),
            RequiredField("Диапазон расхода", ("расход",)),
            ACCURACY,
            OUTPUT,
            POWER,
            PROTECTION,
            REGISTRY,
            VERIFICATION,
        ),
    ),
)

# Тип не распознан: мы не знаем, какие поля обязательны для такого изделия,
# поэтому не придумываем их. В «Требует уточнения» попадут только реальные пробелы
# (пустые поля, нет производителя, описания, фото).
GENERIC = DeviceProfile(
    id="generic",
    title="Тип не определён",
    keywords=(),
    fields=(),
)


def detect_device_type(name: str, category: str | None = None) -> DeviceProfile:
    text = _norm(f"{name} {category or ''}")
    for profile in PROFILES:
        if any(keyword in text for keyword in profile.keywords):
            return profile
    return GENERIC


def find_missing(profile: DeviceProfile, spec_names: Iterable[str]) -> list[str]:
    """Названия обязательных полей, которым не соответствует ни одна характеристика."""
    names = list(spec_names)
    return [f.name for f in profile.fields if not any(f.matches(n) for n in names)]
