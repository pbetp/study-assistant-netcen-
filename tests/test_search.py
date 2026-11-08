from app.ingest import Page
from app.search import Result, display_name, find_pages, keywords, merge_neighbours
from app.store import Hit


def hit(source, page, score, title="t"):
    return Hit(page=Page(source, page, title, "text"), score=score)


def test_neighbouring_pages_become_one_range():
    results = merge_neighbours([hit("a.pdf", 5, 0.7), hit("a.pdf", 3, 0.9), hit("a.pdf", 4, 0.8)])

    assert [(r.first_page, r.last_page) for r in results] == [(3, 5)]
    assert results[0].score == 0.9  # a range is as good as its best page


def test_gaps_and_different_files_are_not_merged():
    results = merge_neighbours([hit("a.pdf", 3, 0.9), hit("a.pdf", 5, 0.8), hit("b.pdf", 4, 0.7)])

    assert [(r.source, r.pages) for r in results] == [
        ("a.pdf", "3"),
        ("a.pdf", "5"),
        ("b.pdf", "4"),
    ]


def test_ranges_are_sorted_by_best_score():
    results = merge_neighbours([hit("a.pdf", 1, 0.5), hit("a.pdf", 9, 0.9), hit("a.pdf", 10, 0.6)])

    assert [r.pages for r in results] == ["9-10", "1"]


def test_titles_are_deduplicated_in_page_order_and_empty_ones_skipped():
    hits = [hit("a.pdf", 1, 0.9, "ARP"), hit("a.pdf", 2, 0.8, ""), hit("a.pdf", 3, 0.7, "ARP")]

    assert merge_neighbours(hits)[0].titles == ["ARP"]


def test_find_pages_puts_the_matching_range_first(embedder, store):
    results = find_pages("tcp handshake", embedder, store)

    best = results[0]
    assert (best.source, best.pages) == ("net.pdf", "3-4")
    assert best.titles == ["TCP handshake", "TCP handshake: example"]


def test_find_pages_respects_max_results(embedder, store):
    assert len(find_pages("tcp dns http", embedder, store, max_results=2)) == 2


def test_other_ranges_need_a_query_word_in_their_title(embedder, store):
    # "dns" matches only the DNS page; the TCP/HTTP pages and the untitled diagram
    # are close enough to be returned by the store, but their titles do not say "dns".
    results = find_pages("dns", embedder, store)

    assert [(r.source, r.pages) for r in results] == [("net.pdf", "12")]


def test_keywords_ignore_case_short_and_common_words():
    assert keywords("How does the TCP 3-way handshake work?") == {"tcp", "way", "handshake", "work"}
    assert keywords("NAT ทำงานอย่างไร") == {"nat"}


def test_nothing_close_enough_means_empty_list(embedder, store):
    assert find_pages("tcp handshake", embedder, store, min_score=1.1) == []


def test_display_name_shortens_course_downloads():
    assert display_name("Chapter_3_(pdf)-1045785-17255919550481.pdf") == "Chapter 3"
    assert display_name("Lecture 01.pdf") == "Lecture 01"


def test_pages_text_for_single_page_and_range():
    assert Result("a.pdf", 7, 7, [], 0.9).pages == "7"
    assert Result("a.pdf", 43, 46, [], 0.9).pages == "43-46"
