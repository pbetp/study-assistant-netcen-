// The page: loads the index and the search model, then answers queries in the browser.
// The search logic itself is in search.js.
import { findPages, pagesText } from "./search.js";

// Pinned version (never "latest"): the page must keep working when a new release comes out.
const TRANSFORMERS_URL = "https://cdn.jsdelivr.net/npm/@huggingface/transformers@3.8.1";

const form = document.getElementById("form");
const input = document.getElementById("q");
const statusLine = document.getElementById("status");
const results = document.getElementById("results");

async function fetchOk(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`could not load ${url} (HTTP ${response.status})`);
  return response;
}

// The three index files written by `python -m app.cli export-site`.
async function loadIndex() {
  const [config, data, buffer] = await Promise.all([
    fetchOk("index/config.json").then((r) => r.json()),
    fetchOk("index/pages.json").then((r) => r.json()),
    fetchOk("index/vectors.bin").then((r) => r.arrayBuffer()),
  ]);
  const vectors = new Float32Array(buffer);
  if (vectors.length !== config.count * config.dim) throw new Error("index files do not match");
  return { config, data, vectors };
}

// Downloads the same quantized model the Python side uses (cached by the browser afterwards).
async function loadModel(config) {
  const { pipeline } = await import(TRANSFORMERS_URL); // dynamic: a failed download can be caught
  const files = new Map(); // file name -> {loaded, total}, to show one overall percentage
  const progress = (event) => {
    if (event.status !== "progress") return;
    files.set(event.file, { loaded: event.loaded, total: event.total });
    const all = [...files.values()];
    const total = all.reduce((sum, f) => sum + f.total, 0);
    const loaded = all.reduce((sum, f) => sum + f.loaded, 0);
    statusLine.textContent = `Downloading the search model… ${Math.round((100 * loaded) / total)}%`;
  };
  return pipeline("feature-extraction", config.model, {
    dtype: config.dtype,
    progress_callback: progress,
  });
}

async function start() {
  statusLine.textContent = "Loading…";
  const index = await loadIndex();
  const extractor = await loadModel(index.config);
  statusLine.textContent = "";
  return { ...index, extractor };
}

const ready = start();
ready.catch((error) => {
  statusLine.textContent = `Could not start: ${error.message}`;
});

// Builds one result card. textContent (not innerHTML) keeps slide titles from being read as HTML.
function card(range, isBest) {
  const box = document.createElement("div");
  box.className = "card" + (isBest ? " best" : "");
  const label = document.createElement("div");
  label.className = "label";
  label.textContent = isBest ? "Start reading" : "Also related";
  const where = document.createElement("div");
  where.className = "where";
  where.textContent = `${range.chapter}, p.${pagesText(range)}`;
  const titles = document.createElement("div");
  titles.className = "titles";
  titles.textContent = range.titles.length ? range.titles.join(" · ") : "(diagram slide, no title)";
  box.append(label, where, titles);
  return box;
}

async function search(query) {
  results.replaceChildren();
  let app;
  try {
    statusLine.textContent = "Loading the search model… (first visit only)";
    app = await ready;
  } catch {
    return; // the error is already shown
  }
  statusLine.textContent = "Searching…";
  const output = await app.extractor(app.config.query_prefix + query, {
    pooling: "mean",
    normalize: true,
  });
  const found = findPages({
    query,
    queryVec: output.data,
    data: app.data,
    vectors: app.vectors,
    config: app.config,
  });
  if (found.length === 0) {
    statusLine.textContent = "Not found in the slides.";
    return;
  }
  statusLine.textContent = "";
  found.forEach((range, i) => results.append(card(range, i === 0)));
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const query = input.value.trim();
  if (!query) return;
  history.replaceState(null, "", "?q=" + encodeURIComponent(query)); // shareable link
  search(query).catch((error) => {
    statusLine.textContent = `Something went wrong: ${error.message}`;
  });
});

// A link like  index.html?q=udp  fills the box and searches as soon as the page is ready.
const fromLink = new URLSearchParams(location.search).get("q");
if (fromLink) {
  input.value = fromLink;
  form.requestSubmit();
}
