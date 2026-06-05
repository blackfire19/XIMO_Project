from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from app.core.deps import get_current_user, require_roles
from app.database import get_db
from app.models.announcement import Announcement
from app.models.user import User

router = APIRouter(prefix="/announcements", tags=["公告通知"])


class AnnouncementCreate(BaseModel):
    content: str


@router.get("/")
def list_announcements(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items = (
        db.query(Announcement)
        .filter(Announcement.is_active == True)
        .order_by(Announcement.created_at.desc())
        .all()
    )
    result = []
    for a in items:
        creator = db.get(User, a.created_by)
        result.append(
            {
                "id": a.id,
                "content": a.content,
                "created_by": a.created_by,
                "creator_name": creator.full_name if creator else "",
                "created_at": str(a.created_at),
            }
        )
    return result


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_announcement(
    body: AnnouncementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("boss", "purchaser", "super_admin")),
):
    ann = Announcement(
        content=body.content,
        created_by=current_user.id,
        is_active=True,
    )
    db.add(ann)
    db.commit()
    db.refresh(ann)
    return {"id": ann.id, "content": ann.content, "created_at": str(ann.created_at)}


@router.delete("/{announcement_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_announcement(
    announcement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ann = db.get(Announcement, announcement_id)
    if not ann:
        raise HTTPException(status_code=404, detail="公告不存在")
    if ann.created_by != current_user.id and current_user.role.name != "super_admin":
        raise HTTPException(status_code=403, detail="只能撤销自己发布的公告")
    ann.is_active = False
    ann.revoked_at = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
    ann.revoked_by = current_user.id
    db.commit()
