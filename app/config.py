"""Settings and tuning values, in one place (no secrets in code).

Settings come from environment variables and every one has a default, so the project runs
with zero setup. To override one in PowerShell:  $env:DOCS_DIR = "data_other"
"""

import os
from dataclasses import dataclass
from pathlib import Path

# How the finder is tuned. Each value was measured on the evaluation queries (see README).
# They are also written into the index (config.json), so the web page searches with the
# same numbers. Scores depend on the model: re-measure them if you change EMBED_MODEL.
MIN_SCORE = 0.82  # a page less similar than this is "not about the query"
CANDIDATE_PAGES = 15  # how many close pages to look at before merging them into ranges
MAX_RESULTS = 3  # the best range ("start reading here") + up to 2 more


@dataclass(frozen=True)
class Settings:
    docs_dir: Path  # folder with the PDFs; change it to index another course
    index_dir: Path  # where the index is saved (and where the web page reads it)
    embed_model: str  # Hugging Face repo with the ONNX model files

    @classmethod
    def from_env(cls) -> "Settings":
        env = os.environ.get
        return cls(
            docs_dir=Path(env("DOCS_DIR", "data")),
            index_dir=Path(env("INDEX_DIR", "site/index")),
            embed_model=env("EMBED_MODEL", "Xenova/multilingual-e5-small"),
        )
