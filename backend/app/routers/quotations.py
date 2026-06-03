from fastapi import APIRouter

router = APIRouter(prefix="/quotations", tags=["询报价"])


@router.get("/")
def list_quotations():
    pass


@router.post("/")
def create_quotation():
    pass


@router.get("/{quotation_id}")
def get_quotation(quotation_id: int):
    pass


@router.put("/{quotation_id}")
def update_quotation(quotation_id: int):
    pass


@router.post("/{quotation_id}/generate-pi")
def generate_pi(quotation_id: int):
    # TODO: 生成 PI PDF（客户版/内部版，4语言）
    pass


@router.post("/{quotation_id}/convert-to-order")
def convert_to_order(quotation_id: int):
    # TODO: 一键转单，复制产品行快照
    pass
