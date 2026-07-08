# XIMO Project 项目理解文档

更新时间：2026-07-08

## 1. 项目定位

XIMO Project 是一个面向钢贸/外贸业务的内部管理系统，前后端分离，核心围绕“客户跟进 -> 询价单 -> 收定金 -> 正式订单 -> 出运单据 -> 财务记账/工资核算”的业务闭环展开。

系统主要服务对象包括：

- 超级管理员：用户、权限和全局数据管理。
- 老板/管理层：看板、员工评价、业务进度总览、公告发布。
- 业务员：客户管理、跟进记录、询价单、订单推进、归档文件维护。
- 采购员：公告发布。
- 财务：已完结订单记账、利润登记、工资核算标记。
- 后勤/物流：出运相关单据维护，尤其是 CO 和出口许可证。

## 2. 技术栈

### 后端

- Python + FastAPI
- SQLAlchemy 2.x ORM
- Alembic 数据库迁移
- PostgreSQL
- Pydantic / pydantic-settings
- JWT + httpOnly Cookie 认证
- passlib/bcrypt 密码哈希
- StaticFiles 提供上传附件访问

后端入口：`backend/app/main.py`

### 前端

- Vue 3
- Vite
- Vue Router
- Pinia
- Ant Design Vue
- Axios
- ECharts

前端入口：`frontend/src/main.js`

路由配置：`frontend/src/router/index.js`

## 3. 目录结构

```text
backend/
  app/
    main.py              FastAPI 应用入口，注册中间件、静态文件、路由
    config.py            环境变量配置
    database.py          SQLAlchemy engine/session/Base
    core/                认证、依赖、常量
    models/              数据库模型
    schemas/             Pydantic 请求/响应模型
    routers/             API 路由
  alembic/               数据库迁移
  scripts/seed_data.py   初始化角色和超级管理员
  requirements.txt       后端依赖

frontend/
  src/
    api/                 前端 API 封装
    stores/auth.js       登录态和用户信息
    router/index.js      前端路由与路由守卫
    layouts/             主布局
    views/               页面
    components/          可复用组件
    utils/               格式化、国家数据等工具
  package.json
  vite.config.js

docs/
  database_schema.sql    早期/设计态数据库结构文档
  project_overview.md    当前项目理解文档

deploy/
  deploy.md              部署说明
  nginx.conf             Nginx 配置
  supervisor.conf        Supervisor 配置
```

## 4. 启动与运行

### 后端

后端依赖 `.env`，至少需要：

```env
DATABASE_URL=postgresql://user:password@host:port/database
SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=480
UPLOAD_DIR=./uploads
COOKIE_SECURE=False
```

开发启动：

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
python -m scripts.seed_data
uvicorn app.main:app --reload
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

Vite 开发服务器默认端口 `5173`，并把 `/api` 和 `/uploads` 代理到 `http://localhost:8000`。

### 默认初始化数据

`backend/scripts/seed_data.py` 会创建角色，并创建默认超级管理员：

- 用户名：`admin`
- 密码：`admin123`

首次部署后应立即修改密码。

## 5. 认证与权限

### 认证机制

- 登录接口校验用户名/密码后生成 JWT。
- JWT 写入后端设置的 `access_token` httpOnly Cookie。
- 前端不保存 token，只在 `sessionStorage` 缓存用户信息，刷新或进入受保护页面时通过 `/api/auth/me` 校验 Cookie。
- 后端仍兼容 Bearer token，便于脚本或测试调用。

### 后端权限入口

- `get_current_user`：读取 Cookie 或 Bearer token，校验 JWT，返回当前用户。
- `require_roles(...)`：要求当前用户具备指定角色。

### 前端权限入口

- `frontend/src/stores/auth.js`：保存当前用户和 `hasRole` 判断。
- `frontend/src/router/index.js`：未登录跳转登录页；财务和物流只允许进入看板、订单列表和订单详情。
- `frontend/src/layouts/MainLayout.vue`：根据角色隐藏菜单项。

### 角色能力概览

| 角色 | 主要能力 |
| --- | --- |
| `super_admin` | 全局管理，用户管理，跨业务数据访问与修改 |
| `boss` | 管理看板、评价员工、查看全局业务、发布公告 |
| `salesperson` | 管理自己的客户、跟进、询价和订单 |
| `purchaser` | 公告发布 |
| `finance` | 已完结订单记账、利润登记、工资核算 |
| `logistics` | 后勤单据维护，订单详情中只看物流相关信息 |

