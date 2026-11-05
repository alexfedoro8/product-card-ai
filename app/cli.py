"""Пакетный прогон из командной строки.

    python -m app.cli товар1.json товар2.json

Для каждого файла пишет <имя>.json и <имя>.md в папку --out (по умолчанию examples/output).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from app.core.config import EXAMPLES_DIR, get_settings
from app.core.errors import AppError
from app.llm import create_client
from app.schemas import ProductInput
from app.services import CardGenerator


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Черновики карточек товаров КИП из JSON-файлов")
    parser.add_argument("files", nargs="+", type=Path, help="JSON-файлы с данными товаров")
    parser.add_argument("--out", type=Path, default=EXAMPLES_DIR / "output", help="папка для результатов")
    args = parser.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # кириллица в консоли Windows

    try:
        settings = get_settings()
        client = create_client(settings)
    except AppError as exc:
        print(f"Ошибка настройки: {exc.message}")
        return 2
    generator = CardGenerator(client, max_attempts=settings.max_attempts, temperature=settings.temperature)
    provider = settings.provider.title if settings.provider else "—"
    print(f"Провайдер: {provider}, модель: {settings.model}")

    args.out.mkdir(parents=True, exist_ok=True)
    failed = 0
    for path in args.files:
        print(f"→ {path.name}: ", end="", flush=True)
        try:
            product = ProductInput.model_validate(json.loads(path.read_text(encoding="utf-8")))
            card = generator.generate(product)
        except FileNotFoundError:
            print("файл не найден")
        except json.JSONDecodeError as exc:
            print(f"некорректный JSON (строка {exc.lineno}, столбец {exc.colno}): {exc.msg}")
        except ValidationError as exc:
            reasons = "; ".join(
                f"{'.'.join(map(str, e['loc'])) or 'данные'}: {e['msg'].removeprefix('Value error, ')}"
                for e in exc.errors()
            )
            print(f"данные не прошли проверку — {reasons}")
        except AppError as exc:
            print(f"ошибка модели — {exc.message}")
        else:
            (args.out / f"{path.stem}.json").write_text(card.model_dump_json(indent=2), encoding="utf-8")
            (args.out / f"{path.stem}.md").write_text(card.markdown, encoding="utf-8")
            print(
                f"готово (попыток: {card.meta.attempts}, не хватает полей: {len(card.missing_fields)}, "
                f"замечаний: {len(card.warnings)})"
            )
            continue
        failed += 1

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
