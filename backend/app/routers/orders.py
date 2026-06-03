from fastapi import APIRouter

router = APIRouter(prefix="/orders", tags=["订单管理"])


@router.get("/")
def list_orders():
    pass


@router.get("/{order_id}")
def get_order(order_id: int):
    pass


@router.put("/{order_id}/status")
def update_order_status(order_id: int):
    pass


@router.post("/{order_id}/shipments")
def add_shipment(order_id: int):
    pass


@router.put("/{order_id}/shipments/{shipment_id}")
def update_shipment(order_id: int, shipment_id: int):
    pass


@router.post("/{order_id}/generate-ci")
def generate_ci(order_id: int):
    # TODO: 生成 CI PDF（客户版/内部版，4语言）
    pass


@router.post("/{order_id}/generate-pl")
def generate_pl(order_id: int):
    # TODO: 生成 PL PDF
    pass


@router.post("/{order_id}/attachments")
def upload_attachment(order_id: int):
    pass


@router.get("/{order_id}/attachments")
def list_attachments(order_id: int):
    pass