## 6. 核心业务流程

### 6.1 客户跟进

相关模型：

- `Customer`
- `FollowUpRecord`
- `FollowUpImage`

业务规则：

- 客户有负责人 `owner_id`，业务员通常只能访问自己的客户。
- 客户分级包括 `key`、`normal`、`potential`。
- 跟进频次包括 `daily`、`weekly`、`monthly`。
- 跟进记录只新增，不做删除接口。
- 跟进记录可标记为有效/无效，并可上传多张图片。
- 系统有自动降级逻辑：长期未有效跟进时，客户跟进频次会下调；也支持手动升级频次。

主要页面：

- `frontend/src/views/customers/CustomerList.vue`
- `frontend/src/views/customers/CustomerDetail.vue`
- `frontend/src/views/customers/FollowUpList.vue`

主要接口：

- `GET /api/customers/`
- `POST /api/customers/`
- `GET /api/customers/{id}`
- `PUT /api/customers/{id}`
- `PUT /api/customers/{id}/upgrade-freq`
- `GET /api/customers/{id}/follow-ups`
- `POST /api/customers/{id}/follow-ups`
- `GET /api/customers/follow-ups/all`

### 6.2 已移除功能：产品库

产品库功能已从当前应用入口中删除：

- 后端不再注册 `/api/products` 路由。
- 前端不再提供 `/products` 页面和侧边栏菜单。
- 产品库前端页面、前端 API、后端路由、后端模型、后端 Schema 已删除。

注意：历史 Alembic 迁移里仍可能保留 `products` 表及历史外键，用于兼容既有迁移链。当前删除不主动清理数据库历史表，也不新增 drop table 迁移。

### 6.3 询价单

相关模型：

- `Inquiry`
- `InquiryFile`

询价单状态：

- `active`：进行中
- `deposit_received`：已收定金
- `converted`：已转正式订单
- `void`：已作废

询价单编号：

```text
ENQ-XIMO{业务员编码}{YYYYMMDD}-{两位序号}
```

例如业务员编码为 `A01`，当天第一张询价单：

```text
ENQ-XIMOA0120260708-01
```

文件类型：

- `pricing_sheet`：核价单，登记定金前必需
- `pi`：PI，登记定金前必需
- `freight_quote`：货代/运费报价，可选

文件版本规则：

- 同一 `doc_type` 上传新文件时，旧版本会自动置为非当前版本。
- 新版本 `is_current=True`。
- 历史版本保留，用作工作记录。
- 询价单只有在 `active` 状态下允许删除当前版本文件。

流程规则：

- 老板角色不能创建询价单。
- 登记定金前必须有当前版本的核价单和 PI。
- 已作废询价单不能登记定金。
- 已转订单询价单不能再修改定金。
- 已收定金后可转为正式订单。

主要接口：

- `GET /api/inquiries/`
- `POST /api/inquiries/`
- `GET /api/inquiries/{id}`
- `PUT /api/inquiries/{id}`
- `PATCH /api/inquiries/{id}/deposit`
- `PATCH /api/inquiries/{id}/void`
- `POST /api/inquiries/{id}/files`
- `DELETE /api/inquiries/{id}/files/{file_id}`

### 6.4 正式订单

相关模型：

- `FormalOrder`
- `OrderFile`
- `ShipmentBL`
- `ShipmentContainer`

订单由已收定金的询价单转换生成。转换后：

- 询价单状态变为 `converted`。
- 订单状态初始为 `confirmed`。
- 订单关联原询价单、客户、业务员。

订单编号：

```text
XIMO{业务员编码}{YYYYMMDD}{两位序号}
```

例如：

```text
XIMOA012026070801
```

订单状态流转：

```text
confirmed -> production -> ready -> shipping -> completed
```

现货订单会跳过 `production`：

```text
confirmed -> ready -> shipping -> completed
```

状态含义：

- `confirmed`：已确认
- `production`：生产中
- `ready`：待出运
- `shipping`：出运中
- `completed`：已完结

编辑和锁定规则：

