"""Index the clinic knowledge base (backend/hackathon-hospital/knowledge/*.md) for RAG search.

Only new or changed sections are sent to OpenAI for embeddings, so running it on every deploy is free
when the texts did not change. Run from backend/hackathon-hospital with the environment loaded:
    python ../../deploy/ingest_knowledge.py
"""
import os
import sys

# Run from backend/hackathon-hospital: make the app package importable.
sys.path.insert(0, os.getcwd())

from app.database import SessionLocal
from app.utils.knowledge import ingest_directory


def main() -> int:
    db = SessionLocal()
    try:
        stats = ingest_directory(db)
    finally:
        db.close()
    print("Knowledge base: {documents} documents, {chunks} sections "
          "(added {added}, updated {updated}, removed {removed}, unchanged {unchanged})".format(**stats))
    return 0


if __name__ == "__main__":
    sys.exit(main())
