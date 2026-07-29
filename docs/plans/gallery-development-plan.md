# Show Me Anime — 图片画廊开发计划

> 创建日期：2026-07-29  
> 状态：草案（v2 — 集合优先）  
> 后端：Python | 数据库：SQLite | 前端：Vue 3（推荐）

---

## 1. 项目目标

构建一个本地/局域网图片画廊系统，用于浏览和管理漫画、组图、风景等图片集合。核心能力：

| 能力 | 说明 |
|------|------|
| 文件夹即分类 | 图片按磁盘目录组织，支持任意深度；根目录下可同时存在「分类节点」和「叶子相册」 |
| 集合优先 | **DB 只存文件夹/压缩包级别的集合**，不逐张图片入库 |
| Web 管理 | 浏览器内浏览、搜索集合、编辑元数据、触发扫描 |
| 自动索引 | 监听或定时扫描目录树，增量写入 SQLite（仅 nodes） |
| 集合搜索 | 按相册名、路径、标签检索；**不支持单张图片搜索** |
| 自然排序 | 展示图片时按**文件名自然升序**（`1, 2, …, 10, 100` 而非 `1, 10, 100, 2`） |
| 路径可配置 | **画廊根目录**、**缩略图存储目录**均可自定义；未配置时使用项目内默认值 |

---

## 2. 技术选型

### 2.1 后端：Python + FastAPI（推荐）

| 组件 | 选型 | 理由 |
|------|------|------|
| Web 框架 | **FastAPI** | 异步 I/O、自动 OpenAPI 文档、类型提示友好、生态成熟 |
| ORM | **SQLAlchemy 2.x** | 与 SQLite 配合良好，迁移可用 Alembic |
| 数据库 | **SQLite** | 零配置、单文件；仅存目录树，体量极小 |
| 全文搜索 | **SQLite FTS5** | 仅索引集合（相册名/路径/标签），不索引图片 |
| 文件监听 | **watchdog** | 跨平台目录变更监听，配合防抖增量入库 |
| 图片处理 | **Pillow** | 按需生成缩略图 |
| 配置 | **pydantic-settings** | 类型安全的 `.env` / `config.yaml` |
| 任务调度 | **APScheduler**（可选） | 定时全量校验，补偿 watchdog 漏事件 |

### 2.2 前端：Vue 3 + Vite + Element Plus（推荐）

| 组件 | 选型 | 理由 |
|------|------|------|
| 框架 | **Vue 3 Composition API + script setup** | 组合式逻辑清晰 |
| 构建 | **Vite** | 启动快、HMR 好 |
| UI | **Element Plus** | 树形目录、网格、搜索框、分页齐全 |
| 路由 | **Vue Router** | 相册列表 / 阅读器 / 管理页 |
| 状态 | **Pinia**（按需） | 搜索条件、阅读进度 |
| HTTP | **axios** 或原生 fetch | 对接 FastAPI REST |

**推荐结论：Vue 3 + Element Plus**

### 2.3 部署形态

```
┌─────────────┐     REST/WS      ┌──────────────┐
│  Vue 前端    │ ◄──────────────► │ FastAPI 后端  │
│ (静态资源)   │                  │ + watchdog    │
└─────────────┘                  └──────┬───────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
              gallery.db         图片根目录          thumbs/
           (仅 nodes 等小表)      (只读, 源真相)     (文件缓存, 不入库)
```

- 开发：`uvicorn` 跑 API，`vite dev` 跑前端，Vite 代理 `/api`
- 生产：前端 `vite build` 后由 FastAPI 托管静态文件，或 Nginx 反代

---

## 3. 核心概念与数据模型

### 3.1 设计原则：集合优先

```
DB 存什么          磁盘/运行时读什么
─────────          ─────────────────
目录树 (nodes)  →  打开相册时 listdir / 读 zip 列表
集合元数据      →  图片二进制、顺序
标签、阅读进度  →  缩略图文件 (thumbs/ 目录缓存)
```

**不建 `images` 表**。图片列表在访问相册时从磁盘按需读取，经自然排序后返回；内存中按 `node_id + dir_mtime` 缓存列表，目录未变则复用。

