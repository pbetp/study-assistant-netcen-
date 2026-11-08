# netcentric-study-assistant

Find **where** a topic is in your course slides. Type a topic or a question, in English or
Thai, and get the chapter and page range to start reading.

```
> .\ask udp
Start reading: Chapter 3, p.24-29
  UDP: User Datagram Protocol · UDP: Transport Layer Actions
Also related:
  Chapter 3, p.137      QUIC: Quick UDP Internet Connections

> .\ask NAT ทำงานอย่างไร
Start reading: Chapter 4, p.64-68
  NAT: network address translation

> .\ask pizza
Not found in the slides.
```

Everything runs locally: no API key, no GPU needed, no slide text leaves your computer.

> **Course slides are copyrighted and are not in this repository.** Put your own PDFs in
> `data/` (git-ignored). The index (`chroma_db/`) is git-ignored too, because it contains
> the slide text.

## Run it (Windows, PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt

# 1. put your PDFs in data\  (another course: $env:DOCS_DIR = "other_folder")
# 2. build the index once (the first run downloads a ~470 MB model into .cache\)
.\.venv\Scripts\python.exe -m app.cli index

# 3. search
.\ask udp                  # one search (~10 s: most of it is loading the model)
.\ask                      # keep asking: the model loads once, then every search is instant
```

Web page and REST API: `.\.venv\Scripts\python.exe -m uvicorn app.api:create_default_app --factory`,
then open http://127.0.0.1:8000/ for a search box, or call `GET /find?q=udp` (docs at `/docs`).

To use it from a phone, deploy it as a private web app: see [DEPLOY.md](DEPLOY.md).

## How it works

```
index (once)   PDF ──▶ one Page per slide ──▶ vector ──▶ Chroma (chroma_db/)
                       page number + title    multilingual-e5-small

find           query ──▶ vector ──▶ 15 closest pages ──▶ drop pages below MIN_SCORE
                 ──▶ merge neighbouring pages into ranges  (p.43, 44, 45, 46 → p.43-46)
                 ──▶ best range + other ranges whose title shares a word with the query
```

| file | job |
|---|---|
| `app/ingest.py` | read PDFs: text, page number and title of every slide |
| `app/embed.py` | text → vector (real model, and a fake one for tests) |
| `app/store.py` | save and search vectors in Chroma |
| `app/search.py` | the finder: closest pages → ranges → results |
| `app/cli.py` | `index` and `find` commands, output format |
| `app/api.py` | REST API (`/find`, `/health`) and the page below |
| `app/static/index.html` | one-page search form (plain HTML + JS, no framework) |
| `Dockerfile` | packages the app for hosting (see DEPLOY.md) |
| `app/config.py` | settings from environment variables |

Each design choice was measured, not guessed:

- **Whole pages, not chunks.** Slides are short (about 450 characters). An earlier version
  split them into chunks of 250-2000 characters; smaller chunks never helped (hit@5: 70%,
  65%, 80%, 80% for 250, 500, 1000, 2000), so a page is the unit and every result is a page.
- **Titles from the largest font.** The first line of a slide is often a label inside a
  diagram. The largest text gave a sensible title on 620 of 625 pages (checked by reading
  the full list); the other 5 are diagram-only slides, shown as "(diagram slide, no title)".
- **Neighbouring pages merged into ranges.** A topic usually spans several slides, and one
  range is one place to read.
- **Pages with fewer than 8 words are skipped.** Dividers such as "Additional Chapter 5
  slides" are almost empty, so they matched random queries like "pizza".
- **"Also related" only if the title shares a word with the query.** Without this rule most
  extra lines were unrelated pages with almost the same score. On 55 queries it cut the
  unrelated lines from 81 to 38, while hit@3 for topics went from 100% to 97%.
- **Vector search only.** A throwaway experiment (not in this repo) also tried keyword
  search (BM25) and a mix of both: no overall gain on the same queries, so the simplest
  method stayed.
- **No LLM.** An earlier version wrote answers with a local LLM (Ollama). It worked, but
  for the real use, "where do I start reading?", a page list is faster and cannot invent
  content.

## Evaluation

`eval/questions.json` has 65 queries, each with the file and page(s) that answer it:
35 short **topics** (what you would type, including 5 in Thai), 20 full **questions**, and
10 **off-topic** queries that are correct only if the finder says "not found".
A query is a *hit at k* if an expected page is inside one of the first k results; the finder
shows up to 3, so hit@3 means "the right page is on the screen".

Run `python -m eval.run_eval --out eval/results.md` (uses the index you built):

| queries | n | hit@1 | hit@3 |
|---|---|---|---|
| topic | 35 | 91% | 97% |
| question | 20 | 60% | 70% |
| off-topic | 10 | 70% | 70% |
| all | 65 | 78% | 85% |

How to read it:
- **Type the key term.** Short topics find the right place first 91% of the time; long
  questions only 60%, because their extra words pull in other slides.
- **Limits:** the queries were written by the author of this repo from the slide titles,
  not taken from official exercises, and `MIN_SCORE` and the "also related" rule were tuned
  on these same queries, so the numbers are optimistic. One query is worth 3 (topic),
  5 (question) or 10 (off-topic) percentage points.

## Tests and lint

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest
```

Tests build tiny PDFs on the fly and use a fake embedder: no network, no model, no slides.
GitHub Actions runs both on every push (`.github/workflows/ci.yml`).

## Known limitations
- Diagrams are images or scattered labels, so a topic that only appears inside a figure
  may be missed.
- Thai queries find the best range well; "also related" lines need an English term in the
  query (for example "NAT" in "NAT ทำงานอย่างไร").
- `MIN_SCORE` (0.81) separates on-topic from off-topic queries only roughly: 3 of the 10
  off-topic probes still return a page. Scores depend on the model; re-measure it if you
  change `EMBED_MODEL`.
