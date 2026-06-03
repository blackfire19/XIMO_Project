from sqlalchemy import Date, Integer, Numeric, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    spec: Mapped[str] = mapped_column(String(50), nullable=False)          # 规格，如 63.5*12
    material: Mapped[str] = mapped_column(String(50), nullable=False)      # 材质，如 20#
    product_type: Mapped[str] = mapped_column(String(50), nullable=False, default="无缝钢管")
    manufacturer: Mapped[str | None] = mapped_column(String(100))          # 厂家
    warehouse: Mapped[str] = mapped_column(String(20), nullable=False)     # 南货场 / 图片小管 / 库存货场
    length: Mapped[str | None] = mapped_column(String(50))                 # 长度，如 5.7-6
    unit_price: Mapped[float | None] = mapped_column(Numeric(12, 2))       # 单价（元/吨）
    weight_ton: Mapped[float | None] = mapped_column(Numeric(10, 3))       # 吨数
    quantity_pcs: Mapped[int | None] = mapped_column(Integer)              # 支数
    remark: Mapped[str | None] = mapped_column(Text)                       # 备注
    price_updated_at: Mapped[str | None] = mapped_column(Date)             # 价格更新日期
    created_at: Mapped[str] = mapped_column(server_default="NOW()")
