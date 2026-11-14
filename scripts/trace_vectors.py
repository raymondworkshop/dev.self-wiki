"""Local multilingual-e5-small vectors over trace paragraphs.

Keyword scores and cosine similarity stay on separate lists. This module only
returns a best-first cosine ranking. Fusion happens in trace_retrieval.
"""

from __future__ import annotations

import hashlib
import logging
import os
import threading
from dataclasses import dataclass
from pathlib import Path

from config import TRACE_INDEX_JSON, TRACE_VECTORS_NPZ

try:
    import numpy as np
except ImportError:  # keyword retrieval still runs
    np = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

MODEL_ID = os.environ.get("TRACE_EMBED_MODEL", "intfloat/multilingual-e5-small")
_LOCK = threading.Lock()
_MODEL = None
_CACHE: "VectorStore | None" = None
_UNAVAILABLE = False


@dataclass
class VectorStore:
    ids: list[str]
    hashes: list[str]
    matrix: np.ndarray
    mtime: int


_WARNED = False


def vectors_enabled() -> bool:
    return os.environ.get("TRACE_VECTORS", "1").strip().lower() not in (
        "0",
        "false",
        "no",
    )


def _warn_missing() -> None:
    global _WARNED
    if _WARNED:
        return
    _WARNED = True
    logger.warning(
        "numpy/sentence-transformers not installed; trace vectors are off "
        "(pip install -r requirements.txt)"
    )


def _device() -> str:
    import torch

    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def local_model_dir(model_id: str | None = None) -> Path | None:
    """Folder that already holds the embedding weights. Never contacts the Hub."""
    model_id = (model_id or MODEL_ID).strip()
    direct = Path(model_id).expanduser()
    if direct.is_dir() and (direct / "modules.json").is_file():
        return direct
    snapshots = (
        Path.home()
        / ".cache"
        / "huggingface"
        / "hub"
        / f"models--{model_id.replace('/', '--')}"
        / "snapshots"
    )
    if not snapshots.is_dir():
        return None
    found = [p for p in snapshots.iterdir() if (p / "modules.json").is_file()]
    if not found:
        return None
    return max(found, key=lambda p: p.stat().st_mtime)


def get_model():
    """Load the embedding model once per process, from disk only."""
    global _MODEL, _UNAVAILABLE
    if _MODEL is not None:
        return _MODEL
    if _UNAVAILABLE:
        raise RuntimeError("embedding model unavailable")
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        _UNAVAILABLE = True
        raise RuntimeError(
            "sentence-transformers is not installed; trace stays keyword-only"
        ) from exc
    local = local_model_dir()
    if local is None:
        _UNAVAILABLE = True
        raise RuntimeError(
            f"{MODEL_ID} is not cached locally; Trace stays keyword-only"
        )
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    device = _device()
    logger.info("loading embeddings from %s on %s", local, device)
    model = SentenceTransformer(str(local), device=device, local_files_only=True)
    model.max_seq_length = 512
    _MODEL = model
    return model


def preload() -> None:
    if vectors_enabled():
        get_model()


def _text_hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


def _index_mtime() -> int:
    try:
        return int(TRACE_INDEX_JSON.stat().st_mtime_ns)
    except OSError:
        return 0


def _encode(texts: list[str], *, prefix: str) -> np.ndarray:
    model = get_model()
    payload = [f"{prefix}{text}" for text in texts]
    batch = int(os.environ.get("TRACE_EMBED_BATCH", "64") or 64)
    vectors = model.encode(
        payload,
        normalize_embeddings=True,
        batch_size=max(1, batch),
        show_progress_bar=False,
    )
    return np.asarray(vectors, dtype=np.float32)


def encode_query(text: str) -> np.ndarray:
    return _encode([text], prefix="query: ")[0]


def encode_passages(texts: list[str]) -> np.ndarray:
    if not texts:
        return np.zeros((0, 384), dtype=np.float32)
    # Log long jobs; a full vault is a few minutes.
    step = 2048
    parts: list[np.ndarray] = []
    for start in range(0, len(texts), step):
        chunk = texts[start : start + step]
        if len(texts) > step:
            logger.info(
                "trace vectors: encoding %s–%s / %s",
                start + 1,
                start + len(chunk),
                len(texts),
            )
        parts.append(_encode(chunk, prefix="passage: "))
    return np.vstack(parts)


def _load() -> VectorStore | None:
    if not TRACE_VECTORS_NPZ.exists():
        return None
    data = np.load(TRACE_VECTORS_NPZ, allow_pickle=False)
    ids = [str(x) for x in data["ids"].tolist()]
    hashes = [str(x) for x in data["hashes"].tolist()]
    matrix = np.asarray(data["vectors"], dtype=np.float32)
    mtime = int(data["index_mtime"][0]) if "index_mtime" in data.files else 0
    if len(ids) != matrix.shape[0]:
        return None
    return VectorStore(ids=ids, hashes=hashes, matrix=matrix, mtime=mtime)


