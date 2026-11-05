import pytest

from app.core.config import PROVIDERS, Settings, resolve_provider
from app.core.errors import ConfigError
from app.llm import LazyLLMClient, create_client, register_client


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for provider in PROVIDERS.values():
        monkeypatch.delenv(provider.key_env, raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)


def test_no_keys_no_provider():
    assert resolve_provider() is None


@pytest.mark.parametrize(
    ("env", "expected"),
    [
        ({"DEEPSEEK_API_KEY": "k"}, "deepseek"),
        ({"ANTHROPIC_API_KEY": "k"}, "anthropic"),
        ({"OPENAI_API_KEY": "k", "OPENROUTER_API_KEY": "k"}, "openrouter"),  # приоритет по порядку
        ({"OPENAI_API_KEY": "k", "OPENROUTER_API_KEY": "k", "LLM_PROVIDER": "OpenAI"}, "openai"),
    ],
)
def test_provider_selected_by_key(monkeypatch, env, expected):
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    provider = resolve_provider()
    assert provider is not None and provider.id == expected


def test_unknown_explicit_provider(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gigachat")
    with pytest.raises(ConfigError):
        resolve_provider()


def test_client_without_key_gives_clear_error():
    with pytest.raises(ConfigError) as exc:
        create_client(Settings(None, "", None, "-"))
    assert exc.value.http_status == 503


def test_new_api_kind_plugs_in_without_code_changes():
    """Открытость к расширению: новый вид API регистрируется в фабрике."""
    from dataclasses import replace

    class EchoClient:
        def __init__(self, settings):
            self.model = settings.model

        def complete(self, messages, temperature):
            return "ok"

    register_client("echo", EchoClient)
    provider = replace(PROVIDERS["openai"], id="local", kind="echo")
    client = create_client(Settings(provider, "key", None, "local-model"))
    assert isinstance(client, EchoClient) and client.complete([], 0) == "ok"


def test_lazy_client_creates_real_client_only_on_first_call():
    created = []

    def factory(settings):
        created.append(settings.model)
        return type("C", (), {"model": settings.model, "complete": lambda self, m, t: "answer"})()

    lazy = LazyLLMClient(Settings(None, "", None, "m"), factory=factory)
    assert created == [] and lazy.model == "m"
    assert lazy.complete([], 0) == "answer" and created == ["m"]
