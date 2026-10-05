import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.routes.auth import RoleChecker
from app.schemas import KnowledgeHit
from app.utils import knowledge

router = APIRouter(prefix="/knowledge", tags=["Knowledge base"])
logger = logging.getLogger(__name__)

all_roles = RoleChecker(["admin", "doctor", "patient"])


@router.get("/search", response_model=List[KnowledgeHit], operation_id="search_clinic_knowledge")
def search_clinic_knowledge(
    q: str = Query(..., min_length=2, max_length=500, description="Short question about the clinic, e.g. 'стоимость приёма кардиолога' or 'как отменить запись'"),
    limit: int = Query(4, ge=1, le=8, description="How many sections to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(all_roles),
):
    """Search the SIRIUS clinic knowledge base: address, working hours, contacts, departments, prices and payment,
    booking and cancellation rules, preparation for visits and tests, patient rules, how the AI assistant and cases work.
    Returns the most relevant document sections. Not a source of medical advice."""
    try:
        hits = knowledge.search(db, q, limit)
    except Exception as exc:
        logger.exception("Knowledge base search failed.")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Knowledge base search failed.") from exc
    return [
        KnowledgeHit(document=chunk.doc_title, section=chunk.section, content=chunk.content, score=score)
        for chunk, score in hits
    ]