### 3.2 目录语义（灵活层级）

**不强制「一级 / 二级」**，统一抽象为 **节点（Node）**：

- **容器节点（container）**：目录下还有子目录
- **相册节点（album）**：可浏览的图片集合（叶子文件夹，或根下直接含图的目录）
- **混合根目录**：根下 `漫画/` 是容器，`杂项/` 下直接是图片 → `杂项` 同时是 container 也是 album

磁盘结构示例：

```
/media/gallery/
├── 漫画/
│   ├── 长篇/
│   │   └── 作品A/          → album（内含 1.jpg … 100.jpg）
│   └── 短片/
│       └── 作品B/          → album
├── 组图/
│   └── set-001/            → album
└── 杂项/                   → album + container
    ├── 1.jpg
    └── 2.jpg
```

### 3.3 图片命名与排序约定

**排序规则（系统保证）**

- 展示顺序：**文件名自然升序**（natural sort）
- 支持 `1.jpg, 2.jpg, …, 100.jpg` 与 `0001.jpg, 0002.jpg` 混排时也能正确排序
- 不支持用户自定义排序字段；顺序完全由文件名决定

**内容准备建议（用户侧约定）**

- 建议将图片命名为可排序形式，例如 `0001.jpg` / `0002.jpg` 或 `1.jpg` / `2.jpg`
- 避免 `page1.jpg, page10.jpg, page2.jpg` 这类纯字符串排序会乱序的命名；若使用数字段，系统会用自然排序修正
- 非图片文件（`.txt`, `.nfo` 等）扫描时忽略

**自然排序实现**

```python
import re

def natural_sort_key(name: str) -> list:
    """1, 2, 10, 100 排在正确位置；也兼容 0001, 0002。"""
    return [int(p) if p.isdigit() else p.lower() for p in re.split(r'(\d+)', name)]

def sorted_image_names(filenames: list[str]) -> list[str]:
    return sorted(filenames, key=natural_sort_key)
```

### 3.4 数据库表设计（SQLite）

```sql
-- 节点：目录树 + 相册/压缩包集合
CREATE TABLE nodes (
    id              INTEGER PRIMARY KEY,
    parent_id       INTEGER REFERENCES nodes(id),
    name            TEXT NOT NULL,
    path            TEXT NOT NULL UNIQUE,   -- 相对 gallery_root
    node_type       TEXT NOT NULL,          -- 'container' | 'album'
    source_type     TEXT NOT NULL DEFAULT 'folder',  -- 'folder' | 'zip' | 'cbz'
    image_count     INTEGER DEFAULT 0,    -- 扫描时统计，非明细
    cover_rel_path  TEXT,                   -- 封面文件名，如 "0001.jpg"
    dir_mtime       REAL,                   -- 目录 mtime，用于判断列表是否过期
    created_at      REAL,
    updated_at      REAL
);

-- 标签
CREATE TABLE tags (
    id   INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE node_tags (
    node_id INTEGER REFERENCES nodes(id),
    tag_id  INTEGER REFERENCES tags(id),
    PRIMARY KEY (node_id, tag_id)
);

-- 阅读进度（按页码 index，不引用 image 表）
CREATE TABLE read_progress (
    node_id     INTEGER PRIMARY KEY REFERENCES nodes(id),
    page_index  INTEGER NOT NULL,           -- 0-based，对应排序后的列表下标
    updated_at  REAL
);

-- FTS5：仅索引集合，不索引单张图片
CREATE VIRTUAL TABLE search_index USING fts5(
    node_id UNINDEXED,
    title,
    path,
    tags,
    tokenize = 'unicode61'
);

-- 扫描状态
CREATE TABLE scan_jobs (
    id         INTEGER PRIMARY KEY,
    status     TEXT,
    started_at REAL,
    finished_at REAL,
    added      INTEGER DEFAULT 0,
    updated    INTEGER DEFAULT 0,
    removed    INTEGER DEFAULT 0,
    message    TEXT
);
```

