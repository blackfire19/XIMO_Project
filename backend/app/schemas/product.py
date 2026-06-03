from datetime import date
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel

WarehouseType = Literal["南货场", "图片小管", "库存货场"]


class ProductOut(BaseModel):
    id: int
    spec: str
    material: str
    product_type: str
    manufacturer: str | None
    warehouse: str
    length: str | None
    unit_price: Decimal | None
    weight_ton: Decimal | None
    quantity_pcs: int | None
    remark: str | None
    price_updated_at: date | None

    model_config = {"from_attributes": True}


class ProductImportRow(BaseModel):
    spec: str
    material: str
    product_type: str = "无缝钢管"
    manufacturer: str | None = None
    length: str | None = None
    unit_price: Decimal | None = None
    weight_ton: Decimal | None = None
    quantity_pcs: int | None = None
    remark: str | None = None
