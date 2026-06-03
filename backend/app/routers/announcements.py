from fastapi import APIRouter

router = APIRouter(prefix="/announcements", tags=["公告通知"])


@router.get("/")
def list_announcements():
    pass


@router.post("/")
def create_announcement():
    # TODO: 老板/采购员可发
    pass


@router.delete("/{announcement_id}")
def revoke_announcement(announcement_id: int):
    # TODO: 仅发布人可撤销
    pass
