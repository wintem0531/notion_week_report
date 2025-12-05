# 📝 Notion 自动周报生成工具

从 Notion 任务跟踪器自动生成周报，使用 DeepSeek AI 进行内容总结和润色。

## ✨ 功能特性

- 🔄 **自动获取任务**: 从 Notion "任务跟踪器" 数据库获取本周任务
- 🤖 **AI 智能总结**: 使用 DeepSeek API 自动总结和润色周报内容
- 📅 **定时执行**: 支持配置定时任务（默认每周五 16:30）
- 🖱️ **手动触发**: 支持随时手动生成周报
- 📤 **自动发布**: 自动将周报发布到 Notion "周报" 数据库
- 🐳 **Docker 支持**: 支持 Docker 容器化部署

## 📋 前置要求

- Python >= 3.12
- [uv](https://docs.astral.sh/uv/) 包管理器
- Notion Integration Token
- DeepSeek API Key

## 🚀 快速开始

### 方式一：本地运行

#### 1. 安装依赖

```bash
uv sync
```

#### 2. 配置

复制配置文件示例：

```bash
cp config.example.yaml config.yaml
```

编辑 `config.yaml`，填入你的配置：

```yaml
notion:
  token: "secret_your_notion_token"

deepseek:
  api_key: "sk-your_deepseek_key"
```

#### 3. 运行

```bash
# 预览本周任务（测试连接）
uv run python -m notion_week_report.main --preview

# 手动生成周报
uv run python -m notion_week_report.main --run

# 启动定时任务调度器
uv run python -m notion_week_report.main --schedule
```

---

### 方式二：Docker 部署（推荐）

#### 1. 准备配置文件

```bash
# 创建配置目录
mkdir -p config

# 复制配置文件
cp config.example.yaml config/config.yaml

# 编辑配置文件
vim config/config.yaml
```

#### 2. 使用 Docker Compose 启动

```bash
# 构建并启动（后台运行）
docker compose up -d --build

# 查看日志
docker compose logs -f

# 停止服务
docker compose down
```

#### 3. Docker 常用命令

```bash
# 手动触发生成周报
docker compose run --rm notion-week-report --run --config /app/config/config.yaml

# 预览本周任务
docker compose run --rm notion-week-report --preview --config /app/config/config.yaml

# 查看运行状态
docker compose ps

# 重启服务
docker compose restart
```

#### 4. 单独使用 Docker（不使用 Compose）

```bash
# 构建镜像
docker build -t notion-week-report .

# 运行定时任务
docker run -d \
  --name notion-week-report \
  -v $(pwd)/config:/app/config:ro \
  -e TZ=Asia/Shanghai \
  --restart unless-stopped \
  notion-week-report

# 手动触发
docker run --rm \
  -v $(pwd)/config:/app/config:ro \
  notion-week-report --run --config /app/config/config.yaml
```

---

## 🔑 获取 Token

### 获取 Notion Token

1. 访问 [Notion Integrations](https://www.notion.so/my-integrations)
2. 创建新的 Integration
3. 复制 Internal Integration Token
4. 在 Notion 中，打开 "个人任务计划" 页面
5. 点击右上角 `...` → `连接` → 添加你创建的 Integration

### 获取 DeepSeek API Key

1. 访问 [DeepSeek Platform](https://platform.deepseek.com/)
2. 注册账号并创建 API Key

---

## ⚙️ 配置说明

配置文件使用 YAML 格式，完整配置示例：

```yaml
# Notion 配置
notion:
  token: "secret_xxx"                              # 必填
  task_tracker_database_id: "xxx"                  # 任务跟踪器数据库 ID
  weekly_report_database_id: "xxx"                 # 周报数据库 ID

# DeepSeek 配置
deepseek:
  api_key: "sk-xxx"                                # 必填
  base_url: "https://api.deepseek.com"             # API 地址
  model: "deepseek-chat"                           # 模型名称

# 定时任务配置
schedule:
  day: "friday"                                    # 执行日期
  time: "16:30"                                    # 执行时间

# 周报生成配置
report:
  include_in_progress: true                        # 包含进行中的任务
  include_completed: true                          # 包含已完成的任务
```

### 配置项说明

| 配置项 | 说明 | 默认值 |
|-------|------|--------|
| `notion.token` | Notion Integration Token | 必填 |
| `notion.task_tracker_database_id` | 任务跟踪器数据库 ID | 已预填充 |
| `notion.weekly_report_database_id` | 周报数据库 ID | 已预填充 |
| `deepseek.api_key` | DeepSeek API Key | 必填 |
| `deepseek.base_url` | DeepSeek API 地址 | `https://api.deepseek.com` |
| `deepseek.model` | 使用的模型 | `deepseek-chat` |
| `schedule.day` | 定时执行日期 | `friday` |
| `schedule.time` | 定时执行时间 | `16:30` |
| `report.include_in_progress` | 包含进行中的任务 | `true` |
| `report.include_completed` | 包含已完成的任务 | `true` |

---

## 📁 项目结构

```
notion_week_report/
├── src/notion_week_report/
│   ├── __init__.py          # 包初始化
│   ├── main.py              # 主入口（CLI 命令）
│   ├── config.py            # 配置管理（YAML）
│   ├── notion_client.py     # Notion API 客户端
│   ├── deepseek_client.py   # DeepSeek API 客户端
│   ├── report_generator.py  # 周报生成逻辑
│   └── scheduler.py         # 定时任务调度
├── config/                  # Docker 配置目录
│   └── config.yaml          # 配置文件（需自行创建）
├── config.example.yaml      # 配置文件示例
├── Dockerfile               # Docker 镜像定义
├── docker-compose.yml       # Docker Compose 配置
├── pyproject.toml           # 项目配置和依赖
└── README.md                # 说明文档
```

---

## 🔧 任务筛选逻辑

工具会自动筛选符合以下条件的任务：

1. **状态**: 进行中 或 已完成（可配置）
2. **时间**: 更新时间在本周内（周一至周日）

---

## 📝 生成的周报格式

```markdown
## 本周工作总结

### 已完成工作
- 工作项1：简要描述成果
- 工作项2：简要描述成果

### 进行中工作
- 工作项1：当前进度说明
- 工作项2：当前进度说明

### 下周计划
- 基于进行中的工作，简要说明下周重点
```

---

## 🐛 常见问题

### Q: 获取不到任务？

1. 确认 Notion Integration 已连接到 "个人任务计划" 页面
2. 确认本周有更新过的任务（状态为进行中或已完成）
3. 使用 `--preview` 命令查看能获取到哪些任务

### Q: DeepSeek API 调用失败？

1. 确认 API Key 正确
2. 确认账户有足够余额
3. 检查网络连接

### Q: Docker 容器时区不对？

确保在 `docker-compose.yml` 中设置了正确的时区：

```yaml
environment:
  - TZ=Asia/Shanghai
```

### Q: 如何查看 Docker 容器日志？

```bash
docker compose logs -f
```

---

## 📄 License

MIT License
