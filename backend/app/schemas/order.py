from pydantic import BaseModel
from typing import Optional
from datetime import date


class OrderItemOut(BaseModel):
    id: int
    product_id: Optional[int] = None
    description: str
    quantity: float
    unit: str
    unit_price: float
    unit_price_internal: Optional[float] = None
    sort_order: int
    model_config = {"from_attributes": True}


class ShipmentCreate(BaseModel):
    ship_type: str = "container"
    container_type: Optional[str] = None
    container_number: Optional[str] = None
    seal_number: Optional[str] = None
    vessel_voyage: Optional[str] = None
    etd: Optional[date] = None
    eta: Optional[date] = None
    bl_number: Optional[str] = None
    weight_mt: Optional[float] = None
    remarks: Optional[str] = None


class ShipmentUpdate(ShipmentCreate):
    status: Optional[str] = None


class ShipmentOut(BaseModel):
    id: int
    order_id: int
    ship_type: str
    status: str
    container_type: Optional[str] = None
    container_number: Optional[str] = None
    seal_number: Optional[str] = None
    vessel_voyage: Optional[str] = None
    etd: Optional[date] = None
    eta: Optional[date] = None
    bl_number: Optional[str] = None
    weight_mt: Optional[float] = None
    remarks: Optional[str] = None
    created_at: str
    updated_at: str
    model_config = {"from_attributes": True}


class OrderAttachmentOut(BaseModel):
    id: int
    order_id: int
    doc_type: str
    file_name: str
    file_path: str
    uploaded_by: int
    uploaded_at: str
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


class OrderStatusUpdate(BaseModel):
    status: str
    est_ready_date: Optional[date] = None


class OrderOut(BaseModel):
    id: int
    so_number: str
    quotation_id: Optional[int] = None
    customer: CustomerBrief
    salesperson: SalespersonBrief
    currency: str
    exchange_rate: Optional[float] = None
    trade_terms: Optional[str] = None
    status: str
    est_ready_date: Optional[date] = None
    remarks: Optional[str] = None
    created_at: str
    updated_at: str
    items: list[OrderItemOut] = []
    shipments: list[ShipmentOut] = []
    attachments: list[OrderAttachmentOut] = []
    model_config = {"from_attributes": True}


class OrderListItem(BaseModel):
    id: int
    so_number: str
    customer: CustomerBrief
    salesperson: SalespersonBrief
    currency: str
    trade_terms: Optional[str] = None
    status: str
    est_ready_date: Optional[date] = None
    created_at: str
    model_config = {"from_attributes": True}
