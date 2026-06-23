from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import os

from app.config import settings
from app.routers import auth, users, customers, products, announcements, dashboard, inquiries, formal_orders, evaluations, accounting

app = FastAPI(title="XIMOSteel API", version="1.0.0")


# 安全可预览类型：图片与 PDF 允许浏览器内联渲染（点击在线查看）；
# 其余类型（尤其 HTML/SVG 等可执行脚本的文件）仍强制下载以防 XSS。
INLINE_VIEW_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}


class ForceDownloadMiddleware(BaseHTTPMiddleware):
    """为 /uploads/ 路径下的静态文件设置 Content-Disposition：
    图片/PDF 用 inline 支持在线查看，其余强制 attachment 下载，防止浏览器渲染 HTML/SVG 造成 XSS。"""
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/uploads/"):
            ext = os.path.splitext(request.url.path)[1].lower()
            disposition = "inline" if ext in INLINE_VIEW_EXTENSIONS else "attachment"
            response.headers["Content-Disposition"] = disposition
        return response


app.add_middleware(ForceDownloadMiddleware)
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
app.include_router(inquiries.router, prefix="/api")
app.include_router(formal_orders.router, prefix="/api")
app.include_router(announcements.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(evaluations.router, prefix="/api")
app.include_router(accounting.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}
