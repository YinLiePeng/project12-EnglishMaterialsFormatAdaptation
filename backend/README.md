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
│   │   ├── database.py   # 数据库连接
│   │   └── presets/
│   │       └── styles.py # 8套预设排版样式
│   ├── models/
│   │   ├── task.py       # 任务模型
│   │   ├── template.py   # 模板模型
│   │   └── site_stats.py # 统计模型
│   ├── api/
│   │   └── v1/
│   │       └── endpoints/
│   │           ├── health.py   # 健康检查
│   │           ├── upload.py   # 文件上传
│   │           ├── tasks.py    # 任务管理
│   │           ├── testcase.py # 测试用例收集
│   │           └── hybrid.py   # Hybrid PDF服务
│   ├── services/
│   │   ├── processor.py        # 文档处理核心编排
│   │   ├── cleaner.py          # 内容清洗
│   │   ├── docx/               # DOCX处理
│   │   │   ├── parser.py       # DOCX解析器
│   │   │   ├── generator.py    # DOCX生成器
│   │   │   ├── rule_engine.py  # 规则引擎
│   │   │   └── template_*.py   # 模板处理
│   │   ├── pdf/                # PDF处理
│   │   │   ├── parser.py       # PDF解析器(opendataloader_pdf)
│   │   │   ├── enhanced_parser.py # 增强解析器(标准/Hybrid)
│   │   │   └── detector.py     # PDF类型检测
│   │   ├── llm/                # 大模型服务
│   │   │   ├── client.py       # DeepSeek客户端
│   │   │   └── hybrid_recognizer.py
│   │   ├── ocr/                # OCR服务
│   │   ├── correction/         # 内容纠错
│   │   └── revision/           # Word修订/批注
│   └── utils/
├── alembic/              # 数据库迁移
├── core/dictionary/      # 词典数据(oxford.json, gaokao.json)
├── prompts.yaml          # LLM prompt模板
├── tests/
│   ├── comparison/       # DOCX对比评价体系(见下方文档)
│   └── test_*.py         # 其他测试
├── requirements.txt
├── .env.example
└── alembic.ini
```

## API端点

### 健康检查
- `GET /api/v1/health` - 基础健康检查
- `GET /api/v1/health/detail` - 详细健康检查

### 文件上传
- `POST /api/v1/upload` - 上传文件并创建处理任务
- `POST /api/v1/upload/template-preview` - 上传模板获取HTML预览
- `GET /api/v1/upload/presets` - 获取预设样式列表

### 任务管理
- `GET /api/v1/tasks` - 获取任务列表(支持筛选/排序/分页)
- `GET /api/v1/tasks/{task_id}` - 查询任务状态
- `GET /api/v1/tasks/{task_id}/download` - 下载处理结果
- `DELETE /api/v1/tasks/{task_id}` - 取消任务
- `POST /api/v1/tasks/delete-batch` - 批量删除
- `GET /api/v1/tasks/statistics/summary` - 任务统计
- `GET /api/v1/tasks/{task_id}/llm-stream` - SSE流式LLM处理
- `POST /api/v1/tasks/{task_id}/quick-correction` - 手动修正段落类型
- `POST /api/v1/tasks/{task_id}/ai-recognize` - AI重新识别
- `POST /api/v1/tasks/{task_id}/regenerate` - 重新生成文档

### 测试用例收集
- `POST /api/v1/testcase/submit` - 提交测试用例
- `GET /api/v1/testcase/list` - 获取测试用例列表
- `GET /api/v1/testcase/{id}` - 获取详情
- `DELETE /api/v1/testcase/{id}` - 删除
- `PUT /api/v1/testcase/{id}/status` - 更新状态

### Hybrid PDF服务
- `GET /api/v1/hybrid/status` - 服务状态
- `POST /api/v1/hybrid/start` - 启动服务
- `POST /api/v1/hybrid/stop` - 停止服务

---

## DOCX对比评价体系

### 概述

`tests/comparison/` 目录下实现了一套**DOCX全面对比评价体系**，用于量化评估PDF→DOCX转换效果。这是**优化工作的核心度量工具**——所有优化都应该基于这个评价体系的输出结果来指导方向和验证效果。

**核心原则**: 优化前先跑一遍评价，得到基线分数；优化后再跑一遍，对比分数变化。没有数据支撑的优化是盲目的。

### 运行方法

```bash
cd backend
venv/bin/python tests/comparison/run_comparison.py
```

运行前确保：
1. `测试用例/原生PDF/` 下有19个测试PDF
2. `测试用例/网上下载的英语资料样例/` 下有对应的19个参考DOCX（文件名一一对应）
3. 已安装所有依赖（`pip install -r requirements.txt`）

### 输出

运行后会生成：
1. **控制台摘要表格** — 每个文件的总分和各维度分数
2. **JSON详细报告** — `data/comparison_output/comparison_report.json`

JSON报告结构：
```json
{
  "summary": {
    "total_files": 19,
    "successful": 19,
    "avg_overall_score": 0.783,
    "min_overall_score": 0.606,
    "max_overall_score": 0.869
  },
  "dimension_averages": {
    "text_content": { "avg": 0.828, "min": 0.637, "max": 0.957 },
    "font_formatting": { "avg": 0.906, "min": 0.667, "max": 0.993 },
    ...
  },
  "files": [
    {
      "file_name": "xxx.pdf",
      "overall_score": 0.869,
      "dimensions": {
        "text_content": { "score": 0.957, "details": { ... } },
        "font_formatting": { "score": 0.945, "details": { ... } },
        ...
      }
    }
  ]
}
```

### 11个对比维度详解

每个维度输出 `[0.0, 1.0]` 的分数，最终加权汇总为总分。

| 维度 | 权重 | 测量什么 | 低分意味着什么 |
|------|------|----------|----------------|
| **text_content** | 20% | 文字内容的准确性 | PDF解析丢失/错乱了文字内容 |
| **paragraph_structure** | 10% | 段落数量、匹配率、格式属性序列 | 段落被拆分/合并，或格式属性差异大 |
| **font_formatting** | 12% | 字体名、字号、加粗、斜体、下划线、颜色 | 字体信息在PDF→DOCX过程中丢失或转换错误 |
| **paragraph_formatting** | 10% | 对齐方式、行距、段前段后距、缩进 | 段落排版参数未正确保留 |
| **list_numbering** | 5% | Word原生编号格式 | 编号被当作纯文本而非Word编号 |
| **table_comparison** | 13% | 表格数量、行列数、单元格内容、列宽、合并 | PDF解析器未正确提取表格 |
| **image_comparison** | 8% | 图片数量、尺寸、MD5哈希 | PDF解析器未正确提取图片 |
| **headers_footers** | 5% | 页眉页脚文本内容 | PDF解析器不提取页眉页脚 |
| **page_layout** | 5% | 纸张大小、页边距 | 页面设置未正确保留 |
| **document_structure** | 7% | 元素类型分布、格式签名分布、标题层级 | 文档整体结构差异大 |
| **style_system** | 5% | 字体/字号/对齐方式的使用分布 | 样式应用策略与参考文件不一致 |

### 如何解读评价结果

#### 第一步：看总分和各维度平均分

```
平均  78.3  82.8  85.9  90.6  68.2  100.0  76.2  60.6  44.5  81.5  85.1  68.3
```

- **>80%** 的维度：表现良好，暂不需要优化
- **60-80%** 的维度：有改进空间，优先级中等
- **<60%** 的维度：需要重点关注，是优化的主要方向

#### 第二步：看单个文件的低分维度

找到总分最低的文件，看它的哪个维度拖了后腿：

```
Unit 3 Food 基础过关练...    61.9    81.4    73.5    99.1    69.0   100.0     0.0     0.0    39.5    93.6    70.9    57.6
```

这个文件 `table_comparison: 0.0` 和 `image_comparison: 0.0`，说明PDF解析器完全没有提取到表格和图片。

#### 第三步：看details中的具体差异

JSON报告中每个维度都有 `details` 字段，包含具体的差异信息：

```json
"text_content": {
  "score": 0.637,
  "details": {
    "overall_similarity": 0.602,
    "paragraph_similarity": 0.800,
    "matched_paragraph_count": 38,
    "unmatched_gen_count": 0,
    "unmatched_ref_count": 38,
    "worst_paragraphs": [
      {"gen_text": "...", "ref_text": "...", "similarity": 0.45}
    ]
  }
}
```

- `worst_paragraphs`：列出得分最低的段落对，直接告诉你哪些内容差异最大
- `unmatched_gen_count` / `unmatched_ref_count`：未匹配的段落数量
- `property_match_rates`：各属性的匹配率（用于字体/段落格式维度）

### 如何基于评价结果做优化

#### 优化流程

```
1. 运行评价，得到基线分数
2. 找到最低分维度（如 table_comparison: 0%）
3. 分析原因（PDF解析器未提取表格）
4. 修改代码（改进PDF表格提取逻辑）
5. 重新运行评价，验证分数是否提升
6. 如果提升，提交代码；如果没有，回退并重新分析
```

#### 常见低分原因和优化方向

| 低分维度 | 常见原因 | 优化方向 |
|----------|----------|----------|
| text_content < 70% | PDF解析丢失文字、OCR识别错误 | 检查 `pdf/parser.py` 的文本提取逻辑 |
| font_formatting < 80% | 字体名映射错误、字号转换错误 | 检查 `pdf/parser.py` 的 `FontMapper` |
| paragraph_formatting < 60% | 行距单位转换错误（auto倍数 vs exact磅数） | 检查 `docx/generator.py` 的格式应用逻辑 |
| table_comparison < 50% | PDF表格未被提取 | 检查 `pdf/parser.py` 的表格提取逻辑 |
| image_comparison < 50% | PDF图片未被提取 | 检查 `pdf/parser.py` 的图片提取逻辑 |
| headers_footers < 30% | PDF不提取页眉页脚 | 需要在 `pdf/parser.py` 中增加页眉页脚提取 |
| document_structure < 50% | 元素类型分布差异大 | 检查PDF解析是否遗漏了某些元素类型 |
| style_system < 50% | 字体/字号分布差异大 | 检查样式应用策略是否合理 |

#### 优化验证示例

```bash
# 1. 记录优化前的分数
venv/bin/python tests/comparison/run_comparison.py > before.txt

