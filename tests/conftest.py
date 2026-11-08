"""Shared test setup: a tiny indexed store built with the fake embedder (no model, no network)."""

import pytest

from app.embed import FakeEmbedder
from app.ingest import Page
from app.store import VectorStore

PAGES = [
    Page(
        "net.pdf", 3, "TCP handshake", "tcp handshake uses syn and ack packets to open a connection"
    ),
    Page("net.pdf", 4, "TCP handshake: example", "tcp handshake example with syn synack and ack"),
    Page(
        "net.pdf", 7, "HTTP", "http is a stateless request response protocol used by web browsers"
    ),
    Page("net.pdf", 12, "DNS", "dns translates domain names into ip addresses"),
    Page("other.pdf", 5, "", "router queue diagram"),  # a diagram slide without a title
]


@pytest.fixture
def embedder():
    return FakeEmbedder()


@pytest.fixture
def store(tmp_path, embedder):
    s = VectorStore(tmp_path / "db", name="test")
    s.add(PAGES, embedder.embed_documents([p.text for p in PAGES]))
    return s
