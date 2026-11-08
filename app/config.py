"""All settings in one place, read from environment variables (no secrets in code).

Every field has a default, so the project runs with zero setup.
Set an environment variable to override, e.g. in PowerShell:  $env:DOCS_DIR = "data_other"
"""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    docs_dir: Path  # folder with PDFs; change it to index another course
    store_dir: Path  # where the vector store is saved
    embed_model: str  # sentence-transformers model name
    min_score: float  # below this similarity a page is "not about the query"

    @classmethod
    def from_env(cls) -> "Settings":
        env = os.environ.get
        return cls(
            docs_dir=Path(env("DOCS_DIR", "data")),
            store_dir=Path(env("VECTOR_STORE_DIR", "chroma_db")),
            embed_model=env("EMBED_MODEL", "intfloat/multilingual-e5-small"),
            # 0.81 was measured for multilingual-e5-small on these slides (see README).
            # Scores are NOT comparable between models: re-measure if you change EMBED_MODEL.
            min_score=float(env("MIN_SCORE", "0.81")),
        )
