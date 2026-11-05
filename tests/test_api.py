"""Проверка HTTP-слоя. Запускается, когда установлены зависимости проекта (uv sync)."""

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from app import main  # noqa: E402
from app.api.dependencies import get_llm_client  # noqa: E402
from app.core.config import UPLOAD_DIR  # noqa: E402
from tests.conftest import FakeLLM, make_draft  # noqa: E402

client = TestClient(main.app)


def test_index_and_health():
    assert client.get("/").status_code == 200
    assert client.get("/health").json()["status"] == "ok"


def test_broken_json_returns_readable_422():
    response = client.post(
        "/api/v1/cards", content='{"name": "x", "specs": {', headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 422
    assert response.json()["details"][0].startswith("Некорректный JSON")


def test_insufficient_data_422():
    response = client.post("/api/v1/cards", json={"name": "Манометр", "specs": {"класс точности": ""}})
    assert response.status_code == 422
    assert "недостаточно данных" in " ".join(response.json()["details"])


def test_card_created():
    main.app.dependency_overrides[get_llm_client] = lambda: FakeLLM(make_draft(extracted=[]))
    payload = {
        "name": "Манометр показывающий DM 02",
        "specs": {"диапазон измерений": "0–1,6 МПа", "присоединение": "G1/2"},
    }
    response = client.post("/api/v1/cards", json=payload)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["seo_title"] and body["markdown"]
    assert any(m["name"] == "Фото товара" for m in body["missing_fields"])
    assert all(m["value"] == "данных нет" for m in body["missing_fields"])
    main.app.dependency_overrides.clear()


PNG_1PX = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000d49444154789c63000100000500010d0a2db40000000049454e44ae426082"
)


def test_image_upload_returns_url_usable_in_card():
    response = client.post("/api/v1/images", content=PNG_1PX, headers={"Content-Type": "image/png"})
    assert response.status_code == 200, response.text
    url = response.json()["url"]
    assert url.endswith(".png")
    assert client.get(url).status_code == 200
    (UPLOAD_DIR / url.rsplit("/", 1)[1]).unlink()


def test_non_image_upload_rejected():
    response = client.post("/api/v1/images", content=b"%PDF-1.4 not an image")
    assert response.status_code == 415
    assert response.json()["code"] == "not_an_image"
