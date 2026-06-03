# 部署步骤

## 首次部署

### 1. 安装系统依赖
```bash
sudo apt update
sudo apt install python3.11 python3.11-venv postgresql nginx supervisor -y
```

### 2. 初始化数据库
```bash
sudo -u postgres psql
CREATE DATABASE tradeflow;
CREATE USER tradeflow WITH PASSWORD 'your-password';
GRANT ALL PRIVILEGES ON DATABASE tradeflow TO tradeflow;
\q
```

### 3. 后端部署
```bash
cd /var/www/tradeflow/backend
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# 编辑 .env，填写 DATABASE_URL 和 SECRET_KEY

# 执行数据库迁移
alembic upgrade head
```

### 4. 前端构建
```bash
cd /var/www/tradeflow/frontend
npm install
npm run build
```

### 5. 配置 Nginx
```bash
sudo cp /var/www/tradeflow/deploy/nginx.conf /etc/nginx/sites-available/tradeflow
sudo ln -s /etc/nginx/sites-available/tradeflow /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 6. 配置 Supervisor
```bash
sudo mkdir -p /var/log/tradeflow
sudo cp /var/www/tradeflow/deploy/supervisor.conf /etc/supervisor/conf.d/tradeflow.conf
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start tradeflow
```

## 日常更新

```bash
# 拉取代码
git pull

# 后端（如有数据库变更）
source venv/bin/activate
alembic upgrade head
sudo supervisorctl restart tradeflow

# 前端
cd frontend && npm run build
```

## 开发环境启动

```bash
# 后端
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # 填写本地配置
uvicorn app.main:app --reload

# 前端（新终端）
cd frontend
npm install
npm run dev
```
