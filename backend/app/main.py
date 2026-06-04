from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.config import settings
from app.routers import auth, users, customers, products, quotations, pricing_sheets, orders, announcements, dashboard, inquiries, formal_orders

app = FastAPI(title="XIMOSteel API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://192.168.1.72:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件（上传的附件/图片）
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# 注册路由
app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(customers.router, prefix="/api")
app.include_router(products.router, prefix="/api")
app.include_router(quotations.router, prefix="/api")
app.include_router(pricing_sheets.router, prefix="/api")
app.include_router(orders.router, prefix="/api")
app.include_router(inquiries.router, prefix="/api")
app.include_router(formal_orders.router, prefix="/api")
app.include_router(announcements.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}
