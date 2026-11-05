import json

from app.schemas import ExtractedSpec, LLMDraft
from app.validation import (
    CheckContext,
    DraftValidator,
    ExtractionCoverageCheck,
    LengthCheck,
    default_checks,
    verify_extracted,
)
from app.validation.checks import FILLER_CHECK, RISKY_CHECK, SCOPE_CHECK
from app.validation.text import find_ungrounded_numbers
from tests.conftest import make_draft

SOURCE = (
    "Манометр DM 02\nДиапазон измерений: 0–1,6 МПа\nКласс точности: 1,5\n"
    "Присоединение: G1/2\nДиаметр корпуса: 100 мм"
)


def test_numbers_from_source_pass_with_comma_or_dot():
    assert find_ungrounded_numbers("диапазон 0-1.6 МПа, класс 1,50, DM 02", SOURCE) == []


def test_invented_numbers_are_caught():
    assert find_ungrounded_numbers("степень защиты IP65, корпус 150 мм", SOURCE) == ["65", "150"]


def test_invented_claims_are_caught():
    text = "Корпус из нержавеющей стали, протокол HART, гарантия производителя."
    assert RISKY_CHECK.find(text, SOURCE) == ["нержавеющая сталь", "HART", "гарантия"]


def test_claim_present_in_source_is_allowed():
    assert RISKY_CHECK.find("корпус из нержавеющей стали", SOURCE + "\nКорпус: нержавеющая сталь") == []


def test_lengths():
    draft = LLMDraft.model_validate(
        json.loads(make_draft(title="М" * 71, description_len=500, queries=["a", "a"]))
    )
    issues = LengthCheck().check(CheckContext(draft=draft, source=""))
    # короткое описание не повод для переделки — о нём сообщает оценка данных
    assert len(issues) == 2
    assert "71 символов" in issues[0] and "запросов 1" in issues[1]


def test_valid_draft_has_no_issues():
    draft = LLMDraft.model_validate(json.loads(make_draft(extracted=[])))
    assert DraftValidator().validate(CheckContext(draft=draft, source=SOURCE)) == []


def test_extracted_specs_require_exact_quote():
    description = "Степень защиты корпуса — IP40. Температура среды до +150 °C."
    accepted, rejected = verify_extracted(
        [
            ExtractedSpec(name="Степень защиты", value="IP40", source_quote="Степень защиты корпуса - IP40"),
            ExtractedSpec(name="Материал", value="латунь", source_quote="штуцер из латуни"),
            ExtractedSpec(name="Температура среды", value="до +200 °C", source_quote="до +150 °C"),
        ],
        description,
    )
    assert [s.name for s in accepted] == ["Степень защиты"]
    assert len(rejected) == 2


# Реальный ответ модели на МП4-У: «вода» и выдуманные отрасли при формально верных числах.
MP4_SOURCE = (
    "МП4-У - манометр показывающий\nКазань\nДиаметр корпуса: 160 мм\nВес: 1 кг\nКласс точности: 1\n"
    "По устойчивости к климатическим воздействиям приборы имеют исполнение У2 и Т2. "
    "Приборы выдерживают воздействие вибрации в диапазоне частот от 5 до 25 Гц с амплитудой до 0,1 мм. "
    "Гарантийный срок эксплуатации - 3 года."
)
MP4_TEXT = (
    "Манометр МП4-У предназначен для контроля давления в различных системах. Класс точности 1 "
    "позволяет использовать его там, где требуется высокая точность. Это отличный выбор для инженеров. "
    "Он может быть использован в энергетике, химии и машиностроении."
)


def test_invented_scope_is_caught():
    assert SCOPE_CHECK.find(MP4_TEXT, MP4_SOURCE) == [
        "энергетика",
        "химическая промышленность",
        "машиностроение",
    ]


def test_filler_is_caught():
    assert FILLER_CHECK.find(MP4_TEXT, MP4_SOURCE) == [
        "«отличный»",
        "«высокая точность»",
        "«различные …»",
        "«позволяет / обеспечивает»",
    ]


def test_scope_present_in_input_is_allowed():
    assert SCOPE_CHECK.find("применяется в системах отопления", "для систем отопления") == []


def test_values_lost_from_description_are_caught():
    description = MP4_SOURCE.split("Класс точности: 1\n")[1]
    known = "МП4-У\nДиаметр корпуса\n160 мм\nВес\n1 кг\nКласс точности\n1"
    draft = LLMDraft.model_validate(json.loads(make_draft(extracted=[])))
    ctx = CheckContext(draft=draft, source="", description=description, known=known)
    assert ExtractionCoverageCheck.find_lost(ctx) == ["2", "5", "25", "0,1", "3"]

    full = LLMDraft.model_validate(
        json.loads(
            make_draft(
                extracted=[
                    {
                        "name": "Климатическое исполнение",
                        "value": "У2 и Т2",
                        "source_quote": "исполнение У2 и Т2",
                    },
                    {"name": "Виброустойчивость", "value": "5–25 Гц, до 0,1 мм", "source_quote": "x"},
                    {"name": "Гарантийный срок", "value": "3 года", "source_quote": "x"},
                ]
            )
        )
    )
    ctx = CheckContext(draft=full, source="", description=description, known=known)
    assert ExtractionCoverageCheck.find_lost(ctx) == []


def test_invented_usage_scenarios_are_caught():
    text = "Подходит для трубопроводов и котельных, монтаж прост, обслуживание удобно."
    assert SCOPE_CHECK.find(text, SOURCE) == [
        "трубопроводы",
        "котельные",
        "монтаж и установка",
        "обслуживание",
    ]
    assert FILLER_CHECK.find(text, SOURCE) == ["«удобный»"]


def test_custom_check_plugs_into_validator():
    """Открытость к расширению: своя проверка добавляется без правок генератора."""

    class NoExclamation:
        def check(self, ctx):
            return ["Без восклицательных знаков."] if "!" in ctx.generated_text else []

    draft = LLMDraft.model_validate(json.loads(make_draft(title="Манометр DM 02!", extracted=[])))
    validator = DraftValidator([*default_checks(), NoExclamation()])
    assert validator.validate(CheckContext(draft=draft, source=SOURCE)) == ["Без восклицательных знаков."]
