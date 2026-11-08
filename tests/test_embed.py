import math

from app.embed import FakeEmbedder


def dot(a, b):
    return sum(x * y for x, y in zip(a, b, strict=True))


def test_fake_embedder_is_deterministic():
    e = FakeEmbedder()
    assert e.embed_query("tcp handshake") == e.embed_query("tcp handshake")


def test_vectors_have_length_one():
    v = FakeEmbedder().embed_query("some words here")
    assert math.isclose(math.sqrt(dot(v, v)), 1.0)


def test_shared_words_mean_higher_similarity():
    e = FakeEmbedder()
    query = e.embed_query("what is the tcp handshake")
    related = e.embed_documents(["the tcp handshake has three steps"])[0]
    unrelated = e.embed_documents(["bananas grow in warm climates"])[0]
    assert dot(query, related) > dot(query, unrelated)


def test_empty_text_does_not_crash():
    assert len(FakeEmbedder(dim=8).embed_query("")) == 8
