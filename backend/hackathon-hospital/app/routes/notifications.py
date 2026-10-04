from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import Notification, User
from app.schemas import NotificationResponse
from app.routes.auth import get_current_user

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=List[NotificationResponse])
def list_notifications(
    unread_only: bool = False,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List the signed-in user's notifications, newest first."""
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    if unread_only:
        query = query.filter(Notification.is_read.is_(False))
    return query.order_by(Notification.created_at.desc(), Notification.id.desc()).limit(limit).all()


@router.post("/{id}/read", response_model=NotificationResponse)
def mark_notification_read(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark one of the signed-in user's notifications as read."""
    notification = db.query(Notification).filter(
        Notification.id == id,
        Notification.user_id == current_user.id,
    ).first()
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return notification


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark all of the signed-in user's notifications as read."""
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read.is_(False),
    ).update({Notification.is_read: True})
    db.commit()
    return None
