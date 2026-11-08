"""Find the slide pages that cover a topic.

    query -> vector -> closest pages -> merge neighbouring pages into ranges
          -> best range + other ranges whose title mentions a word of the query

Example: the closest pages for "ARP" are 46, 44, 45, 43 and 98 of Chapter 6.
Merged, that is two places to read: p.43-46 and p.98 ("A day in the life... ARP").
"""

import re
from dataclasses import dataclass
from pathlib import Path

from app.embed import Embedder
from app.store import Hit, VectorStore

CANDIDATE_PAGES = 15  # how many close pages to look at before merging them into ranges
MAX_RESULTS = 3  # the best range ("start reading here") + up to 2 more
STOPWORDS = {"the", "and", "for", "how", "does", "what", "why", "which", "when", "with", "from"}


@dataclass(frozen=True)
class Result:
    source: str  # PDF file name
    first_page: int
    last_page: int
    titles: list[str]  # distinct slide titles in this range, in page order
    score: float  # similarity of the best page in the range

    @property
    def chapter(self) -> str:
        return display_name(self.source)

    @property
    def pages(self) -> str:
        if self.first_page == self.last_page:
            return str(self.first_page)
        return f"{self.first_page}-{self.last_page}"


def find_pages(
    query: str,
    embedder: Embedder,
    store: VectorStore,
    min_score: float = 0.0,
    max_results: int = MAX_RESULTS,
) -> list[Result]:
    """Best places to read about `query`, best first. Empty list = not in the slides."""
    hits = store.search(embedder.embed_query(query), CANDIDATE_PAGES)
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
    """Turn pages that follow each other in the same file into one range.

    A range is as good as its best page, so ranges are sorted by their best score.
    """
    groups: list[list[Hit]] = []
    for hit in sorted(hits, key=lambda h: (h.page.source, h.page.page)):
        previous = groups[-1][-1].page if groups else None
        if previous and previous.source == hit.page.source and hit.page.page == previous.page + 1:
            groups[-1].append(hit)
        else:
            groups.append([hit])

    results = [
        Result(
            source=group[0].page.source,
            first_page=group[0].page.page,
            last_page=group[-1].page.page,
            # dict.fromkeys removes repeated titles but keeps their order
            titles=list(dict.fromkeys(h.page.title for h in group if h.page.title)),
            score=max(h.score for h in group),
        )
        for group in groups
    ]
    return sorted(results, key=lambda r: r.score, reverse=True)


def display_name(source: str) -> str:
    """Short name for a file: 'Chapter_3_(pdf)-1045785-17255919550481.pdf' -> 'Chapter 3'.

    The course website adds '_(pdf)-<numbers>' to every download; other names are kept.
    """
    stem = Path(source).stem
    short = re.split(r"[_\s-]*\(pdf\)", stem)[0].replace("_", " ").strip()
    return short or stem
