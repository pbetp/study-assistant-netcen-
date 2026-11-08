"""Shared test setup: a tiny index built with the fake embedder (no model, no network)."""

import pytest

from app.embed import FakeEmbedder
from app.index import Index
from app.ingest import Page

PAGES = [
    Page(
        "Chapter 1",
        3,
        "TCP handshake",
        "tcp handshake uses syn and ack packets to open a connection",
    ),
    Page("Chapter 1", 4, "TCP handshake: example", "tcp handshake example with syn synack and ack"),
    Page(
        "Chapter 1", 7, "HTTP", "http is a stateless request response protocol used by web browsers"
    ),
    Page("Chapter 1", 12, "DNS", "dns translates domain names into ip addresses"),
    Page("Chapter 2", 5, "", "router queue diagram"),  # a diagram slide without a title
]


@pytest.fixture
def embedder():
    return FakeEmbedder()


@pytest.fixture
def index(embedder):
    return Index(PAGES, embedder.embed_documents([p.text for p in PAGES]))
