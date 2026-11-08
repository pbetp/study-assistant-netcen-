from app.search import Result
from eval.run_eval import evaluate, format_table, is_hit, load_questions

QUESTION = {"kind": "topic", "question": "q", "source": "Chapter_2", "pages": [21, 25]}
OFF_TOPIC = {"kind": "off-topic", "question": "pizza", "source": "", "pages": []}


def result(source, first, last):
    return Result(source, first, last, [], 0.9)


def test_hit_when_an_expected_page_is_inside_a_range():
    assert is_hit(QUESTION, [result("Chapter_2_(pdf).pdf", 24, 26)])  # 25 is inside 24-26
    assert not is_hit(QUESTION, [result("Chapter_3_(pdf).pdf", 25, 25)])  # right page, wrong file
    assert not is_hit(QUESTION, [result("Chapter_2_(pdf).pdf", 26, 30)])  # right file, wrong pages


def test_off_topic_is_correct_only_when_nothing_is_found():
    assert is_hit(OFF_TOPIC, [])
    assert not is_hit(OFF_TOPIC, [result("Chapter_1.pdf", 1, 1)])


def test_evaluate_counts_hits_per_kind_and_k():
    answers = {
        "q": [result("Chapter_2.pdf", 99, 99), result("Chapter_2.pdf", 21, 21)],  # hit at rank 2
        "pizza": [],
    }

    scores = evaluate([QUESTION, OFF_TOPIC], lambda query: answers[query])

    assert scores["topic"] == (1, {1: 0.0, 3: 1.0})
    assert scores["off-topic"] == (1, {1: 1.0, 3: 1.0})
    assert scores["all"] == (2, {1: 0.5, 3: 1.0})


def test_format_table_has_one_row_per_kind():
    table = format_table({"topic": (35, {1: 0.9, 3: 1.0}), "all": (35, {1: 0.9, 3: 1.0})})
    assert "| topic | 35 | 90% | 100% |" in table


def test_shipped_questions_are_well_formed():
    questions = load_questions()
    assert {q["kind"] for q in questions} == {"topic", "question", "off-topic"}
    for q in questions:
        assert q["question"].strip()
        if q["kind"] == "off-topic":
            assert q["pages"] == []
        else:
            assert q["source"].startswith("Chapter_")
            assert q["pages"] and all(isinstance(p, int) and p >= 1 for p in q["pages"])
