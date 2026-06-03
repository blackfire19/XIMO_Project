from sqlalchemy import Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class UserColumnPref(Base):
    __tablename__ = "user_column_prefs"
    __table_args__ = (UniqueConstraint("user_id", "module"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    module: Mapped[str] = mapped_column(String(50), nullable=False)
    columns_config: Mapped[list] = mapped_column(JSONB, nullable=False)
    updated_at: Mapped[str] = mapped_column(server_default="NOW()")
