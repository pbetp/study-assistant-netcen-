"""Command line.

python -m app.cli index          read the PDFs, embed every page, save to the store
python -m app.cli find udp       where in the slides is this topic?
python -m app.cli find           keep asking (the model is loaded only once)
python -m app.cli export-site    write the files the browser version needs (site/index/)
"""

import argparse
import sys
from pathlib import Path

from app.config import Settings
from app.embed import OnnxEmbedder
from app.export_site import export_site_index
from app.ingest import load_documents
from app.search import Result, find_pages
from app.store import VectorStore

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
    print(f"{len(pages)} pages found. Embedding (about a minute)...")
    embedder = OnnxEmbedder(settings.embed_model)
    vectors = embedder.embed_documents([p.text for p in pages])
    store = VectorStore(settings.store_dir)
    store.clear()  # full re-index: remove old pages first
    store.add(pages, vectors)
    print(f"Saved {store.count()} pages to {settings.store_dir}")


def cmd_export_site(settings: Settings, out_dir: Path) -> None:
    pages = load_documents(settings.docs_dir)
    print(f"{len(pages)} pages found. Embedding...")
    vectors = OnnxEmbedder(settings.embed_model).embed_documents([p.text for p in pages])
    export_site_index(pages, vectors, out_dir, settings.embed_model, settings.min_score)
    print(f"Wrote vectors.bin, pages.json and config.json to {out_dir}")


def cmd_find(settings: Settings, query: str) -> None:
    """One query, or (with no query) keep asking until an empty line.

    Loading the model takes about 10 seconds; each search after that is almost instant,
    so the interactive mode is the comfortable way to use it while studying.
    """
    embedder = OnnxEmbedder(settings.embed_model)
    store = VectorStore(settings.store_dir)
    if store.count() == 0:
        print("The index is empty. Run first:  python -m app.cli index")
        return
    if query:
        print(format_results(find_pages(query, embedder, store, settings.min_score)))
        return

    print("Type a topic or question. Empty line to quit.")
    while True:
        try:
            query = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):  # end of input or Ctrl+C
            break
        if not query:
            break
        print(format_results(find_pages(query, embedder, store, settings.min_score)))


def main() -> None:
    # Slides contain symbols (bullets, arrows) that the Windows console cannot print by
    # default; without this, printing a title could crash with UnicodeEncodeError.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(prog="app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("index", help="read the PDFs and build the search index")
    find = sub.add_parser("find", help="find the slide pages about a topic")
    find.add_argument("query", nargs="*", help="topic or question; leave out to keep asking")
    export = sub.add_parser("export-site", help="write the data files for the browser version")
    export.add_argument("--out", type=Path, default=Path("site/index"))
    args = parser.parse_args()

    settings = Settings.from_env()
    if args.command == "index":
        cmd_index(settings)
    elif args.command == "export-site":
        cmd_export_site(settings, args.out)
    else:
        cmd_find(settings, " ".join(args.query))


if __name__ == "__main__":
    main()