**无 `images` 表** — 缩略图路径也不入库，仅存于 `data/thumbs/{hash}.webp` 文件系统。

### 3.5 相册判定规则

扫描时自动标记 `node_type`（Web 管理端可手动覆盖）：

1. 目录内存在图片文件 → 至少 **album**
2. 目录内还有子目录 → 同时 **container**
3. 仅含子目录、无图片 → **container**
4. 空目录 → 跳过
5. `.zip` / `.cbz` 文件 → 单条 **album** 节点，`source_type='zip'`

扫描阶段对 album 节点：统计 `image_count`、取自然排序第一张为默认 `cover_rel_path`、记录 `dir_mtime`。

---

## 4. 功能模块

### 4.1 目录扫描与实时同步

```
watchdog 事件 → 防抖队列(2~5s) → 增量扫描器 → 更新 nodes + FTS
                                      ↑
                              定时全量校验(可选)
```

**扫描器职责（仅集合级）**

- 遍历目录树，upsert/delete `nodes`
- 对 album 节点：`listdir` → 过滤图片 → 自然排序 → 写 `image_count`、`cover_rel_path`、`dir_mtime`
- **不**逐张图片写库；**不**在扫描阶段批量生成缩略图（改为访问时按需生成）
- 同步 FTS（仅 node 的 title/path/tags）

**打开相册时的列表读取**

```
GET /api/nodes/{id}/images
  → 读 nodes.dir_mtime
  → 若内存缓存有效 → 直接返回
  → 否则 listdir → natural_sort → 更新 image_count（若变化）→ 返回
```

**API**

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/scan/trigger` | 手动全量/子树扫描 |
| GET | `/api/scan/status` | 当前任务进度 |

### 4.2 浏览与阅读

| 页面 | 功能 |
|------|------|
| 首页 / 分类 | 面包屑 + 子节点卡片网格（封面、名称、张数） |
| 相册详情 | 图片网格（自然排序）、跳转阅读器 |
| 阅读器 | 全屏翻页、键盘 ←/→、缩放、预加载邻页 |
| 阅读进度 | 服务端 `read_progress` 或 localStorage |

**API**

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/nodes` | 子节点列表（`?parent_id=`） |
| GET | `/api/nodes/{id}` | 节点详情 |
| GET | `/api/nodes/{id}/images` | 图片列表（自然排序，可分页） |
| GET | `/api/nodes/{id}/images/{index}/file` | 原图（index 为排序后下标，支持 Range） |
| GET | `/api/nodes/{id}/images/{index}/thumb` | 缩略图（按需生成 + 文件缓存） |
| PUT | `/api/nodes/{id}/progress` | 保存阅读进度 `{ page_index }` |
| GET | `/api/nodes/{id}/progress` | 读取阅读进度 |

**图片列表响应示例**

```json
{
  "node_id": 12,
  "total": 100,
  "items": [
    { "index": 0, "filename": "1.jpg" },
    { "index": 1, "filename": "2.jpg" }
  ]
}
```

### 4.3 搜索（仅集合）

- 搜索框：debounce 300ms
- **范围**：相册名、路径片段、标签
- **不支持**：单张图片文件名、图片内容搜索
- FTS5：`MATCH` + `ORDER BY rank`，结果均为 album/container 节点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/search?q=&limit=&offset=` | 集合全文搜索 |

### 4.4 Web 管理

| 功能 | 说明 |
|------|------|
| 节点类型修正 | container ↔ album |
| 封面设置 | 指定排序后某 index 对应文件为封面 |
| 标签管理 | 给节点打标签 |
| 扫描控制 | 触发扫描、查看日志 |
| 路径配置 | 画廊根目录、缩略图目录（见 §7.4） |
| 其他配置 | 缩略图尺寸、监听开关 |

**配置 API**

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/settings` | 读取当前生效配置（含解析后的绝对路径） |
| PUT | `/api/settings` | 更新可热改项；变更根目录需确认并触发重扫 |

---

## 5. 项目结构（建议）

