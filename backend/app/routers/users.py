from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.deps import require_roles
from app.models.user import User

router = APIRouter(prefix="/users", tags=["用户管理"])


@router.get("/")
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("super_admin")),
):
    users = db.query(User).all()
    return users


@router.post("/")
def create_user():
    # TODO: 创建用户
    pass


@router.put("/{user_id}")
def update_user(user_id: int):
    # TODO: 编辑用户（含指定业务员编码）
    pass


@router.put("/{user_id}/toggle-active")
def toggle_user_active(user_id: int):
    # TODO: 启用/禁用用户
    pass
