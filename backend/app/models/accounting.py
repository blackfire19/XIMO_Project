from sqlalchemy import Boolean, Integer, Numeric, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class AccountingRecord(Base):
    __tablename__ = "accounting_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("formal_orders.id", ondelete="CASCADE"), unique=True, nullable=False)
    profit: Mapped[float | None] = mapped_column(Numeric(14, 2))
    notes: Mapped[str | None] = mapped_column(Text)
    salary_calculated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    file_name: Mapped[str | None] = mapped_column(String(255))
    file_path: Mapped[str | None] = mapped_column(String(500))
    recorded_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    recorded_at: Mapped[str] = mapped_column(server_default="NOW()")
    updated_at: Mapped[str] = mapped_column(server_default="NOW()")

    order: Mapped["FormalOrder"] = relationship(foreign_keys=[order_id], back_populates="accounting_record")  # type: ignore
    recorder: Mapped["User"] = relationship(foreign_keys=[recorded_by])  # type: ignore
