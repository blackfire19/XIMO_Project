from pydantic import BaseModel
from typing import Optional


class CustomerCreate(BaseModel):
    company_name: str
    country: str
    contact_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    trade_terms: Optional[str] = None
    payment_terms: Optional[str] = None
    grade: str = "potential"


class CustomerUpdate(BaseModel):
    company_name: Optional[str] = None
    country: Optional[str] = None
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    trade_terms: Optional[str] = None
    payment_terms: Optional[str] = None
    grade: Optional[str] = None


class FreqUpgradeBody(BaseModel):
    freq: str  # "daily" | "weekly"


class OwnerOut(BaseModel):
    id: int
    full_name: str
    model_config = {"from_attributes": True}


class CustomerOut(BaseModel):
    id: int
    company_name: str
    country: str
    contact_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    trade_terms: Optional[str] = None
    payment_terms: Optional[str] = None
    grade: str
    follow_freq: str
    consecutive_miss_cycles: int
    is_active: bool
    created_at: str
    owner: OwnerOut
    model_config = {"from_attributes": True}


class FollowUpImageOut(BaseModel):
    id: int
    file_path: str
    file_name: str
    model_config = {"from_attributes": True}


class FollowUpOut(BaseModel):
    id: int
    content: str
    is_effective: bool
    created_by: int
    created_at: str
    images: list[FollowUpImageOut] = []
    model_config = {"from_attributes": True}
