"""fix 'NOW()' literal defaults and backfill corrupted timestamps

Background:
    历史模型里把 server_default 写成了 Python 字符串 "NOW()"，
    SQLAlchemy 会编译成 SQL 字面量  DEFAULT 'NOW()' （字符串），
    而不是函数  DEFAULT now() 。于是凡是没有在代码里显式赋值的行，
    时间戳字段被写入了字面文本 'NOW()'。

本迁移做两件事（对所有受影响的列一次性处理）：
    1. 把列默认值从字面量 'NOW()' 改成真正的函数 now()
    2. 把已经写坏的数据（值正好等于 'NOW()' 的行）回填成当前时间

Revision ID: l2m4n6o8p0q2
Revises: k1l3m5n7o9p1
Create Date: 2026-06-16
"""
from alembic import op

revision = 'l2m4n6o8p0q2'
down_revision = 'k1l3m5n7o9p1'
branch_labels = None
depends_on = None


def upgrade():
    # 遍历当前 schema 下所有「默认值是字面量 'NOW()'」的列，逐列修正默认值并回填脏数据
    op.execute(
        """
        DO $$
        DECLARE
            r RECORD;
        BEGIN
            FOR r IN
                SELECT table_name, column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND column_default LIKE '''NOW()''%'
            LOOP
                -- 1. 修正默认值：字面量 'NOW()' -> 函数 now()
                EXECUTE format(
                    'ALTER TABLE %I ALTER COLUMN %I SET DEFAULT now()',
                    r.table_name, r.column_name
                );
                -- 2. 回填已经写坏的行
                EXECUTE format(
                    'UPDATE %I SET %I = now()::text WHERE %I = ''NOW()''',
                    r.table_name, r.column_name, r.column_name
                );
            END LOOP;
        END $$;
        """
    )


def downgrade():
    # 不提供回退：把正确的 now() 默认值再改回有问题的 'NOW()' 字面量没有意义，
    # 已回填的数据也无法还原成原始的损坏值。
    pass
