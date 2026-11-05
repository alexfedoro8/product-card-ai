import pytest
from pydantic import ValidationError

from app.core.normalize import normalize_specs
from app.schemas import ProductInput


def test_empty_name_rejected():
    with pytest.raises(ValidationError):
        ProductInput.model_validate({"name": "   ", "specs": {"a": "1"}})


def test_no_specs_and_no_description_rejected():
    with pytest.raises(ValidationError, match="недостаточно данных"):
        ProductInput.model_validate({"name": "Манометр", "specs": {"класс": "—"}, "description": " "})


def test_description_only_is_enough():
    product = ProductInput.model_validate({"name": "Манометр", "description": "Текст"})
    assert product.specs == {}


def test_invalid_image_url_rejected():
    with pytest.raises(ValidationError):
        ProductInput.model_validate({"name": "Манометр", "description": "x", "images": ["не ссылка"]})


def test_normalize_specs_splits_empty_values():
    clean, empty = normalize_specs(
        {
            " диапазон  измерений ": "0–1,6 МПа",
            "класс точности": "",
            "IP": "—",
            "Диапазон измерений": "дубль",
            "x": None,
            "ex": True,
        }
    )
    assert clean == {"Диапазон измерений": "0–1,6 МПа", "Ex": "да"}
    assert empty == ["Класс точности", "IP", "X"]
