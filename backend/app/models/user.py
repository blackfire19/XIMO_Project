from sqlalchemy import Boolean, Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(50), nullable=False)

    users: Mapped[list["User"]] = relationship(back_populates="role")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(50), nullable=False)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), nullable=False)
    salesperson_code: Mapped[str | None] = mapped_column(String(20), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[str] = mapped_column(server_default="NOW()")
    updated_at: Mapped[str] = mapped_column(server_default="NOW()")

    role: Mapped[Role] = relationship(back_populates="users")