def _save(store: VectorStore) -> None:
    TRACE_VECTORS_NPZ.parent.mkdir(parents=True, exist_ok=True)
    tmp = TRACE_VECTORS_NPZ.with_name(TRACE_VECTORS_NPZ.stem + "-partial.npz")
    np.savez(
        tmp,
        ids=np.array(store.ids),
        hashes=np.array(store.hashes),
        vectors=store.matrix,
        index_mtime=np.array([store.mtime], dtype=np.int64),
    )
    tmp.replace(TRACE_VECTORS_NPZ)


def ensure_vectors(paragraphs: list[dict], *, force: bool = False) -> VectorStore | None:
    """Build or refresh vectors for a raw/ catalog. Reuses rows whose text is unchanged."""
    global _CACHE
    if np is None or not vectors_enabled():
        if np is None:
            _warn_missing()
        return None
    mtime = _index_mtime()
    usable = [p for p in paragraphs if p.get("id")]
    with _LOCK:
        if (
            not force
            and _CACHE is not None
            and _CACHE.mtime == mtime
            and len(_CACHE.ids) == len(usable)
        ):
            return _CACHE
        existing = None if force else (_CACHE or _load())
        old: dict[str, tuple[str, np.ndarray]] = {}
        if existing is not None:
            for i, pid in enumerate(existing.ids):
                old[pid] = (existing.hashes[i], existing.matrix[i])

        ids: list[str] = []
        hashes: list[str] = []
        rows: list[np.ndarray | None] = []
        missing_at: list[int] = []
        missing_text: list[str] = []
        for para in usable:
            pid = str(para["id"])
            digest = _text_hash(para.get("text") or "")
            prev = old.get(pid)
            ids.append(pid)
            hashes.append(digest)
            if prev is not None and prev[0] == digest:
                rows.append(prev[1])
            else:
                rows.append(None)
                missing_at.append(len(ids) - 1)
                missing_text.append(para.get("text") or "")

        if existing is not None and not missing_text and existing.ids == ids:
            if existing.mtime != mtime or not TRACE_VECTORS_NPZ.exists():
                existing.mtime = mtime
                _save(existing)
            _CACHE = existing
            return existing

        if missing_text:
            logger.info("trace vectors: encoding %s / %s paragraphs", len(missing_text), len(ids))
            encoded = encode_passages(missing_text)
            for slot, vec in zip(missing_at, encoded):
                rows[slot] = vec
        if not rows:
            return None
        matrix = np.stack(rows).astype(np.float32)
        store = VectorStore(ids=ids, hashes=hashes, matrix=matrix, mtime=mtime)
        _save(store)
        _CACHE = store
        logger.info("trace vectors: %s rows → %s", len(ids), TRACE_VECTORS_NPZ.name)
        return store


def _ephemeral(paragraphs: list[dict]) -> VectorStore | None:
    usable = [p for p in paragraphs if p.get("id")]
    if not usable:
        return None
    matrix = encode_passages([p.get("text") or "" for p in usable])
    return VectorStore(
        ids=[str(p["id"]) for p in usable],
        hashes=[_text_hash(p.get("text") or "") for p in usable],
        matrix=matrix,
        mtime=0,
    )


def search(
    query: str,
    paragraphs: list[dict],
    store: VectorStore,
    *,
    top_k: int,
    min_score: float,
) -> list[tuple[float, dict]]:
    if not query.strip() or store.matrix.size == 0:
        return []
    qv = encode_query(query)
    id_to_i = {pid: i for i, pid in enumerate(store.ids)}
    if (
        len(paragraphs) == len(store.ids)
        and paragraphs
        and paragraphs[0].get("id") == store.ids[0]
        and paragraphs[-1].get("id") == store.ids[-1]
    ):
        sims = store.matrix @ qv
        picked = paragraphs
    else:
        idxs: list[int] = []
        picked = []
        for para in paragraphs:
            i = id_to_i.get(para.get("id") or "")
            if i is None:
                continue
            idxs.append(i)
            picked.append(para)
        if not idxs:
            return []
        sims = store.matrix[np.asarray(idxs, dtype=np.int64)] @ qv
    order = np.argsort(-sims)
    hits: list[tuple[float, dict]] = []
    for i in order:
        score = float(sims[int(i)])
        if score < min_score:
            break
        hits.append((score, picked[int(i)]))
        if len(hits) >= top_k:
            break
    return hits


def search_paragraphs(
    query: str,
    paragraphs: list[dict],
    *,
    catalog: list[dict] | None = None,
    top_k: int = 32,
    min_score: float = 0.78,
) -> list[tuple[float, dict]]:
    """Cosine hits for `paragraphs`, building the raw/ catalog when needed."""
    if np is None:
        _warn_missing()
        return []
    if not vectors_enabled() or not query.strip():
        return []
    catalog = catalog if catalog is not None else paragraphs
    persistent = bool(catalog) and str(catalog[0].get("path") or "").startswith("raw/")
    try:
        store = ensure_vectors(catalog) if persistent else _ephemeral(paragraphs)
    except Exception:
        logger.exception("trace vectors unavailable; keyword only")
        return []
    if store is None:
        return []
    return search(query, paragraphs, store, top_k=top_k, min_score=min_score)
