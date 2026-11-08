"""Vector store, backed by Chroma and saved to disk.

The store keeps, for every slide page: its vector, its text, its file, page number and title.
Searching returns the pages whose vectors are closest to the query's vector.
"""

from dataclasses import dataclass
from pathlib import Path

import chromadb

from app.ingest import Page

BATCH_SIZE = 500  # Chroma rejects very large single writes, so we write in batches


@dataclass(frozen=True)
class Hit:
    page: Page
    score: float  # cosine similarity: higher = more similar (max 1.0)


class VectorStore:
    def __init__(self, path: Path, name: str = "slides"):
        self._client = chromadb.PersistentClient(path=str(path))
        self._name = name
        self._collection = self._open()

    def _open(self):
        # "cosine" tells Chroma to measure closeness by angle, which suits
        # normalised sentence embeddings.
        return self._client.get_or_create_collection(self._name, metadata={"hnsw:space": "cosine"})

    def add(self, pages: list[Page], vectors: list[list[float]]) -> None:
        """Save pages with their vectors. Same page id again = overwrite (no duplicates)."""
        if len(pages) != len(vectors):
            raise ValueError("pages and vectors must have the same length")
        for i in range(0, len(pages), BATCH_SIZE):
            batch = pages[i : i + BATCH_SIZE]
            self._collection.upsert(
                ids=[p.id for p in batch],
                embeddings=vectors[i : i + BATCH_SIZE],
                documents=[p.text for p in batch],
                metadatas=[{"source": p.source, "page": p.page, "title": p.title} for p in batch],
            )

    def search(self, query_vector: list[float], limit: int) -> list[Hit]:
        """Return up to `limit` closest pages, best first."""
        total = self.count()
        if total == 0:
            return []
        result = self._collection.query(
            query_embeddings=[query_vector], n_results=min(limit, total)
        )
        hits = []
        for text, meta, distance in zip(
            result["documents"][0], result["metadatas"][0], result["distances"][0], strict=True
        ):
            page = Page(source=meta["source"], page=meta["page"], title=meta["title"], text=text)
            # Chroma returns a distance (smaller = closer); 1 - distance is the similarity.
            hits.append(Hit(page=page, score=1.0 - distance))
        return hits

    def count(self) -> int:
        return self._collection.count()

    def clear(self) -> None:
        """Delete everything, used before a full re-index."""
        self._client.delete_collection(self._name)
        self._collection = self._open()