```
show-me-anime/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── db/
│   │   │   ├── session.py
│   │   │   └── models.py
│   │   ├── schemas/
│   │   ├── api/
│   │   │   ├── nodes.py
│   │   │   ├── albums.py        # 列表/原图/缩略图（按 index）
│   │   │   ├── search.py
│   │   │   └── scan.py
│   │   ├── services/
│   │   │   ├── scanner.py       # 仅扫描 nodes
│   │   │   ├── album_reader.py  # listdir/zip 列表 + 缓存
│   │   │   ├── watcher.py
│   │   │   ├── thumbnail.py     # 按需生成，写 thumbs/
│   │   │   └── search.py
│   │   └── utils/
│   │       └── natural_sort.py
│   ├── alembic/
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── views/
│   │   │   ├── home/
│   │   │   ├── album/
│   │   │   ├── reader/
│   │   │   └── admin/
│   │   ├── components/
│   │   │   ├── NodeTree.vue
│   │   │   ├── AlbumGrid.vue
│   │   │   ├── ImageViewer.vue
│   │   │   └── SearchBar.vue
│   │   └── router/
│   └── vite.config.ts
├── data/
│   ├── gallery.db
│   ├── settings.json            # Web 管理页持久化的路径配置（可选）
│   └── thumbs/                  # 默认缩略图目录（可被 THUMB_DIR 覆盖）
├── gallery/                     # 默认画廊根目录（可被 GALLERY_ROOT 覆盖）
├── .env.example
├── config.yaml.example
└── docs/plans/
```

---

## 6. 开发阶段与里程碑

### Phase 0 — 项目脚手架（约 1 天）

- [ ] 初始化 backend + frontend
- [ ] 实现 `Settings`（pydantic-settings）：画廊根目录、缩略图目录及默认值（见 §7.4）
- [ ] `.env.example` 与 `config.yaml.example`
- [ ] **验收**：`GET /api/health`；未配置时走默认路径；配置后走自定义路径

### Phase 1 — 扫描与数据层（约 2 天）

- [ ] SQLAlchemy models（nodes/tags/read_progress/search_index）
- [ ] `natural_sort` 单测：`1,2,10,100` 与 `0001,0002` 场景
- [ ] `Scanner`：全量扫描仅写 nodes + FTS
- [ ] `AlbumReader`：按需 listdir + 自然排序 + 内存缓存
- [ ] **验收**：扫描后 DB 只有 nodes；打开相册 API 返回正确排序列表

### Phase 2 — 浏览 API + 基础 UI（约 2~3 天）

- [ ] 节点树 API、图片列表 API（按 index）
- [ ] 原图/缩略图服务（路径穿越防护）
- [ ] 缩略图按需生成到 `thumbs/`
- [ ] 前端：目录树 + 相册网格 + 面包屑
- [ ] **验收**：网格顺序与磁盘自然排序一致

### Phase 3 — 阅读器（约 1~2 天）

- [ ] 全屏阅读器：index 翻页、键盘快捷键
- [ ] 邻页预加载
- [ ] 阅读进度持久化
- [ ] **验收**：100+ 页漫画翻页流畅，退出再进恢复进度

### Phase 4 — 集合搜索（约 1 天）

- [ ] FTS 搜索 API（仅 nodes）
- [ ] 前端 SearchBar + 结果页
- [ ] **验收**：按文件夹名/路径找到相册；**不能**搜到单张图片名

### Phase 5 — 实时监听（约 1 天）

- [ ] watchdog + 防抖，增量更新 nodes
- [ ] 目录变更时失效对应 album 内存缓存
- [ ] **验收**：新增文件夹后数秒内可搜索、可浏览

### Phase 6 — 管理功能（约 1~2 天）

- [ ] 封面/标签/节点类型管理
- [ ] 设置页：画廊根目录、缩略图目录表单 + 路径校验提示
- [ ] 扫描控制面板
- [ ] **验收**：改封面、打标签后搜索生效；修改路径配置后重启/重扫行为符合预期

### Phase 7 — 部署（约 1 天）

- [ ] 生产构建、README、可选 Basic 鉴权
- [ ] **验收**：一条命令启动

