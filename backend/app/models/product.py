from sqlalchemy import Boolean, Integer, Numeric, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    outer_diameter: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    inner_diameter: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    length: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    price_usd: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    name: Mapped[str | None] = mapped_column(String(100))
    material: Mapped[str | None] = mapped_column(String(100))
    standard: Mapped[str | None] = mapped_column(String(100))
    surface_finish: Mapped[str | None] = mapped_column(String(100))
    unit: Mapped[str] = mapped_column(String(20), default="MT", nullable=False)
    remarks: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[str] = mapped_column(server_default="NOW()")
    updated_at: Mapped[str] = mapped_column(server_default="NOW()")
