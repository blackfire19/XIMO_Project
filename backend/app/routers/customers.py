from fastapi import APIRouter

router = APIRouter(prefix="/customers", tags=["客户管理"])


@router.get("/")
def list_customers():
    # TODO: 列表（业务员只见自己，老板全见）
    pass


@router.post("/")
def create_customer():
    pass


@router.get("/{customer_id}")
def get_customer(customer_id: int):
    pass


@router.put("/{customer_id}")
def update_customer(customer_id: int):
    pass


@router.get("/{customer_id}/follow-ups")
def list_follow_ups(customer_id: int):
    pass


@router.post("/{customer_id}/follow-ups")
def create_follow_up(customer_id: int):
    # TODO: 支持多图上传
    pass