**预估总工期：9~13 天**（较 v1 略短，因去掉 images 表与图片搜索）

---

## 7. 关键实现细节

### 7.1 自然排序（必测用例）

| 输入文件名 | 期望顺序 |
|-----------|----------|
| `1.jpg, 2.jpg, 10.jpg, 100.jpg` | 1 → 2 → 10 → 100 |
| `0001.jpg, 0002.jpg, 0010.jpg` | 1 → 2 → 10 |
| `page1.jpg, page2.jpg, page10.jpg` | 1 → 2 → 10 |
| 混排 `1.jpg, 0002.jpg, 3.jpg` | 按数值段正确排列 |

### 7.2 安全：路径穿越防护

```python
def safe_resolve(root: Path, rel: str) -> Path:
    target = (root / rel).resolve()
    if not str(target).startswith(str(root.resolve())):
        raise ValueError("path traversal")
    return target
```

### 7.3 图片格式

支持：`.jpg` `.jpeg` `.png` `.webp` `.gif` `.bmp`

### 7.4 路径与配置

#### 7.4.1 可配置项与默认值

| 配置键 | 环境变量 | 默认值 | 说明 |
|--------|----------|--------|------|
| 画廊根目录 | `GALLERY_ROOT` | `{项目根}/gallery` | 图片/文件夹的数据源，扫描与浏览均相对此路径 |
| 缩略图目录 | `THUMB_DIR` | `{项目根}/data/thumbs` | 缩略图缓存写入位置，**必须与源图分离** |
| 数据库 | `DATABASE_URL` | `sqlite:///./data/gallery.db` | 元数据存储 |
| 缩略图最大边 | `THUMB_MAX_SIZE` | `400` | 像素 |
| 监听开关 | `WATCH_ENABLED` | `true` | watchdog |
| 监听防抖 | `WATCH_DEBOUNCE_SECONDS` | `3` | 秒 |

**规则**

- 未设置环境变量 / 配置文件字段 → 使用上表默认值
- 相对路径均相对于**项目根目录**解析为绝对路径后再使用
- 启动时校验：`GALLERY_ROOT` 必须存在且可读；`THUMB_DIR` 不存在则**自动创建**；不可写则报错
- 修改 `GALLERY_ROOT` 后需重新扫描（旧 nodes 路径失效）；修改 `THUMB_DIR` 后旧缩略图不迁移，按需重新生成

#### 7.4.2 配置来源与优先级

```
Web 管理页持久化 (data/settings.json)
        ↓ 覆盖
环境变量 (.env)
        ↓ 覆盖
config.yaml（可选）
        ↓ 覆盖
代码内默认值
```

实现上使用 `pydantic-settings`，统一管理：

```python
# backend/app/config.py 示意
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    gallery_root: Path = PROJECT_ROOT / "gallery"
    thumb_dir: Path = PROJECT_ROOT / "data" / "thumbs"
    database_url: str = f"sqlite:///{PROJECT_ROOT / 'data' / 'gallery.db'}"
    thumb_max_size: int = 400
    watch_enabled: bool = True
    watch_debounce_seconds: int = 3

    def resolve_paths(self) -> None:
        """相对路径 → 绝对路径；创建 thumb_dir。"""
        self.gallery_root = self.gallery_root.resolve()
        self.thumb_dir = self.thumb_dir.resolve()
        self.thumb_dir.mkdir(parents=True, exist_ok=True)
```

#### 7.4.3 配置文件示例

**.env.example**

```env
# 留空则使用默认值
# GALLERY_ROOT=D:/media/my-gallery
# THUMB_DIR=D:/cache/show-me-anime/thumbs

DATABASE_URL=sqlite:///./data/gallery.db
THUMB_MAX_SIZE=400
WATCH_ENABLED=true
WATCH_DEBOUNCE_SECONDS=3
ALBUM_LIST_CACHE_TTL=300
HOST=0.0.0.0
PORT=8000
```

**config.yaml.example（可选）**

