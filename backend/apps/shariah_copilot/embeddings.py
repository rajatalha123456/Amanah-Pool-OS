"""
Local multilingual embeddings for the semantic half of retrieval (English, Urdu and Arabic share one vector space, so an
English question finds an Urdu ruling). The model runs inside this process (ONNX, no PyTorch) and nothing leaves the
network. If it is switched off or cannot load, retrieval degrades to keyword-only and the answer says so.
"""

import logging
import threading

import numpy as np
from django.conf import settings

logger = logging.getLogger("apps")
_lock = threading.Lock()
_model = None
_failed = False


class EmbeddingsUnavailable(Exception):
    pass


def backend():
    return getattr(settings, "COPILOT_EMBEDDING_BACKEND", "fastembed")


def model_name():
    if backend() == "hash":
        return "hash-256"
    return settings.COPILOT_EMBEDDING_MODEL


def _hash_embed(texts):
    """Deterministic bag-of-words vectors for tests and offline use: no model, no network."""
    import zlib

    from .search import tokenize

    out = np.zeros((len(texts), 256), dtype=np.float32)
    for row, text in enumerate(texts):
        for token in tokenize(text):
            out[row, zlib.crc32(token.encode("utf-8")) % 256] += 1.0
    return out


def _load():
    global _model, _failed
    if _model is not None:
        return _model
    if _failed:
        raise EmbeddingsUnavailable("The embedding model could not be loaded earlier in this process.")
    with _lock:
        if _model is None:
            try:
                from fastembed import TextEmbedding

                _model = TextEmbedding(settings.COPILOT_EMBEDDING_MODEL, cache_dir=settings.COPILOT_MODEL_CACHE_DIR)
            except Exception as exc:  # no network, no model files, unsupported platform ...
                _failed = True
                logger.warning("Copilot embedding model unavailable: %s", exc)
                raise EmbeddingsUnavailable(str(exc)) from exc
    return _model


def embed(texts):
    """L2-normalised float32 vectors, shape (len(texts), dim). Raises EmbeddingsUnavailable when semantic search is off."""
    kind = backend()
    if kind == "none":
        raise EmbeddingsUnavailable("Semantic search is switched off (COPILOT_EMBEDDING_BACKEND=none).")
    if not texts:
        return np.zeros((0, 0), dtype=np.float32)
    if kind == "hash":
        vectors = _hash_embed(texts)
    else:
        vectors = np.array(list(_load().embed(texts)), dtype=np.float32)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return (vectors / norms).astype(np.float32)


def to_bytes(vector):
    return np.asarray(vector, dtype=np.float32).tobytes()


def from_bytes(blob):
    return np.frombuffer(bytes(blob), dtype=np.float32)
