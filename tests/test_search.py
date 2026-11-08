import pytest

from app.index import Hit
from app.ingest import Page
from app.search import Result, find_pages, keywords, merge_neighbours


def hit(chapter, page, score, title="t"):
    return Hit(page=Page(chapter, page, title, "text"), score=score)


def test_neighbouring_pages_become_one_range():
    results = merge_neighbours([hit("A", 5, 0.7), hit("A", 3, 0.9), hit("A", 4, 0.8)])

    assert [(r.first_page, r.last_page) for r in results] == [(3, 5)]
    assert results[0].score == 0.9  # a range is as good as its best page


def test_gaps_and_different_chapters_are_not_merged():
    results = merge_neighbours([hit("A", 3, 0.9), hit("A", 5, 0.8), hit("B", 4, 0.7)])

    assert [(r.chapter, r.pages) for r in results] == [("A", "3"), ("A", "5"), ("B", "4")]


def test_ranges_are_sorted_by_best_score():
    results = merge_neighbours([hit("A", 1, 0.5), hit("A", 9, 0.9), hit("A", 10, 0.6)])

    assert [r.pages for r in results] == ["9-10", "1"]


def test_titles_are_deduplicated_in_page_order_and_empty_ones_skipped():
    hits = [hit("A", 1, 0.9, "ARP"), hit("A", 2, 0.8, ""), hit("A", 3, 0.7, "ARP")]

    assert merge_neighbours(hits)[0].titles == ["ARP"]


# The fake embedder gives low scores, so these tests turn the minimum score off (0.0).


def test_find_pages_puts_the_matching_range_first(embedder, index):
    results = find_pages("tcp handshake", embedder, index, min_score=0.0)

    best = results[0]
    assert (best.chapter, best.pages) == ("Chapter 1", "3-4")
    assert best.titles == ["TCP handshake", "TCP handshake: example"]


def test_find_pages_respects_max_results(embedder, index):
    results = find_pages("tcp dns http", embedder, index, min_score=0.0, max_results=2)

    assert len(results) == 2


def test_other_ranges_need_a_query_word_in_their_title(embedder, index):
    # "dns" matches only the DNS page; the TCP/HTTP pages and the untitled diagram
    # are close enough to be returned by the index, but their titles do not say "dns".
    results = find_pages("dns", embedder, index, min_score=0.0)

    assert [(r.chapter, r.pages) for r in results] == [("Chapter 1", "12")]


def test_keywords_ignore_case_short_and_common_words():
    assert keywords("How does the TCP 3-way handshake work?") == {"tcp", "way", "handshake", "work"}
    assert keywords("NAT ทำงานอย่างไร") == {"nat"}


def test_nothing_close_enough_means_empty_list(embedder, index):
    assert find_pages("tcp handshake", embedder, index, min_score=1.1) == []


def test_the_default_minimum_score_is_the_measured_one(embedder, index):
    # The fake embedder never reaches 0.82, so with the default nothing is "close enough".
    assert find_pages("tcp handshake", embedder, index) == []


@pytest.mark.parametrize(("first", "last", "text"), [(7, 7, "7"), (43, 46, "43-46")])
def test_pages_text_for_single_page_and_range(first, last, text):
    assert Result("Chapter 1", first, last, [], 0.9).pages == text
