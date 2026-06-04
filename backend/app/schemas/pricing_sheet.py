from pydantic import BaseModel
from typing import Optional


class PricingSheetItemCreate(BaseModel):
    product_id: Optional[int] = None
    grade_label: Optional[str] = None
    hscode: Optional[str] = None
    description: str
    quantity: float = 1
    unit: str = "MT"
    cost: float = 0           # 成本 CNY/吨
    inland_freight: float = 0  # 陆运费 CNY/吨
    packing_cost: float = 0    # 包装费 CNY/吨
    port_charges: float = 0    # 港杂 CNY/吨
    profit: float = 0          # 利润 CNY/吨
    sort_order: int = 0


class PricingSheetCreate(BaseModel):
    customer_id: Optional[int] = None
    trade_terms: Optional[str] = None
    currency: str = "USD"
    exchange_rate: float
    sea_freight: Optional[float] = None       # 海运费 USD/柜（CIF用）
    tons_per_container: Optional[float] = None # 单柜吨数（CIF用）
    remarks: Optional[str] = None
    items: list[PricingSheetItemCreate] = []


class PricingSheetUpdate(BaseModel):
    customer_id: Optional[int] = None
    trade_terms: Optional[str] = None
    currency: Optional[str] = None
    exchange_rate: Optional[float] = None
    sea_freight: Optional[float] = None
    tons_per_container: Optional[float] = None
    remarks: Optional[str] = None
    items: Optional[list[PricingSheetItemCreate]] = None


class PricingSheetItemOut(BaseModel):
    id: int
    product_id: Optional[int] = None
    grade_label: Optional[str] = None
    hscode: Optional[str] = None
    description: str
    quantity: float
    unit: str
    cost: float
    inland_freight: float
    packing_cost: float
    port_charges: float
    profit: float
    calculated_price: Optional[float] = None
    sort_order: int
    model_config = {"from_attributes": True}


class CustomerBrief(BaseModel):
    id: int
    company_name: str
    country: str
    model_config = {"from_attributes": True}


class SalespersonBrief(BaseModel):
    id: int
    full_name: str
    model_config = {"from_attributes": True}


class PricingSheetImageOut(BaseModel):
    id: int
    category: str
    file_path: str
    file_name: str
    uploaded_at: str
    model_config = {"from_attributes": True}


class PiRef(BaseModel):
    id: int
    pi_number: str
    status: str
    model_config = {"from_attributes": True}


class PricingSheetOut(BaseModel):
    id: int
    ps_number: str
    customer: Optional[CustomerBrief] = None
    salesperson: SalespersonBrief
    trade_terms: Optional[str] = None
    currency: str
    exchange_rate: float
    sea_freight: Optional[float] = None
    tons_per_container: Optional[float] = None
    status: str
    remarks: Optional[str] = None
    created_at: str
    updated_at: str
    items: list[PricingSheetItemOut] = []
    images: list[PricingSheetImageOut] = []
    quotations: list[PiRef] = []
    model_config = {"from_attributes": True}


class PricingSheetListItem(BaseModel):
    id: int
    ps_number: str
    customer: Optional[CustomerBrief] = None
    salesperson: SalespersonBrief
    trade_terms: Optional[str] = None
    currency: str
    exchange_rate: float
    status: str
    created_at: str
    model_config = {"from_attributes": True}
