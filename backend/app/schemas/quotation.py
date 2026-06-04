from pydantic import BaseModel
from typing import Optional
from datetime import date


class QuotationItemCreate(BaseModel):
    product_id: Optional[int] = None
    grade_label: Optional[str] = None
    hscode: Optional[str] = None
    description: str
    quantity: float
    unit: str = "MT"
    unit_price: float
    unit_price_internal: Optional[float] = None
    sort_order: int = 0


class QuotationCreate(BaseModel):
    customer_id: int
    currency: str = "USD"
    exchange_rate: Optional[float] = None
    trade_terms: Optional[str] = None
    delivery_date: Optional[date] = None
    valid_until: Optional[date] = None
    remarks: Optional[str] = None
    contact_person: Optional[str] = None
    payment_terms: Optional[str] = None
    commodity: Optional[str] = None
    packing: Optional[str] = "EXPORT STANDARD"
    port_of_loading: Optional[str] = None
    destination_port: Optional[str] = None
    note_pi: Optional[str] = None
    items: list[QuotationItemCreate] = []


class QuotationUpdate(BaseModel):
    customer_id: Optional[int] = None
    currency: Optional[str] = None
    exchange_rate: Optional[float] = None
    trade_terms: Optional[str] = None
    delivery_date: Optional[date] = None
    valid_until: Optional[date] = None
    remarks: Optional[str] = None
    contact_person: Optional[str] = None
    payment_terms: Optional[str] = None
    commodity: Optional[str] = None
    packing: Optional[str] = None
    port_of_loading: Optional[str] = None
    destination_port: Optional[str] = None
    note_pi: Optional[str] = None
    items: Optional[list[QuotationItemCreate]] = None


class QuotationItemOut(BaseModel):
    id: int
    product_id: Optional[int] = None
    grade_label: Optional[str] = None
    hscode: Optional[str] = None
    description: str
    quantity: float
    unit: str
    unit_price: float
    unit_price_internal: Optional[float] = None
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


class QuotationOut(BaseModel):
    id: int
    pi_number: str
    pricing_sheet_id: Optional[int] = None
    customer: CustomerBrief
    salesperson: SalespersonBrief
    currency: str
    exchange_rate: Optional[float] = None
    trade_terms: Optional[str] = None
    delivery_date: Optional[date] = None
    valid_until: Optional[date] = None
    status: str
    remarks: Optional[str] = None
    contact_person: Optional[str] = None
    payment_terms: Optional[str] = None
    commodity: Optional[str] = None
    packing: Optional[str] = None
    port_of_loading: Optional[str] = None
    destination_port: Optional[str] = None
    note_pi: Optional[str] = None
    created_at: str
    updated_at: str
    items: list[QuotationItemOut] = []
    model_config = {"from_attributes": True}


class QuotationListItem(BaseModel):
    id: int
    pi_number: str
    pricing_sheet_id: Optional[int] = None
    customer: CustomerBrief
    salesperson: SalespersonBrief
    currency: str
    trade_terms: Optional[str] = None
    delivery_date: Optional[date] = None
    valid_until: Optional[date] = None
    status: str
    created_at: str
    model_config = {"from_attributes": True}
