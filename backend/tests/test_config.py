from app.config import Settings, load_dotenv
from app.llm import MockProvider, OpenAIProvider, make_provider


def test_dotenv_does_not_override_real_env(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("# comment\nLLM_MODEL='from-file'\nPK_DURATION_S=45\n", encoding="utf-8")
    monkeypatch.delenv("PK_DURATION_S", raising=False)
    monkeypatch.setenv("LLM_MODEL", "from-shell")
    load_dotenv(env)
    assert Settings.from_env().pk_duration_s == 45
    assert Settings.from_env().llm_model == "from-shell"


def test_provider_selection():
    assert isinstance(make_provider(Settings()), MockProvider)
    assert isinstance(make_provider(Settings(llm_provider="openai")), MockProvider)  # no key
    assert isinstance(make_provider(Settings(llm_provider="openai", llm_api_key="k")), OpenAIProvider)
