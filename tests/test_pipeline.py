import pytest

from app.core.errors import LLMError
from app.services.parsing import parse_draft
from tests.conftest import FakeLLM, generate, make_draft


def test_happy_path_single_call(dm02):
    llm = FakeLLM(
        make_draft(
            extracted=[
                {"name": "степень защиты", "value": "IP40", "source_quote": "Степень защиты корпуса — IP40"}
            ]
        )
    )
    card = generate(dm02, llm)

    assert len(llm.calls) == 1
    assert card.meta.attempts == 1
    assert card.warnings == []
    assert card.key_specs[0].name == "Производитель"
    from_description = [r for r in card.key_specs if r.source == "описание"]
    assert [(r.name, r.value) for r in from_description] == [("Степень защиты", "IP40")]
    missing = {m.name for m in card.missing_fields}
    assert {"Номер в Госреестре СИ", "Межповерочный интервал", "Фото товара"} <= missing
    assert "Степень защиты (IP)" not in missing  # закрыто значением из описания
    assert "данных нет" in card.markdown
    assert all(m.value == "данных нет" for m in card.missing_fields)
    assert card.data_quality.level == "gaps"
    assert card.data_quality.facts_count == len(card.key_specs)


def test_retry_fixes_length_and_invented_number(dm02):
    llm = FakeLLM(make_draft(description_len=1500, extra="Защита IP65. "), make_draft())
    card = generate(dm02, llm)

    assert card.meta.attempts == 2
    assert card.warnings == []
    feedback = llm.calls[1][-1]["content"]
    assert "Сократи" in feedback and "65" in feedback


def test_warnings_kept_when_model_does_not_fix(dm02):
    bad = make_draft(extra="Гарантия три года. ")
    card = generate(dm02, FakeLLM(bad, bad, bad), max_attempts=3)
    assert card.meta.attempts == 3
    assert any("гарантия" in w for w in card.warnings)
    assert not any("Убери" in w for w in card.warnings)  # пользователю — без инструкций для модели


def test_broken_model_json_then_ok(dm02):
    card = generate(dm02, FakeLLM("вот ваш ответ: {oops", make_draft()))
    assert card.meta.attempts == 2


def test_model_never_returns_json(dm02):
    with pytest.raises(LLMError) as exc:
        generate(dm02, FakeLLM("нет", "нет"), max_attempts=2)
    assert exc.value.code == "llm_bad_format"


def test_empty_fields_reported_once():
    from app.schemas import ProductInput

    product = ProductInput.model_validate(
        {
            "name": "Термометр биметаллический ТБ-63",
            "specs": {"диапазон измерений": "0–120 °C", "класс точности": ""},
        }
    )
    draft = make_draft(title="Термометр ТБ-63 0–120 °C", as_list=False).replace(
        "Манометр показывающий DM 02 с диапазоном 0–1,6 МПа и присоединением G1/2. ",
        "Термометр ТБ-63 с диапазоном 0–120 °C. ",
    )
    draft = draft.replace("манометр 1,6 мпа g1/2", "термометр 0-120").replace("dm 02", "тб-63")
    card = generate(product, FakeLLM(draft))
    names = [m.name for m in card.missing_fields]
    assert names.count("Класс точности") == 1
    assert "Класс точности / погрешность" not in names
    assert "Производитель" in names and "Текстовое описание / паспорт" in names


def test_parse_draft_strips_code_fence():
    draft = parse_draft("```json\n" + make_draft() + "\n```")
    assert draft.seo_title.startswith("Манометр")


def test_short_description_is_reported_not_padded(dm02):
    llm = FakeLLM(make_draft(description_len=500))
    card = generate(dm02, llm)
    assert len(llm.calls) == 1  # без повтора: просьба «допиши» порождает «воду»
    assert card.data_quality.level == "poor"
    description_check = next(r for r in card.data_quality.requirements if r.name.startswith("SEO-описание"))
    assert not description_check.ok and "больше фактов" in description_check.hint
    assert any("паспорт" in tip for tip in card.data_quality.how_to_improve)
    assert card.warnings == []  # это замечание о данных, а не о тексте модели


def test_lost_description_values_trigger_retry(dm02):
    llm = FakeLLM(make_draft(extracted=[]), make_draft())
    card = generate(dm02, llm)
    assert card.meta.attempts == 2
    assert "40" in llm.calls[1][-1]["content"]
    assert any(r.value == "IP40" for r in card.key_specs)


def test_unknown_item_type_gets_no_invented_required_fields():
    from app.schemas import ProductInput

    product = ProductInput.model_validate(
        {"name": "Кран шаровой КШ-15", "manufacturer": "Завод", "specs": {"DN": "15"}, "description": "Кран."}
    )
    draft = make_draft(title="Кран шаровой КШ-15", extracted=[]).replace(
        "Манометр показывающий DM 02", "Кран КШ-15"
    )
    card = generate(product, FakeLLM(draft))
    assert card.meta.device_type == "Тип не определён"
    assert [m.name for m in card.missing_fields] == ["Фото товара"]
    assert card.data_quality.gaps_count == 0


def test_issue_for_user_drops_model_instructions():
    from app.validation import issue_for_user

    issue = (
        "В описании товара есть характеристики со значениями 150, "
        "которых нет ни в specs, ни в extracted_specs. "
        "Вынеси каждую в extracted_specs с дословной цитатой из описания."
    )
    assert issue_for_user(issue) == (
        "В описании товара есть характеристики со значениями 150, которые не попали в таблицу характеристик."
    )
    assert issue_for_user("SEO-заголовок 80 символов, нужно не больше 70. Сократи.") == (
        "SEO-заголовок 80 символов, нужно не больше 70."
    )


def test_description_is_not_listed_as_a_characteristic():
    from app.schemas import ProductInput

    product = ProductInput.model_validate(
        {"name": "Термометр ТБ-63", "specs": {"диапазон измерений": "0–120 °C"}}
    )
    draft = make_draft(title="Термометр ТБ-63", description_len=300, extracted=[])
    q = generate(product, FakeLLM(draft)).data_quality
    specs_check = next(r for r in q.requirements if r.name == "Характеристики без пробелов")
    assert "описание" not in specs_check.hint.lower()
    assert any(tip.startswith("Описание не передано") for tip in q.how_to_improve)


def test_parameters_must_be_listed(dm02):
    llm = FakeLLM(make_draft(as_list=False), make_draft())
    card = generate(dm02, llm)
    assert card.meta.attempts == 2
    assert "списком" in llm.calls[1][-1]["content"]
    assert "\n- Диапазон измерений — 0–1,6 МПа," in card.seo_description


def test_list_markers_normalized():
    from app.schemas import LLMDraft

    draft = LLMDraft(
        seo_title="t",
        seo_description="Вступление.\n\nОсновные характеристики:\n• Класс — 1,5,\n– Диаметр — 100 мм.",
        search_queries=["a"],
        commercial_block="c",
    )
    assert draft.seo_description.endswith("- Класс — 1,5,\n- Диаметр — 100 мм.")
