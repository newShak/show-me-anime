# show-me-anime

本地图片画廊，用于浏览和管理漫画、组图等按文件夹组织的图片集合。

## 功能规划

- 以文件夹 / 压缩包为集合单位组织内容
- Web 页面浏览与管理
- 自动扫描目录并索引到 SQLite
- 集合级搜索（相册名、路径、标签）
- 图片按文件名自然排序展示
- 可配置画廊根目录与缩略图存储路径

详细开发计划见 [docs/plans/gallery-development-plan.md](docs/plans/gallery-development-plan.md)。

## 技术栈

| 层级 | 选型 |
|------|------|
| 后端 | Python + FastAPI |
| 数据库 | SQLite + FTS5 |
| 前端 | Vue 3 + Vite + Element Plus |

## 快速开始

### 1. 后端

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r backend/requirements.txt

# 启动 API（默认 http://127.0.0.1:8000）
cd backend
..\.venv\Scripts\uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. 前端

```bash
cd frontend
npm install
npm run dev
```

浏览器打开 http://127.0.0.1:5173 ，首页会显示后端连接状态与当前配置。

### 4. 扫描与浏览（Phase 1）

```bash
# 将图片放入 gallery/ 目录，例如 gallery/comic-a/1.jpg
# 触发扫描
curl -X POST http://127.0.0.1:8000/api/scan/trigger

# 查看顶层分类/相册
curl http://127.0.0.1:8000/api/nodes

# 查看相册内图片列表（自然排序）
curl http://127.0.0.1:8000/api/nodes/{id}/images
```

### 3. 测试

```bash
cd backend
..\.venv\Scripts\pytest -q
```

## 配置

复制 `.env.example` 为 `.env`，或复制 `config.yaml.example` 为 `config.yaml`。

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `GALLERY_ROOT` | `./gallery` | 图片根目录 |
| `THUMB_DIR` | `./data/thumbs` | 缩略图缓存目录 |

未配置时使用默认值。可将图片放入 `./gallery/` 目录进行试用。

配置优先级：`data/settings.json` > `.env` > `config.yaml` > 默认值。

## 许可证

MIT
