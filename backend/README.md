# 英语教学资料智能格式适配与内容纠错工具 - 后端服务

面向全国卷高三/初三英语教师的轻量化网站工具后端服务。

## 技术栈

- **Web框架**: FastAPI 0.104.1
- **数据库**: SQLite + SQLAlchemy (异步)
- **数据库迁移**: Alembic
- **运行环境**: Python 3.11+

## 快速开始

### 1. 创建虚拟环境

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
# 复制环境变量示例文件
cp .env.example .env

# 编辑 .env 文件，填入你的配置
# - LLM_API_KEY: 大模型API密钥
# - BAIDU_OCR_API_KEY: 百度OCR API Key
# - BAIDU_OCR_SECRET_KEY: 百度OCR Secret Key
```

### 4. 初始化数据库

```bash
# 使用Alembic初始化数据库
alembic revision --autogenerate -m "初始化数据库表结构"
alembic upgrade head
```

### 5. 启动服务

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 6. 访问API文档

打开浏览器访问: http://localhost:8000/docs

## 项目结构

```
backend/
├── app/
│   ├── main.py           # FastAPI应用入口
│   ├── core/
│   │   ├── config.py     # 应用配置
│   │   └── database.py   # 数据库连接
│   ├── models/
│   │   ├── task.py       # 任务模型
│   │   ├── template.py   # 模板模型
│   │   └── site_stats.py # 统计模型
│   ├── api/
│   │   └── v1/
│   │       └── endpoints/
│   │           ├── health.py   # 健康检查
│   │           ├── upload.py   # 文件上传
│   │           └── tasks.py    # 任务管理
│   ├── services/         # 业务逻辑(待实现)
│   └── utils/            # 工具函数(待实现)
├── alembic/              # 数据库迁移
│   ├── env.py
│   └── versions/
├── data/                 # SQLite数据库存储
├── tests/                # 测试
├── requirements.txt      # Python依赖
├── .env.example          # 环境变量示例
└── alembic.ini           # Alembic配置
```

## API端点

### 健康检查
- `GET /api/v1/health` - 基础健康检查
- `GET /api/v1/health/detail` - 详细健康检查

### 文件上传
- `POST /api/v1/upload` - 上传文件
- `GET /api/v1/upload/presets` - 获取预设样式列表

### 任务管理
- `GET /api/v1/tasks` - 获取任务列表
- `GET /api/v1/tasks/{task_id}` - 查询任务状态
- `DELETE /api/v1/tasks/{task_id}` - 取消任务

## 开发指南

### 数据库迁移

```bash
# 生成新的迁移脚本
alembic revision --autogenerate -m "描述你的更改"

# 应用迁移
alembic upgrade head

# 回退迁移
alembic downgrade -1
```

### 运行测试

```bash
pytest tests/ -v
```

## 配置说明

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| DATABASE_URL | 数据库连接URL | sqlite+aiosqlite:///./data/english_tool.db |
| LLM_API_KEY | 大模型API密钥 | - |
| LLM_BASE_URL | 大模型API地址 | https://dashscope.aliyuncs.com/compatible-mode/v1 |
| LLM_MODEL | 大模型名称 | qwen-max |
| BAIDU_OCR_API_KEY | 百度OCR API Key | - |
| BAIDU_OCR_SECRET_KEY | 百度OCR Secret Key | - |
| MAX_UPLOAD_SIZE | 最大上传文件大小(bytes) | 52428800 (50MB) |
| DOCX_MAX_PAGES | DOCX最大页数 | 30 |
| PDF_MAX_PAGES | PDF最大页数 | 50 |

## 注意事项

1. V1版本无用户系统，所有接口无需认证
2. 文件临时存储24小时后自动过期
3. 生产环境部署时需要修改CORS配置
