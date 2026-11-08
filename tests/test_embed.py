import math

import numpy as np

from app.embed import FakeEmbedder, mean_pool, normalize


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


def test_mean_pool_averages_real_tokens_and_ignores_padding():
    # One text with 3 token slots, of which the last is padding (mask 0).
    hidden = np.array([[[1.0, 0.0], [3.0, 4.0], [100.0, 100.0]]])
    mask = np.array([[1, 1, 0]])

    assert mean_pool(hidden, mask).tolist() == [[2.0, 2.0]]  # (1+3)/2 and (0+4)/2


def test_normalize_gives_every_vector_length_one():
    unit = normalize(np.array([[3.0, 4.0], [0.0, 2.0]]))

    assert np.allclose(np.linalg.norm(unit, axis=1), 1.0)
    assert unit[0].tolist() == [0.6, 0.8]
