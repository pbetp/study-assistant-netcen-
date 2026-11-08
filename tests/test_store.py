import pytest

from app.ingest import Page
from app.store import VectorStore


def test_search_returns_best_match_first_with_page_and_title(store, embedder):
    hits = store.search(embedder.embed_query("dns domain names"), limit=2)

    assert (hits[0].page.source, hits[0].page.page, hits[0].page.title) == ("net.pdf", 12, "DNS")
    assert hits[0].score >= hits[1].score


def test_limit_larger_than_store_is_fine(store, embedder):
    assert len(store.search(embedder.embed_query("dns"), limit=50)) == 5


def test_empty_store_returns_no_hits(tmp_path, embedder):
    empty = VectorStore(tmp_path / "empty")
    assert empty.search(embedder.embed_query("anything"), limit=3) == []


def test_adding_same_page_twice_does_not_duplicate(store, embedder):
    page = Page("net.pdf", 12, "DNS", "dns translates domain names into ip addresses")
    store.add([page], embedder.embed_documents([page.text]))
    assert store.count() == 5


def test_add_checks_lengths(store):
    with pytest.raises(ValueError):
        store.add([Page("a.pdf", 1, "t", "x")], [])


def test_data_persists_on_disk(tmp_path, embedder):
    path = tmp_path / "db"
    page = Page("a.pdf", 1, "Hello", "hello world")
    VectorStore(path).add([page], embedder.embed_documents([page.text]))

    assert VectorStore(path).count() == 1


def test_clear_empties_the_store(store):
    store.clear()
    assert store.count() == 0
