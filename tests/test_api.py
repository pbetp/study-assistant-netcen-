import pytest
from fastapi.testclient import TestClient

from app.api import create_app


@pytest.fixture
def client(embedder, index):
    # The fake embedder gives low scores, so the minimum score is turned off (0.0).
    return TestClient(create_app(embedder, index, min_score=0.0))


def test_health_reports_page_count(client):
    assert client.get("/health").json() == {"status": "ok", "pages": 5}


def test_find_returns_best_range_first(client):
    response = client.get("/find", params={"q": "tcp handshake"})

    assert response.status_code == 200
    best = response.json()["results"][0]
    assert best["chapter"] == "Chapter 1"
    assert best["pages"] == "3-4"
    assert (best["first_page"], best["last_page"]) == (3, 4)
    assert best["titles"] == ["TCP handshake", "TCP handshake: example"]


def test_not_found_is_an_empty_list(embedder, index):
    client = TestClient(create_app(embedder, index, min_score=1.1))

    body = client.get("/find", params={"q": "tcp"}).json()

    assert body == {"query": "tcp", "results": []}


def test_blank_or_missing_query_is_rejected(client):
    assert client.get("/find", params={"q": "   "}).status_code == 422
    assert client.get("/find").status_code == 422