- 超级管理员和订单所属业务员可编辑未完结订单。
- 工资已核算后，订单主体和大多数文件锁定。
- 进入 `shipping` 或 `completed` 后，正式归档文件锁定为只读。
- `shipping` 阶段仍允许维护海运提单 `ocean_bl`。
- `supplement` 补充附件不受出运锁定限制，但上传后不可删除。
- CO 和出口许可证由后勤/超级管理员维护，不受出运和工资核算锁定限制。

订单文件类型：

- 业务归档：`mtc`、`pl`、`ci`、`inspection`、`packing`、`ocean_bl`
- 后勤单据：`co`、`export_permit`
- 财务/后勤查看类：`fin_ci`、`fin_mtc`、`fin_pl`、`customs_declaration`
- 补充附件：`supplement`

提单规则：

- 当前后端限制一个订单只对应一张提单 `ShipmentBL`。
- 提单可记录运输方式、船司、提单号、船名航次、起运港、目的港、目的国、ETD/ETA。
- 集装箱模式可记录箱型箱量和集装箱明细。
- 散货模式可记录件数、重量、体积。

主要接口：

- `POST /api/formal-orders/`
- `GET /api/formal-orders/`
- `GET /api/formal-orders/{id}`
- `PUT /api/formal-orders/{id}`
- `PATCH /api/formal-orders/{id}/status`
- `POST /api/formal-orders/{id}/files`
- `DELETE /api/formal-orders/{id}/files/{file_id}`
- `POST /api/formal-orders/{id}/bls`
- `PUT /api/formal-orders/{id}/bls/{bl_id}`
- `DELETE /api/formal-orders/{id}/bls/{bl_id}`

### 6.5 财务记账

相关模型：

- `AccountingRecord`

业务规则：

- 只有 `finance` 角色可访问财务记账接口。
- 只能对 `completed` 已完结订单记账。
- 一个订单最多一条记账记录。
- 记账记录包含利润、备注、附件。
- 工资核算标记只能从未核算变为已核算，后端不允许撤销。
- 工资已核算后不能修改记账记录。

主要接口：

- `GET /api/accounting/{order_id}`
- `POST /api/accounting/{order_id}`
- `PATCH /api/accounting/{order_id}/salary`
- `DELETE /api/accounting/{order_id}/file`

### 6.6 员工评价

相关模型：

- `Evaluation`

业务规则：

- 评价分数限制为 1 到 10。
- 老板和超级管理员可以创建/删除评价。
- 评价目标类型包括 `followup`、`inquiry`、`formal_order`。
- 看板中会展示员工评价趋势。

主要接口：

- `POST /api/evaluations`
- `GET /api/evaluations`
- `GET /api/evaluations/stats`
- `DELETE /api/evaluations/{id}`

### 6.7 公告

相关模型：

- `Announcement`

业务规则：

- 登录用户可查看当前有效公告。
- `boss`、`purchaser`、`super_admin` 可发布公告。
- 公告是软撤销，撤销后 `is_active=False`。
- 创建人或超级管理员可撤销公告。

主要接口：

- `GET /api/announcements/`
- `POST /api/announcements/`
- `DELETE /api/announcements/{id}`

### 6.8 看板与全球大屏

主要接口：

- `GET /api/dashboard/boss`
- `GET /api/dashboard/salesperson`
- `GET /api/dashboard/finance`
- `GET /api/dashboard/logistics`
- `GET /api/dashboard/world-map`

看板按角色返回不同数据：

- 老板/超级管理员：今日跟进、有效跟进、进行中订单、出运计划、订单状态统计、员工评价趋势。
- 业务员：今日待跟进、我的客户数、今日已跟进、我的进行中订单、我的评价趋势。
- 财务：待记账订单、已记账订单、待发放工资订单。
- 后勤：缺少 CO 或出口许可证的订单。

全球大屏：

- `/api/dashboard/world-map` 不要求登录，但要求内网/本机访问。
- 返回海外客户国家热力数据，以及未完结订单按提单目的国聚合的航线数据。
- 国内客户会被排除在海外客户热力图之外。

## 7. 数据模型概览

