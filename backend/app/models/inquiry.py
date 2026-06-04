from sqlalchemy import Boolean, Date, Integer, Numeric, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Inquiry(Base):
    __tablename__ = "inquiries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    enq_number: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)
    salesperson_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    # active / deposit_received / converted / void
    deposit_amount: Mapped[float | None] = mapped_column(Numeric(14, 2))
    deposit_date: Mapped[str | None] = mapped_column(Date)
    remarks: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[str] = mapped_column(server_default="NOW()")
    updated_at: Mapped[str] = mapped_column(server_default="NOW()")

    customer: Mapped["Customer"] = relationship(foreign_keys=[customer_id])  # type: ignore
    salesperson: Mapped["User"] = relationship(foreign_keys=[salesperson_id])  # type: ignore
    files: Mapped[list["InquiryFile"]] = relationship(back_populates="inquiry", cascade="all, delete-orphan")
    formal_order: Mapped["FormalOrder | None"] = relationship(back_populates="inquiry")  # type: ignore

    @property
    def formal_order_id(self) -> int | None:
        return self.formal_order.id if self.formal_order else None


class InquiryFile(Base):
    """核价单 / PI / 货代报价——每种文件可多版本，当前版本 is_current=True"""
    __tablename__ = "inquiry_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    inquiry_id: Mapped[int] = mapped_column(ForeignKey("inquiries.id", ondelete="CASCADE"), nullable=False)
    doc_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # pricing_sheet / pi / freight_quote
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    note: Mapped[str | None] = mapped_column(String(200))
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    uploaded_at: Mapped[str] = mapped_column(server_default="NOW()")

    inquiry: Mapped[Inquiry] = relationship(back_populates="files")


class FormalOrder(Base):
    __tablename__ = "formal_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    so_number: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    inquiry_id: Mapped[int] = mapped_column(ForeignKey("inquiries.id"), nullable=False)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)
    salesperson_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    is_stock: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    est_production_date: Mapped[str | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="confirmed", nullable=False)
    # confirmed / production / ready / shipping / completed
    remarks: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[str] = mapped_column(server_default="NOW()")
    updated_at: Mapped[str] = mapped_column(server_default="NOW()")

    inquiry: Mapped[Inquiry] = relationship(back_populates="formal_order")
    customer: Mapped["Customer"] = relationship(foreign_keys=[customer_id])  # type: ignore
    salesperson: Mapped["User"] = relationship(foreign_keys=[salesperson_id])  # type: ignore
    files: Mapped[list["OrderFile"]] = relationship(back_populates="order", cascade="all, delete-orphan")
    bls: Mapped[list["ShipmentBL"]] = relationship(back_populates="order", cascade="all, delete-orphan")

    @property
    def inquiry_files(self) -> list["InquiryFile"]:
        """关联询价单中核价单 / PI 的当前版本，便于订单页直接查看"""
        if not self.inquiry:
            return []
        return [
            f for f in self.inquiry.files
            if f.is_current and f.doc_type in ("pricing_sheet", "pi")
        ]


class OrderFile(Base):
    """MTC / PL / 验货照片 / 装箱照片"""
    __tablename__ = "order_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("formal_orders.id", ondelete="CASCADE"), nullable=False)
    doc_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # mtc / pl / inspection / packing
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    uploaded_at: Mapped[str] = mapped_column(server_default="NOW()")

    order: Mapped[FormalOrder] = relationship(back_populates="files")


class ShipmentBL(Base):
    """一张提单（BL），下挂多个集装箱；散货船时无集装箱记录件数/重量/体积"""
    __tablename__ = "shipment_bls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("formal_orders.id", ondelete="CASCADE"), nullable=False)
    ship_type: Mapped[str] = mapped_column(String(20), default="container", nullable=False)
    # container / bulk
    bl_number: Mapped[str | None] = mapped_column(String(80))
    vessel_voyage: Mapped[str | None] = mapped_column(String(120))
    container_info: Mapped[str | None] = mapped_column(String(200))   # 箱型箱量，如 20GP*2、40HC*1
    load_port: Mapped[str | None] = mapped_column(String(120))      # 起运港
    discharge_port: Mapped[str | None] = mapped_column(String(120))  # 目的港
    etd: Mapped[str | None] = mapped_column(Date)
    eta: Mapped[str | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="planned", nullable=False)
    # planned / loaded / transit / arrived
    # 散货船字段
    pieces: Mapped[int | None] = mapped_column(Integer)
    weight_mt: Mapped[float | None] = mapped_column(Numeric(12, 3))
    volume_cbm: Mapped[float | None] = mapped_column(Numeric(12, 3))
    remarks: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(server_default="NOW()")
    updated_at: Mapped[str] = mapped_column(server_default="NOW()")

    order: Mapped[FormalOrder] = relationship(back_populates="bls")
    containers: Mapped[list["ShipmentContainer"]] = relationship(back_populates="bl", cascade="all, delete-orphan")


class ShipmentContainer(Base):
    """集装箱，隶属于一张 BL"""
    __tablename__ = "shipment_containers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bl_id: Mapped[int] = mapped_column(ForeignKey("shipment_bls.id", ondelete="CASCADE"), nullable=False)
    container_type: Mapped[str | None] = mapped_column(String(20))  # 20GP / 40HC etc.
    container_number: Mapped[str | None] = mapped_column(String(50))
    seal_number: Mapped[str | None] = mapped_column(String(50))

    bl: Mapped[ShipmentBL] = relationship(back_populates="containers")
