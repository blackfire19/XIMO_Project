"""
初始化种子数据：创建角色 + 超级管理员账号
用法：在 backend/ 目录下执行
    python -m scripts.seed_data
默认超管账号：admin / admin123（首次部署后请立即修改密码）
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import SessionLocal
import app.models  # 确保所有模型都注册到 SQLAlchemy
from app.models.user import Role, User
from app.core.security import hash_password

ROLES = [
    {"name": "super_admin", "label": "超级管理员"},
    {"name": "boss",        "label": "老板"},
    {"name": "salesperson", "label": "业务员"},
    {"name": "purchaser",   "label": "采购员"},
]

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"
ADMIN_FULLNAME = "超级管理员"


def seed():
    db = SessionLocal()
    try:
        # 插入角色（已存在则跳过）
        role_map = {}
        for r in ROLES:
            role = db.query(Role).filter(Role.name == r["name"]).first()
            if not role:
                role = Role(name=r["name"], label=r["label"])
                db.add(role)
                db.flush()
                print(f"  创建角色：{r['label']}")
            else:
                print(f"  角色已存在：{r['label']}")
            role_map[r["name"]] = role

        db.commit()

        # 创建超管账号
        existing = db.query(User).filter(User.username == ADMIN_USERNAME).first()
        if not existing:
            admin = User(
                username=ADMIN_USERNAME,
                password_hash=hash_password(ADMIN_PASSWORD),
                full_name=ADMIN_FULLNAME,
                role_id=role_map["super_admin"].id,
                is_active=True,
            )
            db.add(admin)
            db.commit()
            print(f"\n  超管账号已创建：{ADMIN_USERNAME} / {ADMIN_PASSWORD}")
            print("  请登录后立即修改密码！")
        else:
            print(f"\n  超管账号已存在：{ADMIN_USERNAME}")

    finally:
        db.close()


if __name__ == "__main__":
    print("开始初始化种子数据...")
    seed()
    print("完成。")