```mermaid
erDiagram
    Role ||--o{ User : has
    User ||--o{ Customer : owns
    Customer ||--o{ FollowUpRecord : has
    FollowUpRecord ||--o{ FollowUpImage : has

    Customer ||--o{ Inquiry : creates
    User ||--o{ Inquiry : salesperson
    Inquiry ||--o{ InquiryFile : has
    Inquiry ||--o| FormalOrder : converts_to

    FormalOrder ||--o{ OrderFile : has
    FormalOrder ||--o{ ShipmentBL : has
    ShipmentBL ||--o{ ShipmentContainer : has
    FormalOrder ||--o| AccountingRecord : has

    User ||--o{ Evaluation : evaluator
    User ||--o{ Evaluation : subject
    User ||--o{ Announcement : creates
```

关键表：

- `roles`：角色
- `users`：用户
- `customers`：客户
- `follow_up_records`：客户跟进记录
- `follow_up_images`：跟进图片
- `inquiries`：询价单
- `inquiry_files`：询价单附件版本
- `formal_orders`：正式订单
- `order_files`：订单附件
- `shipment_bls`：提单
- `shipment_containers`：集装箱
- `evaluations`：评价
- `announcements`：公告
- `accounting_records`：财务记账

## 8. 文件上传与静态访问

后端通过 `settings.UPLOAD_DIR` 保存上传文件，并把该目录挂载到 `/uploads`。

上传文件保存方式：

- 文件名使用 UUID，避免同名覆盖。
- 数据库保存原始文件名和相对路径。
- 前端通过 `/uploads/{file_path}` 访问。

安全处理：

- `/uploads` 静态文件会经过 `ForceDownloadMiddleware`。
- 图片和 PDF 允许浏览器内联预览。
- 其他类型强制 `Content-Disposition: attachment` 下载，降低 HTML/SVG 等可执行内容带来的 XSS 风险。

目前主要允许文件类型：

- PDF
- 图片：PNG/JPG/JPEG 等
- Office 文档：DOC/DOCX/XLS/XLSX

## 9. 前端页面地图

| 路由 | 页面 | 说明 |
| --- | --- | --- |
| `/login` | `Login.vue` | 登录页 |
| `/board` | `WorldMapBoard.vue` | 全球业务大屏，公开但依赖后端内网限制 |
| `/` | `Dashboard.vue` | 角色看板 |
| `/customers` | `CustomerList.vue` | 客户列表 |
| `/customers/:id` | `CustomerDetail.vue` | 客户详情、跟进记录、评价 |
| `/follow-ups` | `FollowUpList.vue` | 跟进记录汇总 |
| `/inquiries` | `InquiryList.vue` | 询价单列表 |
| `/inquiries/:id` | `InquiryDetail.vue` | 询价单详情、文件版本、登记定金、转订单 |
| `/formal-orders` | `OrderList.vue` | 正式订单列表 |
| `/formal-orders/:id` | `OrderDetail.vue` | 订单详情、单据、提单、财务 |
| `/settings/users` | `UserManagement.vue` | 用户管理，仅超级管理员 |

## 10. 当前代码中的注意点

1. 终端中部分中文注释和文案显示为乱码，大概率是编码显示问题；源码逻辑仍可读，但后续维护建议统一确认文件编码为 UTF-8。

2. `docs/database_schema.sql` 更像早期设计文档，部分表名和当前 ORM 模型不完全一致。例如早期设计里有 `quotations`、`orders`，当前实现中核心是 `inquiries` 和 `formal_orders`。实际开发应以 Alembic 迁移和 `backend/app/models/` 为准。

3. 订单状态推进是线性的，后端不支持任意回退。若业务需要撤回状态，需要新增明确的撤回规则和审计记录。

4. 财务工资核算标记后不可撤销，且会锁定记账修改。实际操作前需要二次确认。

5. 全球大屏接口依赖 `request.client.host` 做内网判断；如果经过 Nginx 反向代理，可能看到的是代理 IP。生产环境应在 Nginx 层也做 allow/deny，或正确传递真实客户端 IP 后再判断。

6. 目前没有看到自动化测试目录。后续对状态流转、权限、文件锁定等高风险逻辑做修改时，建议补充接口级测试。

## 11. 推荐后续维护顺序

如果继续深入或接手开发，建议按以下顺序：

