// Run with:  node --test site/
import assert from "node:assert/strict";
import { test } from "node:test";

import { closestPages, findPages, keywords, mergeNeighbours, pagesText } from "./search.js";

// Four pages in two chapters: [chapter index, page number, title]
const data = {
  chapters: ["Chapter 1", "Chapter 2"],
  pages: [
    [0, 3, "TCP handshake"],
    [0, 4, "TCP handshake: example"],
    [0, 6, "UDP"],
    [1, 7, "TCP flow control"],
  ],
};
// 2-number vectors of length 1; the query is [1, 0], so the score is the first number.
const vectors = new Float32Array([0.9, 0.436, 0.8, 0.6, 0.7, 0.714, 0.85, 0.527]);
const config = { dim: 2, min_score: 0.0, candidates: 10, max_results: 3 };

test("keywords ignores case, short words and very common words", () => {
  assert.deepEqual(
    keywords("How does the TCP 3-way handshake work?"),
    new Set(["tcp", "way", "handshake", "work"]),
  );
  assert.deepEqual(keywords("NAT ทำงานอย่างไร"), new Set(["nat"]));
});

test("closestPages sorts by dot product and respects the limit", () => {
  const hits = closestPages([1, 0], vectors, 2, 2);

  assert.deepEqual(hits.map((h) => h.row), [0, 3]); // scores 0.9 and 0.85
});

test("neighbouring pages of one chapter become one range", () => {
  const hits = [{ row: 1, score: 0.8 }, { row: 0, score: 0.9 }];

  const [range] = mergeNeighbours(hits, data);

  assert.equal(pagesText(range), "3-4");
  assert.equal(range.score, 0.9); // a range is as good as its best page
  assert.deepEqual(range.titles, ["TCP handshake", "TCP handshake: example"]);
});

test("a gap or a different chapter starts a new range", () => {
  const hits = [{ row: 0, score: 0.5 }, { row: 2, score: 0.9 }, { row: 3, score: 0.7 }];

  const ranges = mergeNeighbours(hits, data);

  assert.deepEqual(ranges.map((r) => [r.chapter, pagesText(r)]), [
    ["Chapter 1", "6"],
    ["Chapter 2", "7"],
    ["Chapter 1", "3"],
  ]);
});

test("findPages returns the best range, then ranges whose title shares a query word", () => {
  const results = findPages({ query: "tcp", queryVec: [1, 0], data, vectors, config });

  assert.deepEqual(results.map((r) => [r.chapter, pagesText(r)]), [
    ["Chapter 1", "3-4"], // best
    ["Chapter 2", "7"], // title has "tcp"
  ]); // "UDP" (page 6) is close enough to be a hit but its title has no query word
});

test("pages below min_score are dropped, and nothing close enough means an empty list", () => {
  const strict = { ...config, min_score: 0.95 };

  assert.deepEqual(findPages({ query: "tcp", queryVec: [1, 0], data, vectors, config: strict }), []);
});

test("max_results limits the list", () => {
  const one = { ...config, max_results: 1 };

  assert.equal(findPages({ query: "tcp", queryVec: [1, 0], data, vectors, config: one }).length, 1);
});
