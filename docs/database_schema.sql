-- ============================================================
-- XIMOSteel 数据库表结构设计 v1.0
-- 数据库: PostgreSQL
-- 阶段: 第一阶段（外贸业务流转）
-- ============================================================


-- ============================================================
-- 1. 用户与权限
-- ============================================================

CREATE TABLE roles (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(20) NOT NULL UNIQUE,   -- super_admin / boss / salesperson / purchaser
    label       VARCHAR(50) NOT NULL           -- 超级管理员 / 老板 / 业务员 / 采购员
);

CREATE TABLE users (
    id              SERIAL PRIMARY KEY,
    username        VARCHAR(50) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    full_name       VARCHAR(50) NOT NULL,
    role_id         INTEGER NOT NULL REFERENCES roles(id),
    salesperson_code VARCHAR(20) UNIQUE,       -- 仅业务员有值，超管指定，唯一，大写字母或数字
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ============================================================
-- 2. 公司信息（用于生成 PI / CI 抬头）
-- ============================================================

CREATE TABLE company_info (
    id              SERIAL PRIMARY KEY,
    name_zh         VARCHAR(100),              -- 公司名称（中文）
    name_en         VARCHAR(100),              -- 公司名称（英文）
    address_zh      VARCHAR(255),
    address_en      VARCHAR(255),
    phone           VARCHAR(50),
    fax             VARCHAR(50),
    email           VARCHAR(100),
    bank_name       VARCHAR(100),              -- 开户行
    bank_account    VARCHAR(100),              -- 账号
    swift_code      VARCHAR(20),
    logo_path       VARCHAR(255),              -- Logo 文件路径
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by      INTEGER REFERENCES users(id)
);


-- ============================================================
-- 3. 产品库（第一阶段仅无缝钢管）
-- ============================================================

CREATE TABLE products (
    id              SERIAL PRIMARY KEY,
    outer_diameter  NUMERIC(10,2) NOT NULL,    -- 外径 (mm)
    inner_diameter  NUMERIC(10,2) NOT NULL,    -- 内径 (mm)
    length          NUMERIC(10,2) NOT NULL,    -- 长度 (mm)
    price_usd       NUMERIC(12,2) NOT NULL,    -- 价格 (USD)
    name            VARCHAR(100),              -- 品名（选填）
    material        VARCHAR(100),              -- 材质（选填）
    standard        VARCHAR(100),              -- 执行标准（选填）
    surface_finish  VARCHAR(100),              -- 表面处理（选填）
    unit            VARCHAR(20) NOT NULL DEFAULT 'MT',
    remarks         TEXT,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_by      INTEGER NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ============================================================
-- 4. 客户管理
-- ============================================================

CREATE TABLE customers (
    id              SERIAL PRIMARY KEY,
    company_name    VARCHAR(100) NOT NULL,
    country         VARCHAR(50) NOT NULL,
    contact_name    VARCHAR(50) NOT NULL,
    email           VARCHAR(100),              -- 选填
    phone           VARCHAR(50),
    trade_terms     VARCHAR(50),               -- FOB / CIF / CFR 等
    payment_terms   VARCHAR(100),              -- 付款方式
    grade           VARCHAR(10) NOT NULL DEFAULT 'potential', -- important / normal / potential
    owner_id        INTEGER NOT NULL REFERENCES users(id),    -- 归属业务员
    follow_freq     VARCHAR(10) NOT NULL DEFAULT 'daily',     -- daily / weekly / monthly
    follow_freq_updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),-- 最近一次频次变更时间
    consecutive_miss_cycles INTEGER NOT NULL DEFAULT 0,       -- 连续未有效跟进周期数
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 跟进记录（只增不删）
CREATE TABLE follow_up_records (
    id              SERIAL PRIMARY KEY,
    customer_id     INTEGER NOT NULL REFERENCES customers(id),
    content         TEXT NOT NULL,
    is_effective    BOOLEAN NOT NULL,          -- 有效 / 无效（创建时手动标记）
    created_by      INTEGER NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 跟进记录附图（多张）
CREATE TABLE follow_up_images (
    id              SERIAL PRIMARY KEY,
    follow_up_id    INTEGER NOT NULL REFERENCES follow_up_records(id) ON DELETE CASCADE,
    file_path       VARCHAR(255) NOT NULL,
    file_name       VARCHAR(255) NOT NULL,
    uploaded_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ============================================================
-- 5. 询报价（PI）
-- ============================================================

CREATE TABLE quotations (
    id              SERIAL PRIMARY KEY,
    pi_number       VARCHAR(50) NOT NULL UNIQUE, -- PI-XIMO{code}YYYYMMDD-序号
    customer_id     INTEGER NOT NULL REFERENCES customers(id),
    salesperson_id  INTEGER NOT NULL REFERENCES users(id),
    currency        VARCHAR(10) NOT NULL DEFAULT 'USD',
    exchange_rate   NUMERIC(10,4),             -- 汇率（如需换算）
    trade_terms     VARCHAR(50),               -- 贸易条款
    delivery_date   DATE,                      -- 交货期
    valid_until     DATE,                      -- 有效期
    status          VARCHAR(20) NOT NULL DEFAULT 'draft', -- draft / sent / closed / expired
    remarks         TEXT,
    created_by      INTEGER NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- PI 产品行
CREATE TABLE quotation_items (
    id              SERIAL PRIMARY KEY,
    quotation_id    INTEGER NOT NULL REFERENCES quotations(id) ON DELETE CASCADE,
    product_id      INTEGER REFERENCES products(id), -- NULL 表示自由填写的特殊产品
    -- 以下字段快照或自由填写，不随产品库变动
    description     TEXT NOT NULL,             -- 产品描述
    quantity        NUMERIC(12,3) NOT NULL,
    unit            VARCHAR(20) NOT NULL DEFAULT 'MT',
    unit_price      NUMERIC(12,2) NOT NULL,    -- 客户版单价
    unit_price_internal NUMERIC(12,2),         -- 内部版单价
    sort_order      INTEGER NOT NULL DEFAULT 0
);


-- ============================================================
-- 6. 订单（SO）
-- ============================================================

CREATE TABLE orders (
    id              SERIAL PRIMARY KEY,
    so_number       VARCHAR(50) NOT NULL UNIQUE, -- XIMO{code}YYYYMMDD序号(两位补零)
    quotation_id    INTEGER REFERENCES quotations(id),  -- 来源 PI（一键转单）
    customer_id     INTEGER NOT NULL REFERENCES customers(id),
    salesperson_id  INTEGER NOT NULL REFERENCES users(id),
    currency        VARCHAR(10) NOT NULL DEFAULT 'USD',
    exchange_rate   NUMERIC(10,4),
    trade_terms     VARCHAR(50),
    status          VARCHAR(30) NOT NULL DEFAULT 'confirmed',
    -- confirmed / preparing / ready_to_ship / shipped / completed
    est_ready_date  DATE,                      -- 预计备货完成日期（生产备货中状态使用）
    remarks         TEXT,
    created_by      INTEGER NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 订单产品行（从 PI 复制快照）
CREATE TABLE order_items (
    id              SERIAL PRIMARY KEY,
    order_id        INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id      INTEGER REFERENCES products(id),
    description     TEXT NOT NULL,
    quantity        NUMERIC(12,3) NOT NULL,
    unit            VARCHAR(20) NOT NULL DEFAULT 'MT',
    unit_price      NUMERIC(12,2) NOT NULL,
    unit_price_internal NUMERIC(12,2),
    sort_order      INTEGER NOT NULL DEFAULT 0
);


-- ============================================================
-- 7. 出运（内嵌订单，支持一单多箱）
-- ============================================================

CREATE TABLE shipments (
    id              SERIAL PRIMARY KEY,
    order_id        INTEGER NOT NULL REFERENCES orders(id),
    ship_type       VARCHAR(20) NOT NULL,      -- container / bulk
    vessel_voyage   VARCHAR(100),              -- 船名航次
    etd             DATE,                      -- 预计离港
    eta             DATE,                      -- 预计到港
    bl_number       VARCHAR(100),              -- 提单号
    -- 集装箱专用
    container_type  VARCHAR(20),               -- 20GP / 40HQ 等
    container_number VARCHAR(50),              -- 箱号
    seal_number     VARCHAR(50),               -- 封号
    -- 散货船专用
    weight_mt       NUMERIC(12,3),             -- 重量 (MT)
    status          VARCHAR(20) NOT NULL DEFAULT 'planned',
    -- planned / loaded / in_transit / arrived
    created_by      INTEGER NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ============================================================
-- 8. 单据中心（附件归档）
-- ============================================================

-- 系统生成文档记录（CI/PL 生成历史）
CREATE TABLE generated_documents (
    id              SERIAL PRIMARY KEY,
    order_id        INTEGER NOT NULL REFERENCES orders(id),
    doc_type        VARCHAR(20) NOT NULL,      -- CI / PL
    version         VARCHAR(10) NOT NULL,      -- customer / internal
    language        VARCHAR(10) NOT NULL DEFAULT 'en', -- zh / en / fr / es
    file_path       VARCHAR(255) NOT NULL,
    file_name       VARCHAR(255) NOT NULL,
    generated_by    INTEGER NOT NULL REFERENCES users(id),
    generated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 附件归档（MTC / CO / 出口许可 / 报关单据等）
CREATE TABLE order_attachments (
    id              SERIAL PRIMARY KEY,
    order_id        INTEGER NOT NULL REFERENCES orders(id),
    doc_type        VARCHAR(50) NOT NULL,      -- MTC / CO / export_license / customs / other
    file_path       VARCHAR(255) NOT NULL,
    file_name       VARCHAR(255) NOT NULL,
    uploaded_by     INTEGER NOT NULL REFERENCES users(id),
    uploaded_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ============================================================
-- 9. 公告通知
-- ============================================================

CREATE TABLE announcements (
    id              SERIAL PRIMARY KEY,
    content         TEXT NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,  -- FALSE = 已撤销
    created_by      INTEGER NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revoked_at      TIMESTAMPTZ,
    revoked_by      INTEGER REFERENCES users(id)
);


-- ============================================================
-- 10. 操作日志（全模块增删改）
-- ============================================================

CREATE TABLE operation_logs (
    id              BIGSERIAL PRIMARY KEY,
    operator_id     INTEGER NOT NULL REFERENCES users(id),
    module          VARCHAR(50) NOT NULL,      -- customer / quotation / order / product 等
    record_id       INTEGER NOT NULL,          -- 被操作记录的 ID
    action          VARCHAR(20) NOT NULL,      -- create / update / delete
    field_changes   JSONB,                     -- {"field": {"before": x, "after": y}, ...}
    operated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ============================================================
-- 11. 用户列表字段偏好（按用户个人保存）
-- ============================================================

CREATE TABLE user_column_prefs (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    module          VARCHAR(50) NOT NULL,      -- customer / quotation / order / product 等
    columns_config  JSONB NOT NULL,            -- [{"key": "company_name", "visible": true, "order": 1}, ...]
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, module)
);


-- ============================================================
-- 索引
-- ============================================================

CREATE INDEX idx_customers_owner ON customers(owner_id);
CREATE INDEX idx_follow_up_records_customer ON follow_up_records(customer_id);
CREATE INDEX idx_follow_up_records_created_at ON follow_up_records(customer_id, created_at DESC);
CREATE INDEX idx_quotations_customer ON quotations(customer_id);
CREATE INDEX idx_quotations_salesperson ON quotations(salesperson_id);
CREATE INDEX idx_quotations_status ON quotations(status);
CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_orders_salesperson ON orders(salesperson_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_shipments_order ON shipments(order_id);
CREATE INDEX idx_order_attachments_order ON order_attachments(order_id);
CREATE INDEX idx_operation_logs_module_record ON operation_logs(module, record_id);
CREATE INDEX idx_operation_logs_operator ON operation_logs(operator_id);
CREATE INDEX idx_operation_logs_operated_at ON operation_logs(operated_at DESC);
CREATE INDEX idx_announcements_active ON announcements(is_active, created_at DESC);
