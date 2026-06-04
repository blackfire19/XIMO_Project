from pydantic import BaseModel
from typing import Optional
from datetime import date


# ---------- 公共 brief ----------
class CustomerBrief(BaseModel):
    id: int
    company_name: str
    country: str
    model_config = {"from_attributes": True}


class SalespersonBrief(BaseModel):
    id: int
    full_name: str
    model_config = {"from_attributes": True}


# ---------- 询价单文件 ----------
class InquiryFileOut(BaseModel):
    id: int
    inquiry_id: int
    doc_type: str           # pricing_sheet / pi / freight_quote
    version: int
    is_current: bool
    file_name: str
    file_path: str
    note: Optional[str] = None
    uploaded_by: int
    uploaded_at: str
    model_config = {"from_attributes": True}


# ---------- 询价单 ----------
class InquiryCreate(BaseModel):
    customer_id: int
    salesperson_id: Optional[int] = None   # 默认当前用户
    remarks: Optional[str] = None


class InquiryUpdate(BaseModel):
    remarks: Optional[str] = None


class InquiryDepositUpdate(BaseModel):
    deposit_amount: float
    deposit_date: Optional[date] = None


class InquiryListItem(BaseModel):
    id: int
    enq_number: str
    customer: CustomerBrief
    salesperson: SalespersonBrief
    status: str
    deposit_amount: Optional[float] = None
    deposit_date: Optional[date] = None
    created_at: str
    model_config = {"from_attributes": True}


class InquiryOut(BaseModel):
    id: int
    enq_number: str
    customer: CustomerBrief
    salesperson: SalespersonBrief
    status: str
    deposit_amount: Optional[float] = None
    deposit_date: Optional[date] = None
    remarks: Optional[str] = None
    created_at: str
    updated_at: str
    files: list[InquiryFileOut] = []
    formal_order_id: Optional[int] = None
    model_config = {"from_attributes": True}


# ---------- 正式订单文件 ----------
class OrderFileOut(BaseModel):
    id: int
    order_id: int
    doc_type: str           # mtc / pl / inspection / packing
    file_name: str
    file_path: str
    uploaded_by: int
    uploaded_at: str
    model_config = {"from_attributes": True}


# ---------- 集装箱 ----------
class ContainerCreate(BaseModel):
    container_type: Optional[str] = None
    container_number: Optional[str] = None
    seal_number: Optional[str] = None


class ContainerOut(ContainerCreate):
    id: int
    bl_id: int
    model_config = {"from_attributes": True}


# ---------- 提单 BL ----------
class BLCreate(BaseModel):
    ship_type: str = "container"      # container / bulk
    bl_number: Optional[str] = None
    vessel_voyage: Optional[str] = None
    container_info: Optional[str] = None
    load_port: Optional[str] = None
    discharge_port: Optional[str] = None
    etd: Optional[date] = None
    eta: Optional[date] = None
    # 散货船字段
    pieces: Optional[int] = None
    weight_mt: Optional[float] = None
    volume_cbm: Optional[float] = None
    remarks: Optional[str] = None
    containers: list[ContainerCreate] = []


class BLUpdate(BaseModel):
    ship_type: Optional[str] = None
    bl_number: Optional[str] = None
    vessel_voyage: Optional[str] = None
    container_info: Optional[str] = None
    load_port: Optional[str] = None
    discharge_port: Optional[str] = None
    etd: Optional[date] = None
    eta: Optional[date] = None
    status: Optional[str] = None
    pieces: Optional[int] = None
    weight_mt: Optional[float] = None
    volume_cbm: Optional[float] = None
    remarks: Optional[str] = None


class BLOut(BaseModel):
    id: int
    order_id: int
    ship_type: str
    bl_number: Optional[str] = None
    vessel_voyage: Optional[str] = None
    container_info: Optional[str] = None
    load_port: Optional[str] = None
    discharge_port: Optional[str] = None
    etd: Optional[date] = None
    eta: Optional[date] = None
    status: str
    pieces: Optional[int] = None
    weight_mt: Optional[float] = None
    volume_cbm: Optional[float] = None
    remarks: Optional[str] = None
    created_at: str
    updated_at: str
    containers: list[ContainerOut] = []
    model_config = {"from_attributes": True}


# ---------- 正式订单 ----------
class FormalOrderCreate(BaseModel):
    inquiry_id: int
    is_stock: bool = True
    est_production_date: Optional[date] = None
    remarks: Optional[str] = None


class FormalOrderUpdate(BaseModel):
    is_stock: Optional[bool] = None
    est_production_date: Optional[date] = None
    remarks: Optional[str] = None


class FormalOrderStatusUpdate(BaseModel):
    status: str   # confirmed / production / ready / shipping / completed


class FormalOrderListItem(BaseModel):
    id: int
    so_number: str
    customer: CustomerBrief
    salesperson: SalespersonBrief
    is_stock: bool
    est_production_date: Optional[date] = None
    status: str
    created_at: str
    model_config = {"from_attributes": True}


class FormalOrderOut(BaseModel):
    id: int
    so_number: str
    inquiry_id: int
    customer: CustomerBrief
    salesperson: SalespersonBrief
    is_stock: bool
    est_production_date: Optional[date] = None
    status: str
    remarks: Optional[str] = None
    created_at: str
    updated_at: str
    files: list[OrderFileOut] = []
    bls: list[BLOut] = []
    inquiry_files: list[InquiryFileOut] = []
    model_config = {"from_attributes": True}
