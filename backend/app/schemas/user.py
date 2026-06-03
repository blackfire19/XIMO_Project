import re
from pydantic import BaseModel, field_validator


class UserCreate(BaseModel):
    username: str
    password: str
    full_name: str
    role_id: int
    salesperson_code: str | None = None

    @field_validator("salesperson_code")
    @classmethod
    def validate_code(cls, v):
        if v is not None:
            v = v.strip().upper()
            if not re.fullmatch(r"[A-Z0-9]+", v):
                raise ValueError("业务员编码只能包含大写字母和数字")
        return v or None


class UserUpdate(BaseModel):
    full_name: str | None = None
    role_id: int | None = None
    salesperson_code: str | None = None
    password: str | None = None

    @field_validator("salesperson_code")
    @classmethod
    def validate_code(cls, v):
        if v is not None and v != "":
            v = v.strip().upper()
            if not re.fullmatch(r"[A-Z0-9]+", v):
                raise ValueError("业务员编码只能包含大写字母和数字")
            return v
        return None


class RoleOut(BaseModel):
    id: int
    name: str
    label: str

    model_config = {"from_attributes": True}


class UserOut(BaseModel):
    id: int
    username: str
    full_name: str
    role: RoleOut
    salesperson_code: str | None
    is_active: bool
    created_at: str

    model_config = {"from_attributes": True}
