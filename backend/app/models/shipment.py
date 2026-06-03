from sqlalchemy import Date, Integer, Numeric, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Shipment(Base):
    __tablename__ = "shipments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    ship_type: Mapped[str] = mapped_column(String(20), nullable=False)  # container / bulk
    vessel_voyage: Mapped[str | None] = mapped_column(String(100))
    etd: Mapped[str | None] = mapped_column(Date)
    eta: Mapped[str | None] = mapped_column(Date)
    bl_number: Mapped[str | None] = mapped_column(String(100))
    # 集装箱专用
    container_type: Mapped[str | None] = mapped_column(String(20))
    container_number: Mapped[str | None] = mapped_column(String(50))
    seal_number: Mapped[str | None] = mapped_column(String(50))
    # 散货船专用
    weight_mt: Mapped[float | None] = mapped_column(Numeric(12, 3))
    status: Mapped[str] = mapped_column(String(20), default="planned", nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[str] = mapped_column(server_default="NOW()")
    updated_at: Mapped[str] = mapped_column(server_default="NOW()")

    order: Mapped["Order"] = relationship(back_populates="shipments")  # type: ignore
