"""Export the index as static files for the browser version of the app (site/).

A browser cannot read Chroma, so the same data is written as three small files:

    vectors.bin  every page vector as float32, one page after another (625 x 384 = ~1 MB)
    pages.json   for each row of vectors.bin: which chapter, which page, which title
    config.json  the model and search settings the web page must use

Only slide titles and vectors are exported, never the slide text.
"""

import json
from pathlib import Path

import numpy as np

from app.embed import QUERY_PREFIX
from app.ingest import Page
from app.search import CANDIDATE_PAGES, MAX_RESULTS, display_name


def export_site_index(
    pages: list[Page],
    vectors: list[list[float]],
    out_dir: Path,
    model: str,
    min_score: float,
) -> None:
    if len(pages) != len(vectors):
        raise ValueError("pages and vectors must have the same length")
    matrix = np.asarray(vectors, dtype="<f4")  # little-endian float32, what JavaScript reads

    # Each file is stored once; a row refers to it by position, so the long file
    # name is not repeated 625 times.
    sources = list(dict.fromkeys(p.source for p in pages))
    rows = [[sources.index(p.source), p.page, p.title] for p in pages]
    pages_json = {"chapters": [display_name(s) for s in sources], "pages": rows}
    config = {
        "model": model,
        "dtype": "q8",  # transformers.js name for the quantized model file
        "query_prefix": QUERY_PREFIX,
        "dim": int(matrix.shape[1]),
        "count": len(pages),
        "min_score": min_score,
        "candidates": CANDIDATE_PAGES,
        "max_results": MAX_RESULTS,
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "vectors.bin").write_bytes(matrix.tobytes())
    (out_dir / "pages.json").write_text(
        json.dumps(pages_json, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    (out_dir / "config.json").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
