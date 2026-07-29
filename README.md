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

## 技术栈（计划）

| 层级 | 选型 |
|------|------|
| 后端 | Python + FastAPI |
| 数据库 | SQLite + FTS5 |
| 前端 | Vue 3 + Vite + Element Plus |

## 快速开始

> 项目尚在规划阶段，以下为预期用法。

```bash
# 克隆
git clone git@github.com:newShak/show-me-anime.git
cd show-me-anime

# 后端（待实现）
python -m venv .venv
.venv\Scripts\activate
pip install -r backend/requirements.txt

# 前端（待实现）
cd frontend && npm install && npm run dev
```

## 配置

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `GALLERY_ROOT` | `./gallery` | 图片根目录 |
| `THUMB_DIR` | `./data/thumbs` | 缩略图缓存目录 |

未配置时使用默认值。可将图片放入 `./gallery/` 目录进行试用。

## 许可证

MIT
