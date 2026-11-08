"""REST API.

GET /            ->  a one-page search form (static/index.html) for use in a browser
GET /find?q=udp  ->  {"query": "udp", "results": [{"chapter", "file", "pages", "first_page",
                                                     "last_page", "titles"}, ...]}
GET /health      ->  {"status": "ok", "pages": <number indexed>}

Thin layer only: the real logic lives in search.py so it is easy to test.
Run:  uvicorn app.api:create_default_app --factory
"""

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.config import Settings
from app.embed import Embedder, SentenceTransformerEmbedder
from app.search import find_pages
from app.store import VectorStore

STATIC_DIR = Path(__file__).parent / "static"


class ResultOut(BaseModel):
    chapter: str
    file: str
    pages: str  # "43-46" or "98"
    first_page: int
    last_page: int
    titles: list[str]


class FindResponse(BaseModel):
    query: str
    results: list[ResultOut]  # best first; empty = not found in the slides


def create_app(embedder: Embedder, store: VectorStore, min_score: float = 0.0) -> FastAPI:
    """Build the app from its parts. Tests pass fakes here; production passes real ones."""
    app = FastAPI(title="Netcentric Slide Finder")

    @app.get("/", include_in_schema=False)
    def home() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "pages": store.count()}

    @app.get("/find", response_model=FindResponse)
    def find(q: str = Query(description="topic or question")) -> FindResponse:
        query = q.strip()
        if not query:
            raise HTTPException(status_code=422, detail="q must not be empty")
        if store.count() == 0:
            raise HTTPException(
                status_code=503, detail="Index is empty. Run: python -m app.cli index"
            )
        results = find_pages(query, embedder, store, min_score)
        return FindResponse(
            query=query,
            results=[
                ResultOut(
                    chapter=r.chapter,
                    file=r.source,
                    pages=r.pages,
                    first_page=r.first_page,
                    last_page=r.last_page,
                    titles=r.titles,
                )
                for r in results
            ],
        )

    return app


def create_default_app() -> FastAPI:
    """Production wiring from environment variables (loads the real embedding model)."""
    settings = Settings.from_env()
    return create_app(
        embedder=SentenceTransformerEmbedder(settings.embed_model),
        store=VectorStore(settings.store_dir),
        min_score=settings.min_score,
    )
