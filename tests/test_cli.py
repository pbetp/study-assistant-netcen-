from app.cli import format_results
from app.search import Result

UDP = Result(
    "Chapter_3_(pdf)-1-2.pdf", 24, 30, ["UDP: User Datagram Protocol", "UDP checksum"], 0.9
)
QUIC = Result("Chapter_3_(pdf)-1-2.pdf", 137, 137, ["QUIC"], 0.8)


def test_not_found_message():
    assert format_results([]) == "Not found in the slides."


def test_best_result_is_marked_and_others_listed_below():
    text = format_results([UDP, QUIC])

    assert text.splitlines()[0] == "Start reading: Chapter 3, p.24-30"
    assert "UDP: User Datagram Protocol · UDP checksum" in text
    assert "Also related:" in text and "Chapter 3, p.137" in text


def test_single_result_has_no_also_section():
    assert "Also related" not in format_results([UDP])


def test_slide_without_title_and_long_title_lists():
    no_title = Result("a.pdf", 11, 15, [], 0.9)
    many = Result("a.pdf", 20, 40, ["A", "B", "C", "D"], 0.9)

    assert "(diagram slide, no title)" in format_results([no_title])
    assert "A · B · C · …" in format_results([many])
