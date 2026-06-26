"""normalize legacy so_number to XIMO{code}{date}{seq}

把历史订单编号从旧格式 `SO-XIMO{code}{YYYYMMDD}-{seq}`
规范化为新格式 `XIMO{code}{YYYYMMDD}{seq}`（去掉 SO- 前缀和序号前的连字符）。
业务员编码只允许 [A-Z0-9]（见 schemas/user.py 校验），故旧编号中仅有两个连字符：
SO- 之后那个、序号之前那个，去掉这两处即得新格式，不会误伤编码本身。

Revision ID: p6q8r0s2t4u6
Revises: o5p7q9r1s3t5
Create Date: 2026-06-26
"""
from alembic import op


revision = "p6q8r0s2t4u6"
down_revision = "o5p7q9r1s3t5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 去掉前 3 个字符 'SO-'，再删剩余唯一的连字符（序号分隔符）
    op.execute(
        """
        UPDATE formal_orders
        SET so_number = replace(substring(so_number from 4), '-', '')
        WHERE so_number LIKE 'SO-XIMO%'
        """
    )


def downgrade() -> None:
    # 单向数据规范化：新格式无分隔符，无法可靠还原序号边界（编码可含数字，与日期/序号无法区分），故不提供回滚。
    raise NotImplementedError("so_number 规范化为单向迁移，不支持降级")
