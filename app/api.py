"""REST API.

GET /find?q=udp  ->  {"query": "udp", "results": [{"chapter", "pages", "first_page",
                                                     "last_page", "titles"}, ...]}
GET /health      ->  {"status": "ok", "pages": <number of pages in the index>}

Thin layer only: the real logic lives in search.py so it is easy to test.
The web page for phones is separate and needs no server: see site/.
Run:  uvicorn app.api:create_default_app --factory
"""

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from app.config import MIN_SCORE, Settings
from app.embed import Embedder, OnnxEmbedder
from app.index import Index
from app.search import find_pages


class ResultOut(BaseModel):
    chapter: str
    pages: str  # "43-46" or "98"
    first_page: int
    last_page: int
    titles: list[str]


class FindResponse(BaseModel):
    query: str
    results: list[ResultOut]  # best first; empty = not found in the slides


def create_app(embedder: Embedder, index: Index, min_score: float = MIN_SCORE) -> FastAPI:
    """Build the app from its parts. Tests pass fakes here; production passes real ones."""
    app = FastAPI(title="Netcentric Slide Finder")

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "pages": len(index.pages)}

    @app.get("/find", response_model=FindResponse)
    def find(q: str = Query(description="topic or question")) -> FindResponse:
        query = q.strip()
        if not query:
            raise HTTPException(status_code=422, detail="q must not be empty")
        results = find_pages(query, embedder, index, min_score)
        return FindResponse(
            query=query,
            results=[
                ResultOut(
                    chapter=r.chapter,
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
    return create_app(OnnxEmbedder(settings.embed_model), Index.load(settings.index_dir))
