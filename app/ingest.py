"""Read PDF slides: one `Page` per slide, with its chapter, page number and title.

The whole page is the search unit. Slides are short (about 450 characters on average),
so splitting them into smaller chunks did not improve search (see README), and keeping
whole pages means every result points at exactly one slide page.
"""

import re
import statistics
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

# Pages with fewer words are dividers ("Additional Chapter 5 slides") or empty animation
# frames. They have nothing to read, and because they are almost empty they matched
# random queries such as "pizza". Real slides in this course have at least 9 words.
MIN_WORDS = 8


@dataclass(frozen=True)
class Page:
    chapter: str  # short name of the PDF, e.g. "Chapter 3"
    page: int  # 1-based, same number you see in the PDF viewer
    title: str  # slide title, "" for a diagram-only slide with no clear title
    text: str  # only used to build the index; it is never saved in it


def chapter_name(file_name: str) -> str:
    """Short name shown to the user: 'Chapter_3_(pdf)-1045785-17255919550481.pdf' -> 'Chapter 3'.

    The course website adds '_(pdf)-<numbers>' to every download; other names are kept as they are.
    """
    stem = Path(file_name).stem
    short = re.split(r"[_\s-]*\(pdf\)", stem)[0].replace("_", " ").strip()
    return short or stem


def read_page(pdf_page) -> tuple[str, str, float]:
    """Return (text, title, title font size) of one PDF page.

    The title is the text written in the largest font. The first line is not reliable:
    on many slides it is a label inside a diagram.
    """
    pieces = []  # (font size, text) for every piece of text pypdf finds

    def visit(text, cm, tm, font_dict, font_size):
        if text.strip():
            # Size on screen = font size x vertical scale of the text matrix (tm)
            # x vertical scale of the page matrix (cm).
            pieces.append((font_size * abs(tm[3]) * abs(cm[3]), text))

    text = (pdf_page.extract_text(visitor_text=visit) or "").strip()
    if not pieces:
        return text, "", 0.0
    biggest = max(size for size, _ in pieces)
    title = " ".join(piece for size, piece in pieces if size >= biggest - 0.5)
    return text, clean_title(title), biggest


def clean_title(raw: str) -> str:
    title = " ".join(raw.split())  # collapse newlines and repeated spaces
    return re.sub(r"\s*-\s*", "-", title)  # "Go - Back - N" -> "Go-Back-N"


def extract_pages(pdf_path: Path) -> list[Page]:
    """Extract every page that has real content, with its title."""
    rows = []
    for number, pdf_page in enumerate(PdfReader(pdf_path).pages, start=1):
        text, title, size = read_page(pdf_page)
        if len(text.split()) >= MIN_WORDS:  # skip empty, image-only and divider pages
            rows.append((number, text, title, size))

    # A diagram-only slide has no big title: its largest text is much smaller than the
    # usual title size of this deck. Showing that text as a title would be misleading.
    usual_title_size = statistics.median(size for *_, size in rows) if rows else 0.0
    return [
        Page(
            chapter=chapter_name(pdf_path.name),
            page=number,
            title=title if size >= 0.75 * usual_title_size else "",
            text=text,
        )
        for number, text, title, size in rows
    ]


def load_documents(docs_dir: Path) -> list[Page]:
    """Extract pages from every PDF in docs_dir (sorted, so results are repeatable)."""
    if not docs_dir.is_dir():
        raise FileNotFoundError(f"Documents folder not found: {docs_dir}")

    pages = []
    files = {}  # short chapter name -> the PDF it came from
    for pdf_path in sorted(docs_dir.glob("*.pdf")):
        name = chapter_name(pdf_path.name)
        # Pages are told apart by chapter name and page number, so two PDFs must not share a name.
        if files.setdefault(name, pdf_path.name) != pdf_path.name:
            raise ValueError(f"{files[name]} and {pdf_path.name} would both be called '{name}'")
        pages.extend(extract_pages(pdf_path))
    return pages
