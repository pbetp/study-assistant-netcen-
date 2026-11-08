"""The search index: the vector of every slide page, saved as three small files.

    vectors.bin  all page vectors as float32, one page after another (625 x 384 = ~1 MB)
    pages.json   for each row of vectors.bin: which chapter, which page, which title
    config.json  the model and the search settings

The web page (site/) reads these very same files, so Python and JavaScript search the
same data in the same way. Only titles and vectors are saved, never the slide text.

With so few vectors, searching is just: compare the query with all of them, sort, take the best.
That takes 0.03 ms for 625 vectors, so no vector database is needed.
"""

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from app.config import CANDIDATE_PAGES, MAX_RESULTS, MIN_SCORE
from app.embed import QUERY_PREFIX
from app.ingest import Page


@dataclass(frozen=True)
class Hit:
    page: Page
    score: float  # cosine similarity: higher = more similar (max 1.0)


class Index:
    def __init__(self, pages: list[Page], vectors: list[list[float]] | np.ndarray):
        if len(pages) != len(vectors):
            raise ValueError("pages and vectors must have the same length")
        self.pages = pages
        # Little-endian float32: the format the file is saved in, and what JavaScript reads.
        self.vectors = np.asarray(vectors, dtype="<f4")

    def search(self, query_vector: list[float], limit: int) -> list[Hit]:
        """The `limit` pages closest to the query, best first."""
        # Every vector has length 1, so the dot product is the cosine similarity.
        scores = self.vectors @ np.asarray(query_vector)
        best = np.argsort(-scores, kind="stable")[:limit]  # stable: ties keep page order
        return [Hit(self.pages[i], float(scores[i])) for i in best]

    def save(self, directory: Path, model: str) -> None:
        # Each chapter name is stored once and a row refers to it by position.
        chapters = list(dict.fromkeys(p.chapter for p in self.pages))
        rows = [[chapters.index(p.chapter), p.page, p.title] for p in self.pages]
        config = {
            "model": model,
            "dtype": "q8",  # transformers.js name for the quantized model file
            "query_prefix": QUERY_PREFIX,
            "dim": int(self.vectors.shape[1]),
            "count": len(self.pages),
            "min_score": MIN_SCORE,
            "candidates": CANDIDATE_PAGES,
            "max_results": MAX_RESULTS,
        }
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "vectors.bin").write_bytes(self.vectors.tobytes())
        (directory / "pages.json").write_text(
            json.dumps(
                {"chapters": chapters, "pages": rows}, ensure_ascii=False, separators=(",", ":")
            ),
            encoding="utf-8",
        )
        (directory / "config.json").write_text(
            json.dumps(config, indent=2) + "\n", encoding="utf-8"
        )

    @classmethod
    def load(cls, directory: Path) -> "Index":
        config = json.loads((directory / "config.json").read_text(encoding="utf-8"))
        data = json.loads((directory / "pages.json").read_text(encoding="utf-8"))
        raw = (directory / "vectors.bin").read_bytes()
        vectors = np.frombuffer(raw, dtype="<f4").reshape(config["count"], config["dim"])
        # The slide text is not saved, so loaded pages have none (searching does not need it).
        pages = [Page(data["chapters"][c], page, title, "") for c, page, title in data["pages"]]
        return cls(pages, vectors)
