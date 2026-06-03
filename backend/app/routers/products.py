from datetime import date
from decimal import Decimal, InvalidOperation
from io import BytesIO
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.database import get_db
from app.models.product import Product
from app.models.user import User
from app.schemas.product import ProductOut, WarehouseType

router = APIRouter(prefix="/products", tags=["产品库"])


def _to_decimal(val) -> Decimal | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    try:
        return Decimal(str(val))
    except InvalidOperation:
        return None


def _to_int(val) -> int | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def _to_str(val) -> str | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    s = str(val).strip()
    return s if s else None


def _make_row(spec: str, material: str, ton_val, pcs_val, price_val, length_val) -> dict | None:
    ton = _to_decimal(ton_val)
    pcs = _to_int(pcs_val)
    if not ton and not pcs:
        return None
    return dict(
        spec=spec, material=material, product_type="无缝钢管",
        manufacturer=None, length=_to_str(length_val),
        unit_price=_to_decimal(price_val), weight_ton=ton, quantity_pcs=pcs,
        remark=None,
    )


def _parse_nanhuochang(content: bytes) -> list[dict]:
    df = pd.read_excel(BytesIO(content), sheet_name="南货场", header=None)
    rows = []
    for i in range(2, len(df)):
        row = df.iloc[i]

        spec1 = _to_str(row.iloc[0])
        if not spec1:
            continue

        for material, offset in (("20#", 1), ("45#", 5)):
            r = _make_row(spec1, material,
                          row.iloc[offset], row.iloc[offset+1],
                          row.iloc[offset+2], row.iloc[offset+3])
            if r:
                rows.append(r)

        if len(row) > 9:
            spec2 = _to_str(row.iloc[9])
            if spec2:
                for material, offset in (("20#", 10), ("45#", 14)):
                    if len(row) > offset:
                        r = _make_row(spec2, material,
                                      row.iloc[offset] if len(row) > offset else None,
                                      row.iloc[offset+1] if len(row) > offset+1 else None,
                                      row.iloc[offset+2] if len(row) > offset+2 else None,
                                      row.iloc[offset+3] if len(row) > offset+3 else None)
                        if r:
                            rows.append(r)
    return rows


def _parse_xiaoguan(content: bytes) -> list[dict]:
    df = pd.read_excel(BytesIO(content), header=None)
    rows = []
    for _, row in df.iterrows():
        for mat_col, spec_col, ton_col, len_col in ((0, 1, 2, 3), (4, 5, 6, 7)):
            if len(row) <= spec_col:
                continue
            spec = _to_str(row.iloc[spec_col])
            ton = _to_decimal(row.iloc[ton_col] if len(row) > ton_col else None)
            length = _to_str(row.iloc[len_col] if len(row) > len_col else None)
            if spec and (ton or length):
                rows.append(dict(
                    spec=spec,
                    material=_to_str(row.iloc[mat_col]) or "20#",
                    product_type="无缝钢管",
                    manufacturer=None, length=length,
                    unit_price=None, weight_ton=ton, quantity_pcs=None,
                    remark=None,
                ))
    return rows


def _parse_kucun(content: bytes) -> list[dict]:
    df = pd.read_excel(BytesIO(content), header=0, engine="xlrd")
    rows = []
    for _, row in df.iterrows():
        spec = _to_str(row.iloc[4])
        if not spec:
            continue
        rows.append(dict(
            spec=spec,
            material=_to_str(row.iloc[2]) or "20#",
            product_type=_to_str(row.iloc[3]) or "无缝钢管",
            manufacturer=_to_str(row.iloc[6]),
            length=None,
            unit_price=_to_decimal(row.iloc[5]),
            weight_ton=_to_decimal(row.iloc[7]),
            quantity_pcs=_to_int(row.iloc[8]),
            remark=None,
        ))
    return rows


PARSERS = {
    "南货场": _parse_nanhuochang,
    "图片小管": _parse_xiaoguan,
    "库存货场": _parse_kucun,
}


@router.get("/", response_model=list[ProductOut])
def list_products(
    warehouse: Optional[str] = Query(None),
    material: Optional[str] = Query(None),
    spec: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(Product)
    if warehouse:
        q = q.filter(Product.warehouse == warehouse)
    if material:
        q = q.filter(Product.material == material)
    if spec:
        q = q.filter(Product.spec.ilike(f"%{spec}%"))
    return q.order_by(Product.unit_price.asc().nullslast(), Product.warehouse, Product.spec).all()


@router.post("/import/{warehouse}", summary="上传文件全量替换指定仓库数据")
def import_products(
    warehouse: WarehouseType,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("super_admin", "boss", "purchaser")),
):
    content = file.file.read()
    try:
        rows = PARSERS[warehouse](content)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"文件解析失败：{e}")

    if not rows:
        raise HTTPException(status_code=422, detail="文件中未解析到有效数据，请检查格式")

    today = date.today()
    try:
        db.query(Product).filter(Product.warehouse == warehouse).delete()
        db.bulk_insert_mappings(Product, [
            {**row, "warehouse": warehouse, "price_updated_at": today}
            for row in rows
        ])
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"写入数据库失败：{e}")

    return {"imported": len(rows), "warehouse": warehouse, "price_updated_at": str(today)}
