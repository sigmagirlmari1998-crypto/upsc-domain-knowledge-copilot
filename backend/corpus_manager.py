import io
import json
import base64
import numpy as np
from backend.db import get_session
from backend.models import Corpus, Document


# ---------- corpora ----------
def create_corpus(user_id: int, name: str) -> int:
    name = name.strip()
    if not name:
        raise ValueError("Corpus name is required.")
    with get_session() as s:
        c = Corpus(user_id=user_id, name=name)
        s.add(c)
        s.flush()
        return c.id


def list_corpora(user_id: int):
    with get_session() as s:
        rows = (s.query(Corpus)
                  .filter(Corpus.user_id == user_id)
                  .order_by(Corpus.created_at.desc()).all())
        return [{"id": r.id, "name": r.name} for r in rows]


def delete_corpus(user_id: int, corpus_id: int):
    with get_session() as s:
        c = s.query(Corpus).filter(Corpus.id == corpus_id,
                                   Corpus.user_id == user_id).first()
        if c:
            s.delete(c)


def get_active_corpus(user_id: int, corpus_id: int):
    with get_session() as s:
        c = s.query(Corpus).filter(Corpus.id == corpus_id,
                                   Corpus.user_id == user_id).first()
        return {"id": c.id, "name": c.name} if c else None


# ---------- documents / embeddings ----------
def _emb_to_blob(emb: np.ndarray) -> bytes:
    buf = io.BytesIO()
    np.save(buf, np.asarray(emb), allow_pickle=False)
    return buf.getvalue()


def _blob_to_emb(blob: bytes) -> np.ndarray:
    return np.load(io.BytesIO(blob), allow_pickle=False)


def save_document(corpus_id: int, filename: str,
                  chunks: list[dict], embeddings: np.ndarray):
    """chunks: [{source,page,text}, ...]  embeddings: np.ndarray (N, d)"""
    if not chunks:
        return
    with get_session() as s:
        # de-dupe: replace any prior upload with same filename in this corpus
        (s.query(Document)
           .filter(Document.corpus_id == corpus_id,
                   Document.filename == filename).delete())
        d = Document(
            corpus_id=corpus_id,
            filename=filename,
            chunks_json=json.dumps(chunks, ensure_ascii=False),
            embeddings_npy=_emb_to_blob(embeddings),
        )
        s.add(d)


def load_corpus_data(corpus_id: int):

    with get_session() as s:

        rows = (
            s.query(Document)
            .filter(Document.corpus_id == corpus_id)
            .all()
        )

        # copy everything before session closes
        data = [
            (
                row.chunks_json,
                row.embeddings_npy
            )
            for row in rows
        ]

    all_chunks = []
    all_embs = []

    for chunks_json, embeddings_blob in data:

        all_chunks.extend(
            json.loads(chunks_json)
        )

        all_embs.append(
            _blob_to_emb(embeddings_blob)
        )

    if not all_chunks:
        return [], None

    return all_chunks, np.vstack(all_embs)


def list_documents(corpus_id: int):
    with get_session() as s:
        rows = s.query(Document).filter(Document.corpus_id == corpus_id).all()
        return [{"id": r.id, "filename": r.filename} for r in rows]