1. 先跑通本地后端、前端和数据库迁移。
2. 用 `seed_data.py` 初始化角色与管理员。
3. 创建不同角色用户，验证菜单与接口权限。
4. 按真实业务走一遍：客户 -> 跟进 -> 询价 -> 上传核价单/PI -> 登记定金 -> 转正式订单 -> 推进状态 -> 上传单据 -> 提单 -> 完结 -> 财务记账。
5. 对照这条主流程补测试，优先覆盖权限和状态锁定。
6. 再处理编码、文案、历史设计文档与当前模型不一致的问题。

## 12. 手动调试与功能修改定位

本节用于回答“调试某个功能时应该改哪些文件”。一般规律是：

- 前端页面交互改 `frontend/src/views/` 或 `frontend/src/components/`。
- 前端请求地址和参数改 `frontend/src/api/`。
- 前端登录态、角色判断改 `frontend/src/stores/auth.js`。
- 前端路由和页面访问限制改 `frontend/src/router/index.js`。
- 后端接口逻辑改 `backend/app/routers/`。
- 后端数据结构改 `backend/app/models/`、`backend/app/schemas/`，并新增 Alembic 迁移。
- 后端认证、角色权限改 `backend/app/core/deps.py` 和相关路由中的 `require_roles`。
- 数据库连接、上传目录、Cookie 安全参数改 `.env` 和 `backend/app/config.py`。

### 12.1 登录、用户、角色权限

调试登录失败、Cookie、当前用户：

- 后端登录接口：`backend/app/routers/auth.py`
- JWT 创建/校验：`backend/app/core/security.py`
- 当前用户解析：`backend/app/core/deps.py`
- 前端登录页：`frontend/src/views/Login.vue`
- 前端登录态：`frontend/src/stores/auth.js`
- Axios Cookie 携带：`frontend/src/api/index.js`

调试用户管理、角色、业务员编码：

- 后端接口：`backend/app/routers/users.py`
- 后端模型：`backend/app/models/user.py`
- 后端 Schema：`backend/app/schemas/user.py`
- 前端页面：`frontend/src/views/settings/UserManagement.vue`
- 初始化角色/默认管理员：`backend/scripts/seed_data.py`

调试“某个角色看不到菜单/页面”：

- 菜单显示：`frontend/src/layouts/MainLayout.vue`
- 路由守卫：`frontend/src/router/index.js`
- 后端接口角色限制：各 `backend/app/routers/*.py` 中的 `require_roles(...)`

### 12.2 客户与跟进

调试客户列表、客户详情、客户新增/编辑：

- 前端客户列表：`frontend/src/views/customers/CustomerList.vue`
- 前端客户详情：`frontend/src/views/customers/CustomerDetail.vue`
- 前端 API：`frontend/src/api/customers.js`
- 后端接口：`backend/app/routers/customers.py`
- 后端模型：`backend/app/models/customer.py`
- 后端 Schema：`backend/app/schemas/customer.py`

调试跟进记录、跟进图片上传、有效/无效跟进：

- 前端客户详情跟进区域：`frontend/src/views/customers/CustomerDetail.vue`
- 前端跟进汇总页：`frontend/src/views/customers/FollowUpList.vue`
- 后端跟进接口：`backend/app/routers/customers.py`
- 上传目录配置：`backend/app/config.py` 中的 `UPLOAD_DIR`
- 静态文件访问和下载策略：`backend/app/main.py`

调试客户跟进频次、自动降级、手动升级：

- 后端频次常量：`backend/app/core/constants.py`
- 后端降级/升级逻辑：`backend/app/routers/customers.py`
- 前端客户详情频次显示和升级入口：`frontend/src/views/customers/CustomerDetail.vue`

### 12.3 已移除功能：产品库

产品库已从当前功能中删除。若手动调试时仍看到产品库入口，优先检查是否在使用旧的前端构建产物：

- 前端菜单应不再包含 `/products`。
- 前端路由应不再包含 `Products`。
- 后端 `backend/app/main.py` 应不再注册 `products.router`。
- 源码中不应再存在 `frontend/src/views/products/ProductList.vue`、`frontend/src/api/products.js`、`backend/app/routers/products.py`、`backend/app/models/product.py`、`backend/app/schemas/product.py`。

如果未来要恢复产品库，建议重新设计为独立模块，并补充导入预览、差异确认和操作日志，避免全量替换误操作。

### 12.4 询价单