# 2. 修改代码（如改进PDF表格提取）
# ... 编辑 app/services/pdf/parser.py ...

# 3. 记录优化后的分数
venv/bin/python tests/comparison/run_comparison.py > after.txt

# 4. 对比变化
# 总分: 78.3% → 82.1% (+3.8%)
# table_comparison: 76.2% → 89.5% (+13.3%)  ← 有效优化
# text_content: 82.8% → 81.5% (-1.3%)       ← 注意回归！
```

**重要**: 如果某个维度分数下降，说明优化引入了回归。需要检查是否影响了其他维度。

### 代码架构

```
tests/comparison/
├── run_comparison.py           # 入口脚本（运行这个）
├── pipeline_runner.py          # PDF→DOCX管道执行器
├── docx_comparator.py          # 核心对比器（调用11个维度）
├── paragraph_matcher.py        # 段落三级匹配器
├── run_matcher.py              # Run级文本匹配器
├── font_utils.py               # 字体名/颜色工具函数
├── scoring.py                  # 加权评分引擎
├── report_generator.py         # JSON + 控制台报告生成
└── dimensions/                 # 11个对比维度
    ├── base.py                 # 维度基类（定义compare接口）
    ├── text_content.py         # 文字内容
    ├── paragraph_structure.py  # 段落结构
    ├── font_formatting.py      # 字体格式
    ├── paragraph_formatting.py # 段落格式
    ├── list_numbering.py       # 列表编号
    ├── table_comparison.py     # 表格
    ├── image_comparison.py     # 图片
    ├── headers_footers.py      # 页眉页脚
    ├── page_layout.py          # 页面布局
    ├── document_structure.py   # 文档结构
    └── style_system.py         # 样式体系
