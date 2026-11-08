"""Find the slide pages that cover a topic.

    query -> vector -> closest pages -> merge neighbouring pages into ranges
          -> best range + other ranges whose title mentions a word of the query

Example: the closest pages for "ARP" are 46, 44, 45, 43 and 98 of Chapter 6.
Merged, that is two places to read: p.43-46 and p.98 ("A day in the life... ARP").
site/search.js is the same finder in JavaScript; keep the two in step.
"""

import re
from dataclasses import dataclass

from app.config import CANDIDATE_PAGES, MAX_RESULTS, MIN_SCORE
from app.embed import Embedder
from app.index import Hit, Index

STOPWORDS = {"the", "and", "for", "how", "does", "what", "why", "which", "when", "with", "from"}


@dataclass(frozen=True)
class Result:
    chapter: str  # e.g. "Chapter 3"
    first_page: int
    last_page: int
    titles: list[str]  # distinct slide titles in this range, in page order
    score: float  # similarity of the best page in the range

    @property
    def pages(self) -> str:
        if self.first_page == self.last_page:
            return str(self.first_page)
        return f"{self.first_page}-{self.last_page}"


def find_pages(
    query: str,
    embedder: Embedder,
    index: Index,
    min_score: float = MIN_SCORE,
    max_results: int = MAX_RESULTS,
) -> list[Result]:
    """Best places to read about `query`, best first. Empty list = not in the slides."""
    hits = index.search(embedder.embed_query(query), CANDIDATE_PAGES)
    # Pages below min_score are too far from the query to be about it.
    hits = [h for h in hits if h.score >= min_score]
    ranges = merge_neighbours(hits)
    if not ranges:
        return []

    best, *others = ranges
    # Other ranges are kept only if their title mentions a word of the query. Their scores
    # are too close to unrelated pages to tell them apart, and in the evaluation this rule
    # removed about half of the unrelated lines while keeping almost all useful ones.
    wanted = keywords(query)
    related = [r for r in others if wanted & keywords(" ".join(r.titles))]
    return [best, *related][:max_results]


def keywords(text: str) -> set[str]:
    """Lower-case English words of 3+ letters, minus very common ones ("how", "the", ...).

    Thai words are not matched; a Thai query still gets its best range, and extra ranges
    only through English terms in it (e.g. "NAT" in "NAT ทำงานอย่างไร").
    """
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {w for w in words if len(w) >= 3 and w not in STOPWORDS}


def merge_neighbours(hits: list[Hit]) -> list[Result]:
    """Turn pages that follow each other in the same chapter into one range.

    A range is as good as its best page, so ranges are sorted by their best score.
    """
    groups: list[list[Hit]] = []
    for hit in sorted(hits, key=lambda h: (h.page.chapter, h.page.page)):
        previous = groups[-1][-1].page if groups else None
        if previous and previous.chapter == hit.page.chapter and hit.page.page == previous.page + 1:
            groups[-1].append(hit)
        else:
            groups.append([hit])

    results = [
        Result(
            chapter=group[0].page.chapter,
            first_page=group[0].page.page,
            last_page=group[-1].page.page,
            # dict.fromkeys removes repeated titles but keeps their order
            titles=list(dict.fromkeys(h.page.title for h in group if h.page.title)),
            score=max(h.score for h in group),
        )
        for group in groups
    ]
    return sorted(results, key=lambda r: r.score, reverse=True)
