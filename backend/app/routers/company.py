from fastapi import APIRouter

router = APIRouter(prefix="/company", tags=["公司信息"])


@router.get("/")
def get_company_info():
    pass


@router.put("/")
def update_company_info():
    # TODO: 超管专属，支持 Logo 上传
    pass
