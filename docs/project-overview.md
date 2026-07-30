# Show Me Anime — 项目说明

本地/局域网图片画廊系统，用于浏览和管理按文件夹或压缩包组织的漫画、组图等图片集合。

---

## 1. 项目简介

| 项 | 说明 |
|----|------|
| 定位 | 个人图库管理 + Web 浏览 |
| 数据源 | 磁盘目录树 + ZIP 压缩包（只读，不入库二进制） |
| 索引粒度 | **集合级**（文件夹 / 压缩包），不逐张图片入库 |
| 部署 | 单容器 Docker，FastAPI 托管 Vue 静态资源 |

---

## 2. 设计思路

### 2.1 集合优先（Collection-first）

```
磁盘（真相源）              数据库（索引）
─────────────              ──────────────
目录树 / ZIP 内文件列表  →  nodes 表（集合元数据）
图片二进制               →  不存储
缩略图                   →  thumbs/ 文件缓存
标签、阅读进度           →  tags / node_tags / read_progress
全文搜索                 →  search_index (FTS5)
```

**为什么不建 `images` 表？**

- 图库规模大时，逐张入库维护成本高
- 图片列表在打开相册时从磁盘按需读取即可
- 用 `dir_mtime` + 内存 TTL 缓存列表，目录未变则复用

### 2.2 灵活目录语义

不强制「一级分类 / 二级相册」，统一抽象为 **Node（节点）**：

| node_type | 含义 |
|-----------|------|
| `container` | 仅有子目录/压缩包，本层无直接图片 |
| `album` | 可浏览的图片集合（叶子文件夹或 ZIP） |
| `both` | 同时含子目录和直接图片 |

示例：

```
gallery/
├── 漫画/              → container（子目录有内容）
│   └── 作品A/         → album（1.jpg … 100.jpg）
├── 杂项/              → both（根下直接有图，也有子文件夹）
└── 单行本.zip         → album（source_type=zip）
```

### 2.3 磁盘只读、DB 可删

- 扫描**只读**画廊目录，写入 SQLite 索引
- 管理页「删除节点」仅删 **DB 记录**（及关联标签/进度/搜索索引），**不删磁盘文件**
- 缩略图为衍生数据，可「重建缩略图」整目录清除后按需再生

### 2.4 增量扫描

全量 walk 仍遍历目录树，但对**未变更**的节点用 `dir_mtime` 短路：

- 增量模式：`mtime` 一致且不在 watchdog 热路径 → 复用 DB 元数据，跳过深层分析
- 热路径：watchdog 上报的变更路径及其祖先目录强制重分析
- ZIP：扫描阶段额外用内存 zip 列表缓存，避免重复解压列目录

### 2.5 容器封面继承

纯 `container` 且 `image_count=0` 的节点，扫描后从**第一个有封面的子节点**继承封面路径：

- 子文件夹：`{子目录名}/{cover_rel_path}`
- 子 ZIP：`{压缩包文件名}::{cover_rel_path}`

用于网格展示时容器也有缩略图。

### 2.6 Watchdog 防抖

- `watchdog` 递归监听 `GALLERY_ROOT`
- 忽略只读 `opened` / `closed_no_write` 事件（扫描 walk 读文件会触发）
- 扫描进行中 + 扫描结束后 cooldown 内忽略事件
- 防抖合并后触发**增量扫描**，并传入 `changed_paths` 热路径

---

