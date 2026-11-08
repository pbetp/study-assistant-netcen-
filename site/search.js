// The search logic of the app, a line-by-line port of app/search.py.
// It has no browser code in it, so it can be tested with plain Node (search.test.mjs).
//
//   query vector -> closest pages -> drop pages below min_score
//                -> merge neighbouring pages into ranges
//                -> best range + other ranges whose title shares a word with the query

const STOPWORDS = new Set([
  "the", "and", "for", "how", "does", "what", "why", "which", "when", "with", "from",
]);

// Lower-case English words of 3+ letters, minus very common ones ("how", "the", ...).
// Thai words are not matched, same as the Python version.
export function keywords(text) {
  const words = text.toLowerCase().match(/[a-z0-9]+/g) ?? [];
  return new Set(words.filter((w) => w.length >= 3 && !STOPWORDS.has(w)));
}

// The `limit` rows of `vectors` closest to `queryVec`, best first.
// `vectors` holds one page after another (rows of `dim` numbers). All vectors have length 1,
// so similarity is just the dot product.
export function closestPages(queryVec, vectors, dim, limit) {
  const count = vectors.length / dim;
  const scores = new Array(count);
  for (let row = 0; row < count; row++) {
    let sum = 0;
    const start = row * dim;
    for (let i = 0; i < dim; i++) sum += vectors[start + i] * queryVec[i];
    scores[row] = sum;
  }
  return scores
    .map((score, row) => ({ row, score }))
    .sort((a, b) => b.score - a.score)
    .slice(0, limit);
}

// Turn pages that follow each other in the same chapter into one range.
// `data.pages[row]` is [chapter index, page number, title]. A range is as good as its
// best page, so ranges are sorted by their best score.
export function mergeNeighbours(hits, data) {
  const byPosition = [...hits].sort((a, b) => {
    const [chapterA, pageA] = data.pages[a.row];
    const [chapterB, pageB] = data.pages[b.row];
    return chapterA - chapterB || pageA - pageB;
  });

  const groups = [];
  for (const hit of byPosition) {
    const [chapter, page] = data.pages[hit.row];
    const group = groups[groups.length - 1];
    const [lastChapter, lastPage] = group ? data.pages[group[group.length - 1].row] : [];
    if (group && chapter === lastChapter && page === lastPage + 1) group.push(hit);
    else groups.push([hit]);
  }

  const ranges = groups.map((group) => {
    const rows = group.map((hit) => data.pages[hit.row]);
    const titles = rows.map(([, , title]) => title).filter((title) => title);
    return {
      chapter: data.chapters[rows[0][0]],
      firstPage: rows[0][1],
      lastPage: rows[rows.length - 1][1],
      titles: [...new Set(titles)], // repeated titles removed, order kept
      score: Math.max(...group.map((hit) => hit.score)),
    };
  });
  return ranges.sort((a, b) => b.score - a.score);
}

// "43-46" for a range, "98" for a single page.
export function pagesText(range) {
  return range.firstPage === range.lastPage
    ? String(range.firstPage)
    : `${range.firstPage}-${range.lastPage}`;
}

// Best places to read about `query`, best first. An empty list means "not in the slides".
// `config` comes from index/config.json: dim, min_score, candidates, max_results.
export function findPages({ query, queryVec, data, vectors, config }) {
  const hits = closestPages(queryVec, vectors, config.dim, config.candidates).filter(
    (hit) => hit.score >= config.min_score,
  );
  const ranges = mergeNeighbours(hits, data);
  if (ranges.length === 0) return [];

  const [best, ...others] = ranges;
  const wanted = keywords(query);
  const related = others.filter((range) => {
    const words = keywords(range.titles.join(" "));
    return [...wanted].some((word) => words.has(word));
  });
  return [best, ...related].slice(0, config.max_results);
}
