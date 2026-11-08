"""Turn text into vectors (embeddings).

An embedding is a list of numbers; texts with similar meaning get similar numbers,
so "find relevant slides" becomes "find the closest vectors".

Two implementations share one small interface (`Embedder`):
- OnnxEmbedder: the real multilingual model (Thai + English), runs locally on the CPU.
  It uses the quantized ONNX file of multilingual-e5-small, the same file the browser
  version of the app downloads, so both give the same vectors.
- FakeEmbedder: deterministic and instant, used in tests so they need no model or network.
"""

import hashlib
import math
import os
import re
from pathlib import Path
from typing import Protocol

import numpy as np

MODEL_REPO = "Xenova/multilingual-e5-small"  # Hugging Face repo that hosts the ONNX files
MODEL_FILE = "onnx/model_quantized.onnx"  # 118 MB; the full-size file is 470 MB
MAX_TOKENS = 512  # longest text the model reads; longer text is cut
PAD_ID = 1  # id of the padding token in this model's vocabulary
# E5 models were trained with these prefixes; leaving them out lowers quality.
QUERY_PREFIX = "query: "
PASSAGE_PREFIX = "passage: "


class Embedder(Protocol):
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


def mean_pool(hidden: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """One vector per text: the average of its token vectors, ignoring padding.

    hidden: (texts, tokens, dim) output of the model.
    mask:   (texts, tokens), 1 for a real token and 0 for padding.
    """
    weights = mask[..., None].astype(np.float32)  # (texts, tokens, 1)
    return (hidden * weights).sum(axis=1) / weights.sum(axis=1)


def normalize(vectors: np.ndarray) -> np.ndarray:
    """Scale every vector to length 1, so cosine similarity is just a dot product."""
    return vectors / np.linalg.norm(vectors, axis=1, keepdims=True)


class OnnxEmbedder:
    """Runs the quantized e5 model with ONNX Runtime. Files are downloaded once to cache_dir."""

    def __init__(
        self,
        repo: str = MODEL_REPO,
        cache_dir: Path = Path(".cache/models"),
        batch_size: int = 16,
    ):
        # Imported here, not at the top, so importing this file stays fast and tests
        # that use FakeEmbedder never load the model libraries.
        os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")  # noisy on Windows
        import onnxruntime
        from huggingface_hub import hf_hub_download
        from tokenizers import Tokenizer

        model_path = hf_hub_download(repo, MODEL_FILE, cache_dir=str(cache_dir))
        tokenizer_path = hf_hub_download(repo, "tokenizer.json", cache_dir=str(cache_dir))
        self._session = onnxruntime.InferenceSession(model_path, providers=["CPUExecutionProvider"])
        self._input_names = {i.name for i in self._session.get_inputs()}
        self._tokenizer = Tokenizer.from_file(tokenizer_path)
        self._tokenizer.enable_truncation(max_length=MAX_TOKENS)
        # Pad every text in a batch to the same length so they fit in one array.
        self._tokenizer.enable_padding(pad_id=PAD_ID, pad_token="<pad>")
        self._batch_size = batch_size

    def _encode(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for start in range(0, len(texts), self._batch_size):
            encoded = self._tokenizer.encode_batch(texts[start : start + self._batch_size])
            ids = np.array([e.ids for e in encoded], dtype=np.int64)
            mask = np.array([e.attention_mask for e in encoded], dtype=np.int64)
            inputs = {"input_ids": ids, "attention_mask": mask}
            if "token_type_ids" in self._input_names:  # this model expects it, all zeros
                inputs["token_type_ids"] = np.zeros_like(ids)
            hidden = self._session.run(None, inputs)[0]  # (texts, tokens, dim)
            vectors.append(normalize(mean_pool(hidden, mask)))
        return np.vstack(vectors).tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._encode([PASSAGE_PREFIX + t for t in texts])

    def embed_query(self, text: str) -> list[float]:
        return self._encode([QUERY_PREFIX + text])[0]


class FakeEmbedder:
    """Bag-of-words hashing: every word adds 1 to one of `dim` buckets.

    Texts that share words end up with similar vectors, so retrieval tests behave
    sensibly. md5 is used instead of Python's hash() because hash() changes between runs.
    """

    def __init__(self, dim: int = 64):
        self.dim = dim

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dim
        for word in re.findall(r"\w+", text.lower()):
            bucket = int(hashlib.md5(word.encode()).hexdigest(), 16) % self.dim
            vector[bucket] += 1.0
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)
