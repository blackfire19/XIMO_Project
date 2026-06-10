from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.security import verify_password, create_access_token
from app.core.deps import get_current_user
from app.config import settings
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["认证"])

_COOKIE_NAME = "access_token"
_COOKIE_MAX_AGE = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60


@router.post("/login")
def login(
    response: Response,
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.username == form.username).first()
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已禁用")
    token = create_access_token({"sub": user.id})
    response.set_cookie(
        key=_COOKIE_NAME,
        value=token,
        max_age=_COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
    )
    return {
        "user": {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "role": user.role.name,
            "role_label": user.role.label,
            "salesperson_code": user.salesperson_code,
        },
    }


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(key=_COOKIE_NAME, samesite="lax")
    return {"detail": "已退出登录"}


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "role": current_user.role.name,
        "role_label": current_user.role.label,
        "salesperson_code": current_user.salesperson_code,
    }
