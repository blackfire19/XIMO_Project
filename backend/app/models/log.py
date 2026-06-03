from sqlalchemy import BigInteger, Integer, String, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class OperationLog(Base):
    __tablename__ = "operation_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    operator_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    module: Mapped[str] = mapped_column(String(50), nullable=False)
    record_id: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False)  # create / update / delete
    field_changes: Mapped[dict | None] = mapped_column(JSONB)
    operated_at: Mapped[str] = mapped_column(server_default="NOW()")
