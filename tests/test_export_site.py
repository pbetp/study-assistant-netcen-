import json

import numpy as np

from app.embed import FakeEmbedder
from app.export_site import export_site_index
from app.ingest import Page

PAGES = [
    Page("Chapter_1_(pdf)-1-2.pdf", 4, "Intro", "secret slide text about the internet"),
    Page("Chapter_1_(pdf)-1-2.pdf", 5, "", "another secret slide text"),
    Page("Chapter_2_(pdf)-3-4.pdf", 9, "DNS", "secret dns slide text"),
]


def export(tmp_path):
    vectors = FakeEmbedder(dim=8).embed_documents([p.text for p in PAGES])
    export_site_index(PAGES, vectors, tmp_path / "out", model="some/model", min_score=0.8)
    return tmp_path / "out", vectors


def test_vectors_file_can_be_read_back_row_by_row(tmp_path):
    out, vectors = export(tmp_path)

    matrix = np.frombuffer((out / "vectors.bin").read_bytes(), dtype="<f4").reshape(3, 8)

    assert np.allclose(matrix, np.asarray(vectors, dtype=np.float32))


def test_pages_json_refers_to_chapters_by_position(tmp_path):
    out, _ = export(tmp_path)

    data = json.loads((out / "pages.json").read_text(encoding="utf-8"))

    assert data["chapters"] == ["Chapter 1", "Chapter 2"]
    assert data["pages"] == [[0, 4, "Intro"], [0, 5, ""], [1, 9, "DNS"]]


def test_config_tells_the_page_how_to_search(tmp_path):
    out, _ = export(tmp_path)

    config = json.loads((out / "config.json").read_text(encoding="utf-8"))

    assert config["model"] == "some/model" and config["min_score"] == 0.8
    assert config["dim"] == 8 and config["count"] == 3
    assert config["query_prefix"] == "query: "


def test_slide_text_is_never_exported(tmp_path):
    out, _ = export(tmp_path)

    for file in out.iterdir():
        assert b"secret" not in file.read_bytes()
