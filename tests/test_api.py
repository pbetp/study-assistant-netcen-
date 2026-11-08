import pytest
from fastapi.testclient import TestClient

from app.api import create_app
from app.store import VectorStore


@pytest.fixture
def client(embedder, store):
    return TestClient(create_app(embedder, store))


def test_home_page_is_the_search_form(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert 'id="q"' in response.text and "find?q=" in response.text


def test_health_reports_page_count(client):
    assert client.get("/health").json() == {"status": "ok", "pages": 5}


def test_find_returns_best_range_first(client):
    response = client.get("/find", params={"q": "tcp handshake"})

    assert response.status_code == 200
    best = response.json()["results"][0]
    assert best["file"] == "net.pdf"
    assert best["pages"] == "3-4"
    assert (best["first_page"], best["last_page"]) == (3, 4)
    assert best["titles"] == ["TCP handshake", "TCP handshake: example"]


def test_not_found_is_an_empty_list(embedder, store):
    client = TestClient(create_app(embedder, store, min_score=1.1))

    body = client.get("/find", params={"q": "tcp"}).json()

    assert body == {"query": "tcp", "results": []}


def test_blank_or_missing_query_is_rejected(client):
    assert client.get("/find", params={"q": "   "}).status_code == 422
    assert client.get("/find").status_code == 422


def test_empty_index_gives_503(tmp_path, embedder):
    app = create_app(embedder, VectorStore(tmp_path / "empty"))
    assert TestClient(app).get("/find", params={"q": "dns"}).status_code == 503
