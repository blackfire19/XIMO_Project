from fastapi import APIRouter

router = APIRouter(prefix="/products", tags=["产品库"])


@router.get("/")
def list_products():
    pass


@router.post("/")
def create_product():
    pass


@router.put("/{product_id}")
def update_product(product_id: int):
    pass


@router.post("/import")
def import_products():
    # TODO: Excel 批量导入（采购员专属）
    pass