```

### 添加新维度

如果需要对比新的属性，按以下步骤添加：

1. 在 `dimensions/` 下创建新文件，继承 `ComparisonDimension`
2. 实现 `compare()` 方法，返回 `(score, details)` 元组
3. 在 `dimensions/__init__.py` 中注册
4. 在 `docx_comparator.py` 中添加到 `self.dimensions` 列表
5. 在 `docx_comparator.py` 的 `weight_map` 中设置权重（所有权重之和应为1.0）
6. 运行评价验证新维度正常工作

```python
# dimensions/my_new_dimension.py
from .base import ComparisonDimension

class MyNewDimension(ComparisonDimension):
    name = "my_new_dimension"
    weight = 0.05
    description = "我的新对比维度"

    def compare(self, gen_elements, ref_elements, gen_path, ref_path, match_result=None):
        # 实现对比逻辑
        score = 0.85
        details = {"key": "value"}
        return score, details
```

### 修改评分权重

在 `docx_comparator.py` 的 `weight_map` 中修改：

```python
weight_map = {
    "text_content": 0.20,      # 文字内容
    "paragraph_structure": 0.10, # 段落结构
    "font_formatting": 0.12,    # 字体格式
    "paragraph_formatting": 0.10, # 段落格式
    "list_numbering": 0.05,     # 列表编号
    "table_comparison": 0.13,   # 表格
    "image_comparison": 0.08,   # 图片
    "headers_footers": 0.05,    # 页眉页脚
    "page_layout": 0.05,        # 页面布局
    "document_structure": 0.07, # 文档结构
    "style_system": 0.05,       # 样式体系
}
```

权重调整原则：
- 对用户视觉体验影响大的维度给更高权重（如文字内容、表格）
- 纯技术属性的维度给较低权重（如样式体系）
- 所有权重之和必须为 1.0

---

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
# 运行所有测试
pytest tests/ -v

# 运行PDF解析测试
pytest tests/test_pdf_parser.py -v

# 运行PDF全流程测试
pytest tests/test_processor_pdf.py -v
```