调试询价单列表、筛选、新建：

- 前端列表页：`frontend/src/views/inquiry/InquiryList.vue`
- 前端 API：`frontend/src/api/inquiries.js`
- 后端接口：`backend/app/routers/inquiries.py`
- 后端模型：`backend/app/models/inquiry.py`
- 后端 Schema：`backend/app/schemas/inquiry.py`

调试询价单详情、附件上传、附件版本、登记定金、作废：

- 前端详情页：`frontend/src/views/inquiry/InquiryDetail.vue`
- 前端 API：`frontend/src/api/inquiries.js`
- 后端接口：`backend/app/routers/inquiries.py`

常见修改点：

- 文件类型范围：`backend/app/routers/inquiries.py` 的 `INQUIRY_DOC_TYPES`
- 允许上传扩展名：`backend/app/routers/inquiries.py` 的 `ALLOWED_UPLOAD_EXTENSIONS`
- 询价号生成：`backend/app/routers/inquiries.py` 的 `_gen_enq_number`
- 登记定金前置条件：`backend/app/routers/inquiries.py` 的 `set_deposit`
- 前端必传文件提示：`frontend/src/views/inquiry/InquiryDetail.vue` 的 `DOC_DEFS` 和 `reminder`

### 12.5 正式订单、订单状态与单据

调试订单列表、筛选、状态筛选、财务/后勤筛选：

- 前端列表页：`frontend/src/views/inquiry/OrderList.vue`
- 前端 API：`frontend/src/api/inquiries.js` 中的 `formalOrdersApi`
- 后端接口：`backend/app/routers/formal_orders.py`
- 后端模型：`backend/app/models/inquiry.py`
- 后端 Schema：`backend/app/schemas/inquiry.py`

调试订单详情、状态推进、主题编辑、生产倒计时：

- 前端详情页：`frontend/src/views/inquiry/OrderDetail.vue`
- 后端状态流转：`backend/app/routers/formal_orders.py` 的 `_next_status`
- 后端状态更新接口：`backend/app/routers/formal_orders.py` 的 `update_status`
- 前端状态流转：`frontend/src/views/inquiry/OrderDetail.vue` 的 `computeNext`

如果修改订单状态流转，必须同时检查：

- 后端 `_next_status`
- 前端 `computeNext`
- 前端 `STATUS_LABEL`
- 后端 `STATUS_LABELS`
- 列表筛选和看板统计中是否写死状态值

调试订单附件、文件锁定、补充附件：

- 后端文件类型：`backend/app/routers/formal_orders.py` 的 `ORDER_DOC_TYPES`
- 后端后勤文件：`LOGISTICS_MANAGED_DOC_TYPES`
- 后端财务/后勤查看类文件：`FINANCE_LOGISTICS_DOC_TYPES`
- 后端锁定状态：`FILE_LOCK_STATUSES`
- 后端出运阶段例外：`SHIPPING_STAGE_DOC_TYPES`
- 后端补充附件：`SUPPLEMENT_DOC_TYPE`
- 前端订单详情文件区：`frontend/src/views/inquiry/OrderDetail.vue`
- 前端单据定义：`OrderDetail.vue` 中的 `DOC_DEFS`、`FIN_DOC_DEFS`、`LOGI_DOC_KEYS` 等常量

调试提单、目的国、航线大屏：

- 后端提单接口：`backend/app/routers/formal_orders.py`
- 后端模型：`ShipmentBL`、`ShipmentContainer` in `backend/app/models/inquiry.py`
- 前端提单区域：`frontend/src/views/inquiry/OrderDetail.vue`
- 国家选择工具：`frontend/src/utils/countries.js`
- 全球大屏数据：`backend/app/routers/dashboard.py` 的 `world_map`
- 全球大屏页面：`frontend/src/views/WorldMapBoard.vue`

### 12.6 财务记账与工资核算

调试订单完结后的财务记账：

- 前端订单详情财务区域：`frontend/src/views/inquiry/OrderDetail.vue`
- 前端 API：`frontend/src/api/accounting.js`
- 后端接口：`backend/app/routers/accounting.py`
- 后端模型：`backend/app/models/accounting.py`

常见修改点：

