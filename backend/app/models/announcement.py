from sqlalchemy import Boolean, Integer, Text, ForeignKey, text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Announcement(Base):
    __tablename__ = "announcements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[str] = mapped_column(server_default=text("now()"))
    revoked_at: Mapped[str | None] = mapped_column()
    revoked_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
