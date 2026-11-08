import json

import numpy as np
import pytest

from app.config import CANDIDATE_PAGES, MAX_RESULTS, MIN_SCORE
from app.index import Index
from app.ingest import Page


def test_search_returns_best_match_first_with_page_and_title(index, embedder):
    hits = index.search(embedder.embed_query("dns domain names"), limit=2)

    best = hits[0].page
    assert (best.chapter, best.page, best.title) == ("Chapter 1", 12, "DNS")
    assert hits[0].score >= hits[1].score


def test_limit_larger_than_the_index_is_fine(index, embedder):
    assert len(index.search(embedder.embed_query("dns"), limit=50)) == 5


def test_pages_and_vectors_must_have_the_same_length():
    with pytest.raises(ValueError):
        Index([Page("Chapter 1", 1, "t", "x")], [])


def test_vectors_file_can_be_read_back_row_by_row(tmp_path, index):
    index.save(tmp_path, model="some/model")

    matrix = np.frombuffer((tmp_path / "vectors.bin").read_bytes(), dtype="<f4").reshape(5, 64)

    assert np.array_equal(matrix, index.vectors)


def test_pages_json_refers_to_chapters_by_position(tmp_path, index):
    index.save(tmp_path, model="some/model")

    data = json.loads((tmp_path / "pages.json").read_text(encoding="utf-8"))

    assert data["chapters"] == ["Chapter 1", "Chapter 2"]
    assert data["pages"][0] == [0, 3, "TCP handshake"]
    assert data["pages"][-1] == [1, 5, ""]


def test_config_tells_the_page_how_to_search(tmp_path, index):
    index.save(tmp_path, model="some/model")

    config = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))

    assert config["model"] == "some/model"
    assert config["query_prefix"] == "query: "
    assert (config["dim"], config["count"]) == (64, 5)
    assert (config["min_score"], config["candidates"], config["max_results"]) == (
        MIN_SCORE,
        CANDIDATE_PAGES,
        MAX_RESULTS,
    )


def test_a_saved_index_searches_like_the_original(tmp_path, index, embedder):
    index.save(tmp_path, model="some/model")
    loaded = Index.load(tmp_path)
    query = embedder.embed_query("tcp handshake syn")

    def summary(idx):
        return [(h.page.chapter, h.page.page, h.page.title, h.score) for h in idx.search(query, 5)]

    assert summary(loaded) == summary(index)


def test_slide_text_is_never_saved(tmp_path, index):
    index.save(tmp_path, model="some/model")

    for file in tmp_path.iterdir():
        assert b"stateless" not in file.read_bytes()
    assert all(page.text == "" for page in Index.load(tmp_path).pages)


def test_loading_a_missing_index_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        Index.load(tmp_path / "nothing-here")
