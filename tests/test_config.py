from pathlib import Path

from app.config import MAX_RESULTS, MIN_SCORE, Settings


def test_defaults_work_without_any_environment(monkeypatch):
    for name in ("DOCS_DIR", "INDEX_DIR", "EMBED_MODEL"):
        monkeypatch.delenv(name, raising=False)

    s = Settings.from_env()

    assert s.docs_dir == Path("data")
    assert s.index_dir == Path("site/index")
    assert s.embed_model == "Xenova/multilingual-e5-small"


def test_environment_overrides_defaults(monkeypatch):
    monkeypatch.setenv("DOCS_DIR", "other_course")
    monkeypatch.setenv("INDEX_DIR", "other_index")

    s = Settings.from_env()

    assert s.docs_dir == Path("other_course")
    assert s.index_dir == Path("other_index")


def test_tuning_values_are_sensible():
    assert 0 < MIN_SCORE < 1
    assert MAX_RESULTS >= 1
