from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.deps import require_roles, get_current_user
from app.core.security import hash_password
from app.models.user import User, Role
from app.schemas.user import UserCreate, UserUpdate, UserOut, RoleOut

router = APIRouter(prefix="/users", tags=["用户管理"])


@router.get("/roles", response_model=list[RoleOut])
def list_roles(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("super_admin")),
):
    return db.query(Role).all()


@router.get("/", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("super_admin")),
):
    return db.query(User).order_by(User.id).all()


@router.get("/salespersons", response_model=list[UserOut])
def list_salespersons(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("super_admin", "boss", "finance")),
):
    """供财务/老板筛选用：返回所有在职业务员"""
    from app.models.user import Role
    return (
        db.query(User)
        .join(Role, User.role_id == Role.id)
        .filter(Role.name == "salesperson", User.is_active == True)
        .order_by(User.full_name)
        .all()
    )


@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    body: UserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("super_admin")),
):
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")

    role = db.get(Role, body.role_id)
    if not role:
        raise HTTPException(status_code=400, detail="角色不存在")

    if role.name == "salesperson" and not body.salesperson_code:
        raise HTTPException(status_code=400, detail="业务员必须指定业务员编码")

    if body.salesperson_code:
        conflict = db.query(User).filter(User.salesperson_code == body.salesperson_code).first()
        if conflict:
            raise HTTPException(status_code=400, detail="业务员编码已被占用")

    now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
    user = User(
        username=body.username,
        password_hash=hash_password(body.password),
        full_name=body.full_name,
        role_id=body.role_id,
        salesperson_code=body.salesperson_code,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.put("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    body: UserUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(require_roles("super_admin")),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if body.role_id is not None:
        role = db.get(Role, body.role_id)
        if not role:
            raise HTTPException(status_code=400, detail="角色不存在")
        user.role_id = body.role_id

    # 以最终角色为基准做校验
    target_role = db.get(Role, user.role_id)
    if target_role.name == "salesperson":
        code = body.salesperson_code if body.salesperson_code is not None else user.salesperson_code
        if not code:
            raise HTTPException(status_code=400, detail="业务员必须指定业务员编码")
    else:
        # 角色改为非业务员时，自动清空编码
        if body.role_id is not None:
            user.salesperson_code = None

    if body.salesperson_code is not None:
        if body.salesperson_code:
            conflict = (
                db.query(User)
                .filter(User.salesperson_code == body.salesperson_code, User.id != user_id)
                .first()
            )
            if conflict:
                raise HTTPException(status_code=400, detail="业务员编码已被占用")
        user.salesperson_code = body.salesperson_code or None

    if body.full_name is not None:
        user.full_name = body.full_name

    if body.password:
        user.password_hash = hash_password(body.password)

    db.commit()
    db.refresh(user)
    return user


@router.put("/{user_id}/toggle-active", response_model=UserOut)
def toggle_user_active(
    user_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(require_roles("super_admin")),
):
    if user_id == current.id:
        raise HTTPException(status_code=400, detail="不能禁用自己的账号")

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    user.is_active = not user.is_active
    db.commit()
    db.refresh(user)
    return user
