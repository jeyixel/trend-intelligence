"""Text similarity backend.
Uses a pretrained sentence-embedding model when `sentence-transformers` is installed (and the model
can be downloaded); otherwise falls back to character n-gram TF-IDF so the prototype always runs."""
import numpy as np

import config

_st_model = None
_st_failed = False


def _load_st():
    global _st_model, _st_failed
    if _st_model is not None or _st_failed:
        return _st_model
    try:
        from sentence_transformers import SentenceTransformer
        _st_model = SentenceTransformer(config.EMBEDDING_MODEL)
    except Exception as e:
        print(f"[embedder] sentence-transformers unavailable ({type(e).__name__}); using TF-IDF fallback")
        _st_failed = True
    return _st_model


def backend_name() -> str:
    return f"sentence-transformers:{config.EMBEDDING_MODEL}" if _load_st() else "tfidf-char-ngrams (fallback)"


_doc_cache: dict = {}


def similarities(query: str, docs: list[str]) -> np.ndarray:
    """Cosine similarity of `query` to each doc, clipped to [0, 1]."""
    if not docs:
        return np.array([])
    model = _load_st()
    if model is not None:
        key = tuple(docs)
        if key not in _doc_cache:
            _doc_cache.clear()
            _doc_cache[key] = model.encode(docs, normalize_embeddings=True)
        q = model.encode([query], normalize_embeddings=True)[0]
        sims = _doc_cache[key] @ q
    else:
        from sklearn.feature_extraction.text import TfidfVectorizer
        vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True, lowercase=True)
        m = vec.fit_transform(docs + [query])
        sims = (m[:-1] @ m[-1].T).toarray().ravel()   # rows are L2-normalised -> cosine
    return np.clip(sims, 0.0, 1.0)
