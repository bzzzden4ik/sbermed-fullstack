"""Minimal RAG over the clinic knowledge base (Markdown files in KNOWLEDGE_DIR).

Indexing splits every document into sections (`## ...`), embeds them with OpenAI and stores them in
`knowledge_chunks` (pgvector on PostgreSQL). Search embeds the question and returns the closest sections.
Only new or changed sections are embedded again, so re-indexing on every deploy costs nothing.
"""
import hashlib
import logging
import math
import os
import re
from dataclasses import dataclass
from functools import lru_cache

from sqlalchemy import Float, bindparam
from sqlalchemy.orm import Session

from app.config import settings
from app.models import EMBEDDING_DIM, KnowledgeChunk

logger = logging.getLogger(__name__)

MAX_CHUNK_CHARS = 1500


@dataclass
class Chunk:
    doc_slug: str
    doc_title: str
    section: str
    chunk_key: str
    content: str

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(f"{self.doc_title}\n{self.section}\n{self.content}".encode("utf-8")).hexdigest()

    @property
    def embedding_text(self) -> str:
        # The document and section titles give short sections enough context for retrieval.
        return f"{self.doc_title}. {self.section}.\n{self.content}"


# --- Embeddings -------------------------------------------------------------------------------

def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed texts with OpenAI. Replaced by a deterministic fake in tests."""
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OpenAI API key is not configured.")
    from openai import OpenAI

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    response = client.embeddings.create(model=settings.KNOWLEDGE_EMBEDDING_MODEL, input=texts)
    return [item.embedding for item in response.data]


@lru_cache(maxsize=512)
def _cached_query_embedding(query: str) -> tuple[float, ...]:
    return tuple(embed_texts([query])[0])


def embed_query(query: str) -> list[float]:
    """Embedding of a search question; identical questions are not sent to OpenAI again."""
    return list(_cached_query_embedding(" ".join(query.lower().split())))


# --- Markdown -> chunks -----------------------------------------------------------------------

def split_markdown(slug: str, text: str) -> list[Chunk]:
    """`# Title` names the document; every `## Section` becomes a chunk (long ones split by paragraphs)."""
    title_match = re.search(r"^#\s+(.+)$", text, flags=re.MULTILINE)
    doc_title = title_match.group(1).strip() if title_match else slug
    chunks: list[Chunk] = []
    for part in re.split(r"^##\s+", text, flags=re.MULTILINE)[1:]:
        heading, _, body = part.partition("\n")
        section = heading.strip()
        body = body.strip()
        if not body:
            continue
        pieces, current = [], ""
        for paragraph in re.split(r"\n\s*\n", body):
            if current and len(current) + len(paragraph) > MAX_CHUNK_CHARS:
                pieces.append(current)
                current = paragraph
            else:
                current = f"{current}\n\n{paragraph}" if current else paragraph
        pieces.append(current)
        for index, piece in enumerate(pieces, start=1):
            key = section if len(pieces) == 1 else f"{section} ({index})"
            chunks.append(Chunk(slug, doc_title, section, key[:300], piece.strip()))
    return chunks


def load_documents(directory: str) -> list[Chunk]:
    chunks: list[Chunk] = []
    for name in sorted(os.listdir(directory)):
        if name.endswith(".md") and not name.startswith("_"):
            with open(os.path.join(directory, name), encoding="utf-8") as f:
                chunks.extend(split_markdown(name[:-3], f.read()))
    return chunks


# --- Indexing ---------------------------------------------------------------------------------

def ingest_directory(db: Session, directory: str | None = None) -> dict[str, int]:
    """Synchronise the knowledge table with the Markdown files. Returns counts of the changes."""
    directory = directory or settings.KNOWLEDGE_DIR
    chunks = load_documents(directory)
    existing = {(row.doc_slug, row.chunk_key): row for row in db.query(KnowledgeChunk).all()}
    wanted = {(chunk.doc_slug, chunk.chunk_key): chunk for chunk in chunks}

    to_embed = [chunk for key, chunk in wanted.items() if key not in existing or existing[key].content_hash != chunk.content_hash]
    vectors = embed_texts([chunk.embedding_text for chunk in to_embed]) if to_embed else []

    added = updated = 0
    for chunk, vector in zip(to_embed, vectors):
        row = existing.get((chunk.doc_slug, chunk.chunk_key))
        if row is None:
            row = KnowledgeChunk(doc_slug=chunk.doc_slug, chunk_key=chunk.chunk_key)
            db.add(row)
            added += 1
        else:
            updated += 1
        row.doc_title = chunk.doc_title
        row.section = chunk.section
        row.content = chunk.content
        row.content_hash = chunk.content_hash
        row.embedding = vector

    removed = 0
    for key, row in existing.items():
        if key not in wanted:
            db.delete(row)
            removed += 1
    db.commit()
    return {"documents": len({c.doc_slug for c in chunks}), "chunks": len(chunks),
            "added": added, "updated": updated, "removed": removed, "unchanged": len(chunks) - added - updated}


# --- Search -----------------------------------------------------------------------------------

def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


def search(db: Session, query: str, limit: int = 4) -> list[tuple[KnowledgeChunk, float]]:
    """Return the closest knowledge chunks with a similarity score (1 = identical meaning)."""
    if db.query(KnowledgeChunk.id).first() is None:
        return []
    vector = embed_query(query)
    if db.get_bind().dialect.name == "postgresql":
        from pgvector.sqlalchemy import Vector

        # pgvector cosine distance operator; the HNSW index (vector_cosine_ops) serves this ordering.
        query_vector = bindparam("query_vector", vector, type_=Vector(EMBEDDING_DIM))
        distance = KnowledgeChunk.embedding.op("<=>", return_type=Float())(query_vector).label("distance")
        rows = db.query(KnowledgeChunk, distance).order_by(distance).limit(limit).all()
        return [(row, round(1 - float(dist), 4)) for row, dist in rows]
    scored = [(row, _cosine_similarity(vector, row.embedding)) for row in db.query(KnowledgeChunk).all()]
    scored.sort(key=lambda item: item[1], reverse=True)
    return [(row, round(score, 4)) for row, score in scored[:limit]]
