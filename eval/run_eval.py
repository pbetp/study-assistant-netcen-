"""Measure how often the finder points at the right slides.

questions.json has three kinds of queries, each with the chapter and the pages that answer it:
- "topic":     short, like what you would type ("udp", "slow start", "ที่อยู่ MAC")
- "question":  a full sentence
- "off-topic": not in the slides; correct only if the finder returns nothing

A query is a hit at k if one of the first k results (page ranges) contains an expected page.
The finder shows 3 results, so hit@3 = "the right page is on the screen".

Uses the index built by `python -m app.cli index`.
Run:  python -m eval.run_eval  [--out eval/results.md]
"""

import argparse
import json
import sys
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path

from app.config import MIN_SCORE, Settings
from app.embed import OnnxEmbedder
from app.index import Index
from app.search import Result, find_pages

QUESTIONS_FILE = Path(__file__).parent / "questions.json"
KS = (1, 3)
KINDS = ("topic", "question", "off-topic")


def load_questions(path: Path = QUESTIONS_FILE) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def is_hit(question: dict, results: list[Result]) -> bool:
    if not question["pages"]:  # off-topic: the right answer is "not found"
        return not results
    return any(
        r.chapter == question["chapter"] and r.first_page <= page <= r.last_page
        for r in results
        for page in question["pages"]
    )


def evaluate(
    questions: list[dict], find: Callable[[str], list[Result]]
) -> dict[str, tuple[int, dict[int, float]]]:
    """Return {kind: (number of queries, {k: hit rate})}, plus an "all" row."""
    rows = defaultdict(list)  # kind -> [(question, results)]
    for q in questions:
        results = find(q["question"])
        rows[q["kind"]].append((q, results))
        rows["all"].append((q, results))
    return {
        kind: (len(pairs), {k: sum(is_hit(q, r[:k]) for q, r in pairs) / len(pairs) for k in KS})
        for kind, pairs in rows.items()
    }


def format_table(scores: dict[str, tuple[int, dict[int, float]]]) -> str:
    lines = ["| queries | n | " + " | ".join(f"hit@{k}" for k in KS) + " |"]
    lines.append("|---|---|" + "---|" * len(KS))
    for kind in [*KINDS, "all"]:
        if kind in scores:
            n, rates = scores[kind]
            lines.append(f"| {kind} | {n} | " + " | ".join(f"{rates[k]:.0%}" for k in KS) + " |")
    return "\n".join(lines)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, help="also write the table to this file")
    args = parser.parse_args()

    settings = Settings.from_env()
    embedder = OnnxEmbedder(settings.embed_model)
    index = Index.load(settings.index_dir)

    def find(query: str) -> list[Result]:
        return find_pages(query, embedder, index)

    table = format_table(evaluate(load_questions(), find))
    header = f"Model {settings.embed_model}, MIN_SCORE {MIN_SCORE}\n\n"
    print(header + table)
    if args.out:
        args.out.write_text(header + table + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
