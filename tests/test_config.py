from pathlib import Path

from app.config import Settings


def test_defaults_work_without_any_environment(monkeypatch):
    for name in ("DOCS_DIR", "VECTOR_STORE_DIR", "EMBED_MODEL", "MIN_SCORE"):
        monkeypatch.delenv(name, raising=False)

    s = Settings.from_env()

    assert s.docs_dir == Path("data")
    assert s.store_dir == Path("chroma_db")
    assert 0 < s.min_score < 1


def test_environment_overrides_defaults(monkeypatch):
    monkeypatch.setenv("DOCS_DIR", "other_course")
    monkeypatch.setenv("MIN_SCORE", "0.5")

    s = Settings.from_env()

    assert s.docs_dir == Path("other_course")
    assert s.min_score == 0.5
