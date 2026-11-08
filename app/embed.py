"""Step 3: turn text into vectors (embeddings).

An embedding is a list of numbers; texts with similar meaning get similar numbers,
so "find relevant slides" becomes "find the closest vectors".

Two implementations share one small interface (`Embedder`):
- SentenceTransformerEmbedder: the real multilingual model (Thai + English), runs locally.
- FakeEmbedder: deterministic and instant, used in tests so they need no model or network.
"""

import hashlib
import math
import re
from pathlib import Path
from typing import Protocol


class Embedder(Protocol):
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class SentenceTransformerEmbedder:
    """Wraps a sentence-transformers model. The model is downloaded once into cache_dir."""

    def __init__(self, model_name: str, cache_dir: Path = Path(".cache/models")):
        # Imported here, not at the top, so importing this file stays fast and tests
        # that use FakeEmbedder never load torch.
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name, cache_folder=str(cache_dir))
        # E5 models were trained with these prefixes; leaving them out lowers quality.
        self._is_e5 = "e5" in model_name.lower()

    def _encode(self, texts: list[str]) -> list[list[float]]:
        # normalize_embeddings=True makes every vector length 1, so cosine similarity
        # is just a dot product and scores stay between -1 and 1.
        vectors = self._model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return vectors.tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if self._is_e5:
            texts = [f"passage: {t}" for t in texts]
        return self._encode(texts)

    def embed_query(self, text: str) -> list[float]:
        if self._is_e5:
            text = f"query: {text}"
        return self._encode([text])[0]


class FakeEmbedder:
    """Bag-of-words hashing: every word adds 1 to one of `dim` buckets.

    Texts that share words end up with similar vectors, so retrieval tests behave
    sensibly. md5 is used instead of Python's hash() because hash() changes between runs.
    """

    def __init__(self, dim: int = 64):
        self.dim = dim

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dim
        for word in re.findall(r"\w+", text.lower()):
            bucket = int(hashlib.md5(word.encode()).hexdigest(), 16) % self.dim
            vector[bucket] += 1.0
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)