## 3. 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Browser (Vue 3 SPA)                     │
│  浏览 / 阅读器 / 搜索 / 管理(配置·标签·任务记录)              │
└───────────────────────────┬─────────────────────────────────┘
                            │ REST /api/*
┌───────────────────────────▼─────────────────────────────────┐
│                     FastAPI (backend)                          │
│  nodes · search · tags · scan · settings · tasks · health   │
├──────────────┬──────────────┬──────────────┬────────────────┤
│ Scanner      │ AlbumReader  │ Thumbnail    │ Watcher        │
│ (索引)       │ (按需列图)   │ (Pillow)     │ (watchdog)     │
└──────┬───────┴──────┬───────┴──────┬───────┴────────┬───────┘
       │              │              │                │
       ▼              ▼              ▼                ▼
  gallery.db      GALLERY_ROOT    THUMB_DIR      inotify 事件
  (SQLite+FTS5)   (源文件只读)    (webp 缓存)
```

**技术栈**

| 层级 | 选型 |
|------|------|
| 后端 | Python 3.12 · FastAPI · SQLAlchemy 2.x |
| 数据库 | SQLite + FTS5 虚拟表 |
| 文件监听 | watchdog 6.x |
| 图片 | Pillow（缩略图 WebP） |
| 前端 | Vue 3 · Vite · Element Plus · TypeScript |
| 配置 | pydantic-settings · `.env` / `config.yaml` / `data/settings.json` |

---

## 4. 数据模型

### 4.1 ER 关系

```
nodes (自关联 parent_id)
  ├── node_tags ── tags
  ├── read_progress
  └── search_index (FTS5, node_id)

scan_jobs        ← 扫描任务记录
task_logs        ← 其他管理任务（如重建缩略图）
```

### 4.2 表结构

#### `nodes` — 集合索引

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | |
| parent_id | INTEGER FK | 父节点，根为 NULL |
| name | TEXT | 显示名（目录名或 ZIP 去后缀名） |
| path | TEXT UNIQUE | 相对 `GALLERY_ROOT` 的路径，根为空字符串 |
| node_type | TEXT | `container` / `album` / `both` |
| source_type | TEXT | `folder` / `zip` |
| image_count | INTEGER | 集合内图片数量（扫描或读盘时更新） |
| subdir_count | INTEGER | 子目录数量 |
| cover_rel_path | TEXT | 封面：文件夹内相对路径；ZIP 内 entry；继承时为 `子名/...` 或 `a.zip::entry` |
| dir_mtime | REAL | 目录或 ZIP 的 mtime，用于增量判断 |
| created_at / updated_at | REAL | Unix 时间戳 |

#### `tags` / `node_tags`

- 标签名全局唯一
- 多对多：一个节点可打多个标签
- 标签变更时同步更新 FTS 索引中的 `tags` 列

#### `read_progress`

| 字段 | 说明 |
|------|------|
| node_id | PK，FK → nodes |
| page_index | 当前阅读页（0-based） |
| updated_at | 最后更新时间 |

#### `search_index` (FTS5 虚拟表)

| 列 | 索引 |
|----|------|
| node_id | UNINDEXED |
| title | ✅ 节点名 |
| path | ✅ 相对路径 |
| tags | ✅ 空格拼接的标签名 |

#### `scan_jobs` — 扫描记录

| 字段 | 说明 |
|------|------|
| status | `running` / `done` / `failed` |
| source | `manual` / `api` / `watchdog` |
| mode | `incremental` / `full` |
| added / updated / removed | 本次扫描统计 |
| started_at / finished_at | Unix 时间戳 |

#### `task_logs` — 其他任务

| task_type | 说明 |
|-----------|------|
| `rebuild_thumbs` | 清除缩略图缓存 |

---

## 5. 扫描流程

```
触发源: API / watchdog / (预留 manual)
    │
    ▼
run_scan(source, mode, changed_paths?)
    │ 全局锁，409 若已有扫描
    ▼
Scanner.scan_all()
    ├─ walk GALLERY_ROOT
    ├─ 每个目录 → _analyze_dir
    ├─ 每个 .zip  → _analyze_archive
    ├─ 增量: mtime 未变且非热路径 → 跳过
    ├─ 对比 DB: added / updated / removed
    ├─ sync_node_search_index (变更节点)
    ├─ _apply_container_covers
    └─ 更新 scan_jobs 状态
```

**扫描范围**：仅索引**文件夹**与**压缩包**节点，不递归索引单张图片文件为独立节点。

---

## 6. 图片读取

### 6.1 列表

`AlbumReader.list_images(node)`：

1. 文件夹：`iterdir` + 图片扩展名过滤 + **自然排序**（`1, 2, 10` 而非 `1, 10, 2`）
2. ZIP：`list_archive_images` 列 entry + 自然排序
3. 缓存：`node_id → { dir_mtime, filenames, cached_at }`，TTL 由 `album_list_cache_ttl` 控制

### 6.2 原图 / 缩略图

| 端点 | 行为 |
|------|------|
| `.../images/{index}/file` | 文件夹 `FileResponse`；ZIP 读入内存 `Response` |
| `.../images/{index}/thumb` | Pillow 生成 WebP，缓存到 `THUMB_DIR` |
| `.../cover/thumb` | 解析 `cover_rel_path`（含继承路径）后同上 |

路径解析含 **目录遍历防护**（`resolve` 后必须在画廊根或节点目录内）。

---

## 7. REST API

Base URL: `/api`  
开发时 Vite 代理 `/api` → 后端；生产由 FastAPI 同域托管。

### 7.1 健康检查

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | `{ "status": "ok" }` |

### 7.2 节点与相册

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/nodes?parent_id=&sort_by=&sort_order=` | 子节点列表；`parent_id` 省略为根 |
| GET | `/nodes/{id}` | 单个节点 |
| PATCH | `/nodes/{id}` | 更新 `node_type` / `cover_rel_path` / `cover_index` |
| POST | `/nodes/batch-delete` | 批量删 DB 记录 `{ ids: number[] }` |
| GET | `/nodes/{id}/images` | 图片文件名列表（含 index） |
| GET | `/nodes/{id}/images/{index}/file` | 原图 |
| GET | `/nodes/{id}/images/{index}/thumb` | 缩略图 WebP |
| GET | `/nodes/{id}/cover/thumb` | 封面缩略图 |
| GET | `/nodes/{id}/progress` | 阅读进度 |
| PUT | `/nodes/{id}/progress` | 保存进度 `{ page_index }` |
| GET | `/nodes/progress?ids=1,2,3` | 批量读进度 |

**排序**：`sort_by` = `name` | `mtime`；`sort_order` = `asc` | `desc`

**NodeResponse 字段**：`id, parent_id, name, path, node_type, source_type, image_count, subdir_count, cover_rel_path`

### 7.3 搜索

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/search?q=&tags=&limit=&offset=` | FTS + 标签过滤 |

- `q`：全文关键词（标题/路径/标签）
- `tags`：逗号分隔 tag id，**OR** 关系
- `q` 与 `tags` 至少提供一个

### 7.4 标签

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/tags` | 全部标签 |
| GET | `/tags/paged?page=&pageSize=` | 分页 |
| POST | `/tags` | 创建 `{ name }` |
| DELETE | `/tags/{id}` | 删除标签（同时移除关联） |
| GET | `/tags/nodes/{node_id}` | 节点标签 |
| PUT | `/tags/nodes/{node_id}` | 覆盖设置 `{ tag_ids }` |
| DELETE | `/tags/nodes/{node_id}/tags/{tag_id}` | 移除单个标签 |
| GET | `/tags/nodes/tags?ids=1,2` | 批量查节点标签 |
| POST | `/tags/nodes/batch-add` | 批量加标签 `{ node_ids, tag_ids }` |

### 7.5 扫描

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/scan/trigger` | `{ mode: "incremental" \| "full" }`，409 若扫描中 |
| GET | `/scan/status` | 最近一次 scan_jobs 记录 |

### 7.6 配置

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/settings` | 当前配置 |
| PUT | `/settings` | 部分更新，写入 `data/settings.json` |
| POST | `/settings/rebuild-thumbs` | 清空缩略图目录 |

**可在线修改**：`gallery_root`, `thumb_dir`, `thumb_max_size`, `watch_enabled`, `watch_debounce_seconds`, `log_level`  
修改 `gallery_root` 后响应 `needs_rescan: true`。

### 7.7 任务记录

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/tasks?page=&pageSize=` | 合并 scan_jobs + task_logs，按开始时间倒序 |
| POST | `/tasks/purge` | `{ startTime, endTime }` Unix 秒，按范围删除；`running` 扫描不删 |

---

## 8. 前端结构

### 8.1 路由

| 路径 | 页面 |
|------|------|
| `/` | 首页 |
| `/browse`, `/browse/:nodeId` | 目录浏览（网格 + 面包屑） |
| `/reader/:nodeId` | 阅读器（分页 / 长图滚动，缩略图侧栏可隐藏） |
| `/search` | 搜索 |
| `/admin/settings` | 配置 |
| `/admin/tags` | 标签管理 |
| `/admin/tasks` | 任务记录、扫描触发、按时间清理记录 |

### 8.2 代码组织

```
frontend/src/
├── api/          # axios 封装，对接 /api
├── types/        # TS 类型（与后端 DTO 对齐）
├── views/        # 页面（文件夹内 index.vue）
├── components/   # 可复用组件（AlbumGrid, ScrollViewer 等）
└── utils/        # 格式化、任务记录文案等
```

---

## 9. 配置优先级

```
data/settings.json  >  .env  >  config.yaml  >  代码默认值
```

| 变量 | 默认 | 说明 |
|------|------|------|
| `GALLERY_ROOT` | `./gallery` | 画廊根目录 |
| `THUMB_DIR` | `./data/thumbs` | 缩略图缓存 |
| `DATABASE_URL` | `sqlite:///./data/gallery.db` | 数据库 |
| `THUMB_MAX_SIZE` | `400` | 缩略图长边像素 |
| `WATCH_ENABLED` | `true` | 文件监听 |
| `WATCH_DEBOUNCE_SECONDS` | `3` | watchdog 防抖秒数 |
| `ALBUM_LIST_CACHE_TTL` | `300` | 相册列表内存缓存 TTL |
| `LOG_LEVEL` | `INFO` | 日志级别 |

---

## 10. 后端目录

```
backend/app/
├── api/           # 路由层
├── db/            # models, session, 轻量 migration
├── schemas/       # Pydantic DTO
├── services/      # 业务逻辑
│   ├── scanner.py       # 扫描索引
│   ├── album_reader.py  # 按需列图
│   ├── media.py         # 原图/封面解析
│   ├── thumbnail.py     # 缩略图
│   ├── watcher.py       # watchdog
│   ├── search.py        # FTS 查询
│   ├── scan_runner.py   # 扫描单例锁
│   └── task_log.py      # 任务记录
├── utils/         # 自然排序、路径工具
├── config.py
├── constants.py
└── main.py
```

---

## 11. 安全说明

- **无内置认证**：管理 API 与浏览 API 同等暴露，部署时需反向代理 + 鉴权或仅内网访问
- **路径安全**：图片接口校验 resolved 路径在允许范围内
- **删除语义**：batch-delete 仅删索引，不删源文件

详见 [README 安全说明](../README.md#安全说明)。

---

## 12. 扩展方向（未实现）

- 用户认证与权限
- 更多压缩格式（cbz 以外）
- 定时全量校验任务
- Alembic 正式迁移（当前为 SQLite 轻量 ALTER）