```yaml
gallery_root: D:/media/my-gallery   # 不填则用默认 {项目根}/gallery
thumb_dir: D:/cache/thumbs          # 不填则用默认 {项目根}/data/thumbs
thumb_max_size: 400
watch_enabled: true
```

#### 7.4.4 典型使用场景

| 场景 | 配置方式 |
|------|----------|
| 本地试用 | 不配置，把图片放进 `./gallery/` |
| 图片在 D 盘、缩略图在 SSD 缓存盘 | `.env` 分别指定 `GALLERY_ROOT` 与 `THUMB_DIR` |
| 局域网 NAS 挂载 | `GALLERY_ROOT=//nas/photos/comics` |
| 运行时修改 | 管理页保存 → 写入 `data/settings.json` → 提示重启或触发重扫 |

---

## 8. 非功能性要求

| 项 | 目标 |
|----|------|
| DB 规模 | 1 万相册 ≈ 1 万行 nodes，与图片总数无关 |
| 单相册图片数 | 数千张可接受（listdir + 内存缓存） |
| 性能 | 缩略图懒加载；阅读器预加载；列表缓存 |
| 可移植 | 拷贝 `gallery.db` + 缩略图目录 + `.env`/`settings.json`；新机器改 `GALLERY_ROOT` 指向新位置即可 |

---

## 9. 风险与对策

| 风险 | 对策 |
|------|------|
| 超大相册（1 万+ 图）listdir 慢 | 分页 API；首次只返回 total + 前 N 项 |
| 文件名完全无数字导致顺序难控 | 文档约定 + 管理页展示当前排序预览 |
| watchdog 不稳定 | 定时扫描 + 手动扫描 |
| 缓存与磁盘不一致 | 对比 `dir_mtime` 自动失效 |
| 修改画廊根目录后索引错乱 | 提示全量重扫；可选清空 nodes 表再扫 |
| 缩略图目录无写权限 | 启动时检测并报错，管理页展示当前路径 |

---

## 10. 明确不做（v1 Out of Scope）

- 单张图片搜索 / 图片级 FTS
- 逐张图片入库（`images` 表）
- 用户自定义排序（拖拽 reorder）
- ZIP/CBZ 浏览（可 Phase 8 再加，模型已预留 `source_type`）
- AI 打标签、重复图检测

---

## 11. 建议的下一步

1. 确认图片根目录路径、是否需要鉴权
2. 执行 Phase 0 脚手架
3. 准备测试数据：含 `1~100.jpg` 自然排序、含 `0001~0050.jpg`、含乱序文件名的对照文件夹

---

## 附录 A — 依赖清单

**backend/requirements.txt**

```
fastapi>=0.115
uvicorn[standard]>=0.32
sqlalchemy>=2.0
alembic>=1.14
pydantic-settings>=2.6
pillow>=11.0
watchdog>=6.0
apscheduler>=3.10
python-multipart>=0.0.12
pytest>=8.0
httpx>=0.28
```

**frontend（核心）**

```
vue ^3.5
vue-router ^4.5
element-plus ^2.9
axios ^1.7
vite ^6.0
typescript ^5.7
```

---

## 附录 B — API 一览（v1）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/settings` | 当前配置（含默认/自定义路径） |
| PUT | `/api/settings` | 更新路径等配置 |
| GET | `/api/nodes` | 子节点 |
| GET | `/api/nodes/{id}` | 节点详情 |
| PATCH | `/api/nodes/{id}` | 更新类型/封面 |
| GET | `/api/nodes/{id}/images` | 自然排序图片列表 |
| GET | `/api/nodes/{id}/images/{index}/file` | 原图 |
| GET | `/api/nodes/{id}/images/{index}/thumb` | 缩略图 |
| GET/PUT | `/api/nodes/{id}/progress` | 阅读进度 |
| GET | `/api/search` | 集合搜索（不含图片） |
| POST | `/api/scan/trigger` | 触发扫描 |
| GET | `/api/scan/status` | 扫描状态 |
| GET/POST/DELETE | `/api/tags` | 标签 |
| POST | `/api/nodes/{id}/tags` | 节点打标 |
