from fastapi import APIRouter

router = APIRouter(prefix="/dashboard", tags=["首页看板"])


@router.get("/boss")
def boss_dashboard():
    # TODO: 今日全员跟进、进行中订单、本月出运计划
    pass


@router.get("/salesperson")
def salesperson_dashboard():
    # TODO: 今日应跟进客户、我的进行中订单
    pass
