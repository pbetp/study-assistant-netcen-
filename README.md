# netcentric-study-assistant

Find **where** a topic is in your course slides. Type a topic or a question, in English or
Thai, and get the chapter and page range to start reading. It runs entirely in the browser
(no server, no API key) and also as a command line and a small REST API.

**Live demo: https://pbetp.github.io/study-assistant-netcen-/** (the first visit downloads a
search model of about 135 MB; the page shows only slide titles and page numbers).

```
> udp
Start reading: Chapter 3, p.24-29
  UDP: User Datagram Protocol · UDP: Transport Layer Actions
Also related:
  Chapter 3, p.137      QUIC: Quick UDP Internet Connections

> NAT ทำงานอย่างไร
Start reading: Chapter 4, p.64-68
  NAT: network address translation

> pizza
Not found in the slides.
```

> **Course slides are copyrighted and are not in this repository.** Put your own PDFs in
> `data/` (git-ignored). The index (`site/index/`) contains **only slide titles, page numbers
> and vectors**, never slide text.

## Use it

**Web page (phone or computer).** Open the [live demo](https://pbetp.github.io/study-assistant-netcen-/)
(hosted free on GitHub Pages; to publish your own copy see below). The first visit downloads
the search model (about 135 MB); the browser keeps it, so later visits are fast. Links like
`...?q=udp` search straight away.

**Command line (Windows, PowerShell):**

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt

# 1. put your PDFs in data\  (another course: $env:DOCS_DIR = "other_folder")
# 2. build the index once (the first run downloads the model into .cache\)
.\.venv\Scripts\python.exe -m app.cli index

# 3. search
.\ask udp                  # one search
.\ask                      # keep asking: the model loads once, then every search is instant
```

**REST API:** `.\.venv\Scripts\python.exe -m uvicorn app.api:create_default_app --factory`, then
`GET http://127.0.0.1:8000/find?q=udp` (docs at `/docs`).

Settings are environment variables with defaults (see `app/config.py` and `.env.example`):
`DOCS_DIR`, `INDEX_DIR`, `EMBED_MODEL`.

## Publish the web page (free, permanent, no card)

The page is plain files in `site/`, so GitHub Pages can host it.

1. Build the index from your slides, then commit it (`app.cli index` writes `site\index\`):
   ```powershell
   git add site\index; git commit -m "Update slide index"; git push
   ```
2. In the repository: **Settings -> Pages -> Source: GitHub Actions**. The workflow
   `.github/workflows/pages.yml` publishes `site/` on every push that changes it.

Anyone with the link can open the page and see the slide titles. If the slides are not yours to
share, keep the repository and the page private or do not publish `site/index/`.

## How it works

```
index (once, on your PC)
  PDF ──▶ one Page per slide ──▶ vector ──▶ site/index/  vectors.bin  pages.json  config.json
          chapter, number, title  (ONNX model)            └──── read by Python AND by the web page

search (the same steps in Python and in the browser)
  query ──▶ vector ──▶ compare with every page vector ──▶ 15 closest pages
        ──▶ drop pages below MIN_SCORE
        ──▶ merge neighbouring pages into ranges  (p.43, 44, 45, 46 → p.43-46)
        ──▶ best range + other ranges whose title shares a word with the query
```

| file | job |
|---|---|
| `app/ingest.py` | read PDFs: chapter, page number, title and text of every slide |
| `app/embed.py` | text → vector with the quantized ONNX model (and a fake one for tests) |
| `app/index.py` | the index: save it to / load it from 3 files, search it |
| `app/search.py` | the finder: closest pages → ranges → results |
| `app/config.py` | settings from environment variables, and the tuned search values |
| `app/cli.py`, `app/api.py` | command line and REST API |
| `site/search.js` | the same finder in JavaScript (a port of `search.py`) |
| `site/app.js`, `site/index.html` | the page: loads the index and the model, shows results |

Each design choice was measured, not guessed:

- **No vector database.** There are only 625 vectors (1 MB). Comparing the query with all of
  them and sorting takes 0.03 ms (measured; 100,000 vectors would still take 8 ms), so the
  index is a plain matrix saved in a file. A vector database such as Chroma would matter at
  hundreds of thousands of vectors. An earlier version used Chroma; removing it dropped 52
  packages (217 MB) and let Python and the web page share one index.
- **Whole pages, not chunks.** Slides are short (about 450 characters). An earlier version
  split them into chunks of 250-2000 characters; smaller chunks never helped, so a page is the
  unit and every result is a page.
- **Titles from the largest font.** The first line of a slide is often a label inside a
  diagram. The largest text gave a sensible title on 620 of 625 pages (checked by reading the
  full list); the other 5 are diagram-only slides ("(diagram slide, no title)").
- **Neighbouring pages merged into ranges.** A topic usually spans several slides, and one
  range is one place to read.
- **Pages with fewer than 8 words are skipped.** Dividers such as "Additional Chapter 5 slides"
  are almost empty, so they matched random queries like "pizza".
- **"Also related" only if the title shares a word with the query.** Without this rule most
  extra lines were unrelated pages with almost the same score.
- **One model for Python and the browser.** The quantized ONNX version of
  multilingual-e5-small (118 MB) searches as well as the full PyTorch one (same hit rates)
  and runs in a browser through transformers.js. Using it everywhere also removed PyTorch
  from the project.
- **The JavaScript finder is checked against the Python one.** On all 65 evaluation queries,
  the same query vectors give identical results in both (65 of 65), and `node --test` runs
  unit tests of `search.js` in CI.
- **No LLM.** An earlier version wrote answers with a local LLM. For the real use, "where do I
  start reading?", a page list is faster and cannot invent content.

## Evaluation

`eval/questions.json` has 65 queries, each with the chapter and page(s) that answer it:
35 short **topics** (what you would type, including 5 in Thai), 20 full **questions**, and
10 **off-topic** queries that are correct only if the finder says "not found".
A query is a *hit at k* if an expected page is inside one of the first k results; the finder
shows up to 3, so hit@3 means "the right page is on the screen".

Python (`python -m eval.run_eval --out eval/results.md`, uses the index you built):

| queries | n | hit@1 | hit@3 |
|---|---|---|---|
| topic | 35 | 89% | 94% |
| question | 20 | 70% | 75% |
| off-topic | 10 | 70% | 70% |
| all | 65 | 80% | 85% |

The same 65 queries through the real web page (desktop Chrome, driven by a script): **identical
results, 80% hit@1 / 85% hit@3 overall**, topics 89% / 94%, questions 70% / 75%, off-topic 70% / 70%.

How to read it:
- **Type the key term.** Short topics are the most reliable; long questions are weaker because
  their extra words pull in other slides.
- **Limits:** the queries were written by the author of this repo from the slide titles, not
  taken from official exercises, and `MIN_SCORE` and the "also related" rule were tuned on these
  same queries, so the numbers are optimistic. One query is worth 3 (topic), 5 (question) or
  10 (off-topic) percentage points.

## Tests and lint

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest
node --test site/search.test.mjs
```

Tests build tiny PDFs on the fly and use a fake embedder: no network, no model, no slides.
GitHub Actions runs all three on every push (`.github/workflows/ci.yml`).

## Known limitations
- The web page was tested in desktop Chrome (a real browser driven from a script), **not yet on
  a phone**. The first visit needs about 135 MB of download, and the page used roughly 800 MB of
  memory in Chrome (measured), which a small phone may not have.
- Diagrams are images or scattered labels, so a topic that only appears inside a figure may
  be missed.
- Thai queries find the best range well; "also related" lines need an English term in the
  query (for example "NAT" in "NAT ทำงานอย่างไร").
- `MIN_SCORE` (0.82) separates on-topic from off-topic queries only roughly: 3 of the 10
  off-topic probes still return a page. Scores depend on the model; re-measure it if you
  change `EMBED_MODEL`.
- The browser and Python compute vectors with different tokenizer code, so results can differ
  slightly (for example one extra page at the edge of a range).
