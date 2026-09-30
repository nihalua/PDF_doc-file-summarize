from docsum import settings


def test_save_load_forget(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert settings.load_api_key() is None
    settings.save_api_key("  sk-ant-test  ")
    assert settings.load_api_key() == "sk-ant-test"
    settings.forget_api_key()
    assert settings.load_api_key() is None


def test_env_var_wins(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("APPDATA", str(tmp_path))
    settings.save_api_key("saved")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "from-env")
    assert settings.load_api_key() == "from-env"


def test_corrupt_config_is_ignored(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    settings.config_path().parent.mkdir(parents=True)
    settings.config_path().write_text("{not json")
    assert settings.load_api_key() is None