### 运行DOCX对比评价

```bash
# 完整评价（处理19个PDF + 对比）
venv/bin/python tests/comparison/run_comparison.py

# 评价报告位置
data/comparison_output/comparison_report.json
```

## 配置说明

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| DATABASE_URL | 数据库连接URL | sqlite+aiosqlite:///./data/english_tool.db |
| LLM_API_KEY | 大模型API密钥 | - |
| LLM_BASE_URL | 大模型API地址 | https://api.deepseek.com |
| LLM_MODEL | 大模型名称 | deepseek-chat |
| BAIDU_OCR_API_KEY | 百度OCR API Key | - |
| BAIDU_OCR_SECRET_KEY | 百度OCR Secret Key | - |
| MAX_UPLOAD_SIZE | 最大上传文件大小(bytes) | 52428800 (50MB) |
| DOCX_MAX_PAGES | DOCX最大页数 | 30 |
| PDF_MAX_PAGES | PDF最大页数 | 50 |
| MAX_REVISIONS | 最大修订数量 | 500 |
| LLM_MAX_TOKENS | LLM单次调用最大Token数 | 20000 |

## 注意事项

1. V1版本无用户系统，所有接口无需认证
2. 文件临时存储24小时后自动过期
3. 生产环境部署时需要修改CORS配置
4. PDF→DOCX转换使用 `preserve` 模式（保留原格式）+ 规则引擎（无LLM）
5. 评价体系的19个测试用例覆盖小学到高中的上海英语教材