- “只能已完结订单记账”：`backend/app/routers/accounting.py` 的 `create_or_update_record`
- 工资核算后不可修改：`backend/app/routers/accounting.py`
- 工资核算后订单文件锁定：`backend/app/routers/formal_orders.py` 的 `_salary_calculated`、`_can_edit`
- 财务看板统计：`backend/app/routers/dashboard.py` 的 `finance_dashboard`

### 12.7 看板、公告、评价

调试首页看板数据：

- 前端页面：`frontend/src/views/Dashboard.vue`
- 前端 API：`frontend/src/api/dashboard.js`
- 后端接口：`backend/app/routers/dashboard.py`

按角色分别看：

- 老板看板：`boss_dashboard`
- 业务员看板：`salesperson_dashboard`
- 财务看板：`finance_dashboard`
- 后勤看板：`logistics_dashboard`
- 全球大屏：`world_map`

调试公告：

- 前端看板公告区域：`frontend/src/views/Dashboard.vue`
- 前端 API：`frontend/src/api/announcements.js`
- 后端接口：`backend/app/routers/announcements.py`
- 后端模型：`backend/app/models/announcement.py`

调试评价：

- 前端评价组件：`frontend/src/components/EvaluationPanel.vue`
- 前端看板评价趋势：`frontend/src/views/Dashboard.vue`
- 前端 API：`frontend/src/api/evaluations.js`
- 后端接口：`backend/app/routers/evaluations.py`
- 后端模型：`backend/app/models/evaluation.py`

### 12.8 数据库字段变更

如果只是改页面文案或接口逻辑，不一定需要迁移。只要新增/删除/修改数据库字段，就需要同时处理：

1. 修改 SQLAlchemy 模型：`backend/app/models/*.py`
2. 修改 Pydantic Schema：`backend/app/schemas/*.py`
3. 修改后端路由读写逻辑：`backend/app/routers/*.py`
4. 新增 Alembic 迁移：`backend/alembic/versions/`
5. 修改前端页面和 API 参数：`frontend/src/views/`、`frontend/src/api/`
6. 执行 `alembic upgrade head`

当前项目的真实数据库结构应优先以 Alembic 迁移和 `backend/app/models/` 为准，不要只依赖 `docs/database_schema.sql`。

### 12.9 调试时建议的主流程

手动调试建议按下面顺序走一遍：

1. 用超级管理员登录，创建业务员并设置业务员编码。
2. 用业务员登录，创建客户。
3. 在客户详情添加有效跟进和图片。
4. 创建询价单。
5. 上传核价单和 PI。
6. 登记定金。
7. 转正式订单。
8. 推进订单状态，分别测试现货和非现货。
9. 上传订单归档文件、财务/后勤单据和补充附件。
10. 创建/编辑提单，填写目的国。
11. 推进到已完结。
12. 用财务账号记账并标记工资核算。
13. 用后勤账号检查 CO/出口许可证维护。
14. 打开老板看板和全球大屏，检查统计是否同步变化。

### 12.10 常见问题快速定位

| 现象 | 优先检查文件 |
| --- | --- |
| 登录后马上跳回登录页 | `backend/app/routers/auth.py`、`backend/app/core/deps.py`、`frontend/src/api/index.js`、`frontend/src/stores/auth.js` |
| 某角色菜单不显示 | `frontend/src/layouts/MainLayout.vue` |
| 某角色页面进不去 | `frontend/src/router/index.js` |
| 某接口 403 | 对应 `backend/app/routers/*.py` 的 `require_roles` 或 `_can_access` |
| 文件上传成功但打不开 | `backend/app/main.py`、上传接口保存的 `file_path`、前端 `/uploads/${file_path}` |
| 订单不能推进状态 | `backend/app/routers/formal_orders.py` 的 `_next_status`、前端 `OrderDetail.vue` 的 `computeNext` |
| 询价不能登记定金 | `backend/app/routers/inquiries.py` 的 `set_deposit`、前端 `InquiryDetail.vue` 的 `canDeposit` |
| 财务不能记账 | `backend/app/routers/accounting.py`，确认订单是否 `completed` |
| 工资核算后无法修改 | `backend/app/routers/accounting.py`、`backend/app/routers/formal_orders.py` |
| 全球大屏 403 | `backend/app/routers/dashboard.py` 的 `require_lan`，以及 Nginx/代理 IP 设置 |
