from sqlalchemy import Date, Integer, Numeric, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Quotation(Base):
    __tablename__ = "quotations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pi_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    pricing_sheet_id: Mapped[int | None] = mapped_column(ForeignKey("pricing_sheets.id"))
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)
    salesperson_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="USD", nullable=False)
    exchange_rate: Mapped[float | None] = mapped_column(Numeric(10, 4))
    trade_terms: Mapped[str | None] = mapped_column(String(50))
    delivery_date: Mapped[str | None] = mapped_column(Date)
    valid_until: Mapped[str | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    remarks: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[str] = mapped_column(server_default="NOW()")
    updated_at: Mapped[str] = mapped_column(server_default="NOW()")

    contact_person: Mapped[str | None] = mapped_column(String(100))
    payment_terms: Mapped[str | None] = mapped_column(Text)
    commodity: Mapped[str | None] = mapped_column(String(200))
    packing: Mapped[str | None] = mapped_column(String(100), default="EXPORT STANDARD")
    port_of_loading: Mapped[str | None] = mapped_column(String(200))
    destination_port: Mapped[str | None] = mapped_column(String(200))
    note_pi: Mapped[str | None] = mapped_column(Text)

    items: Mapped[list["QuotationItem"]] = relationship(back_populates="quotation", cascade="all, delete-orphan")
    customer: Mapped["Customer"] = relationship(foreign_keys=[customer_id])  # type: ignore
    salesperson: Mapped["User"] = relationship(foreign_keys=[salesperson_id])  # type: ignore
    pricing_sheet_ref: Mapped["PricingSheet | None"] = relationship(  # type: ignore
        foreign_keys=[pricing_sheet_id], back_populates="quotations"
    )


class QuotationItem(Base):
    __tablename__ = "quotation_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    quotation_id: Mapped[int] = mapped_column(ForeignKey("quotations.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"))
    grade_label: Mapped[str | None] = mapped_column(String(50))
    hscode: Mapped[str | None] = mapped_column(String(20))
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(12, 3), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), default="MT", nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    unit_price_internal: Mapped[float | None] = mapped_column(Numeric(12, 2))
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    quotation: Mapped[Quotation] = relationship(back_populates="items")
