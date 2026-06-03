from sqlalchemy import Date, Integer, Numeric, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    so_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    quotation_id: Mapped[int | None] = mapped_column(ForeignKey("quotations.id"))
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)
    salesperson_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="USD", nullable=False)
    exchange_rate: Mapped[float | None] = mapped_column(Numeric(10, 4))
    trade_terms: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(30), default="confirmed", nullable=False)
    est_ready_date: Mapped[str | None] = mapped_column(Date)
    remarks: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[str] = mapped_column(server_default="NOW()")
    updated_at: Mapped[str] = mapped_column(server_default="NOW()")

    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")
    shipments: Mapped[list["Shipment"]] = relationship(back_populates="order")  # type: ignore


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"))
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(12, 3), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), default="MT", nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    unit_price_internal: Mapped[float | None] = mapped_column(Numeric(12, 2))
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    order: Mapped[Order] = relationship(back_populates="items")
