from sqlalchemy import Integer, Numeric, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class PricingSheet(Base):
    __tablename__ = "pricing_sheets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ps_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"))
    salesperson_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    trade_terms: Mapped[str | None] = mapped_column(String(50))
    currency: Mapped[str] = mapped_column(String(10), default="USD", nullable=False)
    exchange_rate: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    # CIF 专用
    sea_freight: Mapped[float | None] = mapped_column(Numeric(12, 2))      # 海运费总额（USD/柜）
    tons_per_container: Mapped[float | None] = mapped_column(Numeric(10, 3))  # 单柜吨数
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)  # draft/confirmed/converted
    remarks: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)

    items: Mapped[list["PricingSheetItem"]] = relationship(
        back_populates="pricing_sheet", cascade="all, delete-orphan"
    )
    images: Mapped[list["PricingSheetImage"]] = relationship(
        back_populates="pricing_sheet", cascade="all, delete-orphan"
    )
    customer: Mapped["Customer"] = relationship(foreign_keys=[customer_id])  # type: ignore
    salesperson: Mapped["User"] = relationship(foreign_keys=[salesperson_id])  # type: ignore
    quotations: Mapped[list["Quotation"]] = relationship(  # type: ignore
        foreign_keys="[Quotation.pricing_sheet_id]", back_populates="pricing_sheet_ref"
    )


class PricingSheetImage(Base):
    """核价单附件图片（费用说明 / 海运费说明）"""
    __tablename__ = "pricing_sheet_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ps_id: Mapped[int] = mapped_column(ForeignKey("pricing_sheets.id", ondelete="CASCADE"), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False)  # cost_notes | freight_notes
    file_path: Mapped[str] = mapped_column(String(255), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    uploaded_at: Mapped[str] = mapped_column(String, nullable=False)

    pricing_sheet: Mapped["PricingSheet"] = relationship(back_populates="images")


class PricingSheetItem(Base):
    __tablename__ = "pricing_sheet_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ps_id: Mapped[int] = mapped_column(ForeignKey("pricing_sheets.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"))
    grade_label: Mapped[str | None] = mapped_column(String(50))
    hscode: Mapped[str | None] = mapped_column(String(20))
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(12, 3), nullable=False, default=1)
    unit: Mapped[str] = mapped_column(String(20), default="MT", nullable=False)
    # 成本拆分（CNY/吨）
    cost: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)          # 产品成本
    inland_freight: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0) # 陆运费
    packing_cost: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)   # 包装费
    port_charges: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)   # 港杂
    profit: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)          # 利润
    # 计算结果（外币/吨）
    calculated_price: Mapped[float | None] = mapped_column(Numeric(12, 4))
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    pricing_sheet: Mapped[PricingSheet] = relationship(back_populates="items")
