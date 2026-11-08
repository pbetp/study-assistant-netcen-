"""Command line.

python -m app.cli index          read the PDFs, embed every page, save the index (site/index/)
python -m app.cli find udp       where in the slides is this topic?
python -m app.cli find           keep asking (the model is loaded only once)
"""

import argparse
import sys

from app.config import Settings
from app.embed import OnnxEmbedder
from app.index import Index
from app.ingest import load_documents
from app.search import Result, find_pages

MAX_TITLES = 3  # a long range can have many titles; show only the first few


def format_results(results: list[Result]) -> str:
    """The best range first and clearly marked, the others on short lines below it."""
    if not results:
        return "Not found in the slides."
    best, *others = results
    lines = [f"Start reading: {best.chapter}, p.{best.pages}", f"  {titles_text(best)}"]
    if others:
        lines.append("Also related:")
        lines += [f"  {r.chapter}, p.{r.pages:<8} {titles_text(r)}" for r in others]
    return "\n".join(lines)


def titles_text(result: Result) -> str:
    if not result.titles:
        return "(diagram slide, no title)"
    shown = " · ".join(result.titles[:MAX_TITLES])
    return shown + (" · …" if len(result.titles) > MAX_TITLES else "")


def cmd_index(settings: Settings) -> None:
    pages = load_documents(settings.docs_dir)
    if not pages:
        print(f"No PDF pages found in {settings.docs_dir}")
        return
    print(f"{len(pages)} pages found. Embedding (about 15 seconds)...")
    vectors = OnnxEmbedder(settings.embed_model).embed_documents([p.text for p in pages])
    Index(pages, vectors).save(settings.index_dir, settings.embed_model)
    print(f"Saved the index of {len(pages)} pages to {settings.index_dir}")


def cmd_find(settings: Settings, query: str) -> None:
    """One query, or (with no query) keep asking until an empty line.

    Loading the model takes about 10 seconds; each search after that is almost instant,
    so the interactive mode is the comfortable way to use it while studying.
    """
    try:
        index = Index.load(settings.index_dir)
    except FileNotFoundError:
        print(f"No index in {settings.index_dir}. Run first:  python -m app.cli index")
        return
    embedder = OnnxEmbedder(settings.embed_model)
    if query:
        print(format_results(find_pages(query, embedder, index)))
        return

    print("Type a topic or question. Empty line to quit.")
    while True:
        try:
            query = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):  # end of input or Ctrl+C
            break
        if not query:
            break
        print(format_results(find_pages(query, embedder, index)))


def main() -> None:
    # Slides contain symbols (bullets, arrows) that the Windows console cannot print by
    # default; without this, printing a title could crash with UnicodeEncodeError.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(prog="app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("index", help="read the PDFs and build the search index")
    find = sub.add_parser("find", help="find the slide pages about a topic")
    find.add_argument("query", nargs="*", help="topic or question; leave out to keep asking")
    args = parser.parse_args()

    settings = Settings.from_env()
    if args.command == "index":
        cmd_index(settings)
    else:
        cmd_find(settings, " ".join(args.query))


if __name__ == "__main__":
    main()
