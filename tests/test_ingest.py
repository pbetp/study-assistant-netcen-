"""Offline tests for ingest.py. They build tiny PDFs on the fly, so no real slides are needed."""

import pytest

from app.ingest import Page, clean_title, extract_pages, load_documents


def make_pdf(path, pages):
    """Write a minimal valid PDF. `pages` is a list of pages; each page is a list of
    (font size, text) lines, drawn from top to bottom."""
    n_pages = len(pages)
    font_num = 3 + 2 * n_pages
    objects = ["<< /Type /Catalog /Pages 2 0 R >>"]
    kids = " ".join(f"{3 + 2 * i} 0 R" for i in range(n_pages))
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {n_pages} >>")
    for i, lines in enumerate(pages):
        stream, y = "", 180
        for size, text in lines:
            stream += f"BT /F1 {size} Tf 20 {y} Td ({text}) Tj ET\n"
            y -= size + 10
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 400 200] /Contents {4 + 2 * i} 0 R "
            f"/Resources << /Font << /F1 {font_num} 0 R >> >> >>"
        )
        objects.append(f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream")
    objects.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    body = "%PDF-1.4\n"
    offsets = []
    for n, obj in enumerate(objects, start=1):
        offsets.append(len(body))  # byte position where this object starts
        body += f"{n} 0 obj\n{obj}\nendobj\n"
    xref_start = len(body)
    body += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n"
    body += "".join(f"{offset:010d} 00000 n \n" for offset in offsets)
    body += f"trailer\n<< /Root 1 0 R /Size {len(objects) + 1} >>\n"
    body += f"startxref\n{xref_start}\n%%EOF\n"
    path.write_bytes(body.encode("latin-1"))


BODY = (12, "body text with enough words to count as a real slide")


def test_title_is_the_text_in_the_largest_font(tmp_path):
    pdf = tmp_path / "a.pdf"
    make_pdf(pdf, [[(10, "label in a diagram"), (24, "Real Title"), BODY]])

    [page] = extract_pages(pdf)

    assert page.title == "Real Title"
    assert "body text" in page.text and "label in a diagram" in page.text


def test_page_numbers_are_one_based_and_survive_skipped_pages(tmp_path):
    pdf = tmp_path / "a.pdf"
    make_pdf(pdf, [[(24, "First"), BODY], [], [(24, "Third"), BODY]])

    pages = extract_pages(pdf)

    # The empty page is dropped, but page numbers still match the real PDF.
    assert [(p.page, p.title) for p in pages] == [(1, "First"), (3, "Third")]


def test_divider_pages_with_almost_no_text_are_skipped(tmp_path):
    pdf = tmp_path / "a.pdf"
    make_pdf(pdf, [[(24, "Additional Chapter 5 slides")], [(24, "Real"), BODY]])

    assert [p.page for p in extract_pages(pdf)] == [2]


def test_diagram_slide_without_big_title_gets_no_title(tmp_path):
    pdf = tmp_path / "a.pdf"
    titled = [(24, "Some Title"), BODY]
    diagram = [(10, "box"), (10, "arrow from the sender box to the receiver box")]
    make_pdf(pdf, [titled, titled, diagram, titled])

    pages = extract_pages(pdf)

    assert [p.title for p in pages] == ["Some Title", "Some Title", "", "Some Title"]


def test_clean_title_fixes_spaced_hyphens_and_whitespace():
    assert clean_title("Go - Back - N:\n  sender") == "Go-Back-N: sender"


def test_load_documents_reads_all_pdfs_sorted(tmp_path):
    make_pdf(tmp_path / "b.pdf", [[(24, "from b"), BODY]])
    make_pdf(tmp_path / "a.pdf", [[(24, "from a"), BODY]])
    (tmp_path / "notes.txt").write_text("not a pdf")

    pages = load_documents(tmp_path)

    assert [(p.source, p.title) for p in pages] == [("a.pdf", "from a"), ("b.pdf", "from b")]


def test_load_documents_missing_folder_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_documents(tmp_path / "does-not-exist")


def test_page_id_is_stable_and_unique():
    a = Page("a.pdf", 1, "t", "x")
    assert a.id == "a.pdf|1"
    assert a.id != Page("a.pdf", 2, "t", "x").id
