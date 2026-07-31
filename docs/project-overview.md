# Show Me Anime — 项目说明

本地/局域网图片画廊系统，用于浏览和管理按文件夹或压缩包组织的漫画、组图等图片集合。支持标签、收藏、外站下载入库与 Docker 一键部署。

---

## 1. 项目简介

| 项 | 说明 |
|----|------|
| 定位 | 个人图库管理 + Web 浏览 + 外站资源下载 |
| 数据源 | 磁盘目录树 + ZIP 压缩包（只读，不入库二进制） |
| 索引粒度 | **集合级**（文件夹 / 压缩包），不逐张图片入库 |
| 部署 | 单容器 Docker，FastAPI 托管 Vue 静态资源 |
| 预构建镜像 | [yaliyhub/show-me-anime:latest](https://hub.docker.com/r/yaliyhub/show-me-anime) |

### 1.1 功能一览

**画廊与阅读**

- 树形目录 + 网格浏览，支持按名称/修改时间排序
- 阅读器：翻页 / 长图滚动，缩略图导航，阅读进度记忆
- 批量选择：打标签、移动、删除（同步删磁盘）
- 新建子文件夹、编辑节点类型与封面（含子节点封面继承）
- 大目录性能优化：缩略图懒加载、分批渲染、并发限流

**发现与整理**

- FTS5 全文搜索 + 标签过滤（OR / AND）
- 最近添加、最近浏览、收藏
- 标签管理与批量打标

**索引与维护**

- 增量 / 全量扫描，watchdog 防抖自动增量
- 任务记录（扫描、重建缩略图）与按时间清理
- 应用日志：按日轮转、Web 查看、可配置保留天数

**外站下载（WNA CG）**

- 搜索、分类浏览、详情预览、单本/批量下载
- 下载任务队列、断点续传、取消、重试、强制覆盖
- 目标路径已存在时自动跳过；下载完成后触发扫描入库
- 下载记录（状态筛选、分页、文件大小统计、删除）
- 可选 HTTP 代理、限速、并发控制；`curl_cffi` 绕过 CDN 指纹限制

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
最近浏览、收藏           →  recent_views / favorites
全文搜索                 →  search_index (FTS5)
外站下载任务             →  download_records（元数据，文件落盘到 gallery）
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
├── 漫画/              → container
│   └── 作品A/         → album（1.jpg … 100.jpg）
├── imports/wnacg/     → container（外站下载默认目录）
│   └── 某本子/        → album
├── 杂项/              → both
└── 单行本.zip         → album（source_type=zip）
```

### 2.3 扫描与删除

- **扫描**：只读画廊目录，写入 SQLite 节点索引
- **删除节点**（`batch-delete`）：**同时删除磁盘上的目录/压缩包与 DB 记录**（含标签、进度、收藏、搜索索引），**不可恢复**
- **移动节点**（`move`）：同步移动磁盘目录/压缩包并更新子树 path
- 缩略图为衍生数据，可「重建缩略图」整目录清除后按需再生

### 2.4 增量扫描

全量 walk 仍遍历目录树，但对**未变更**的节点用 `dir_mtime` 短路：

- 增量模式：`mtime` 一致且不在 watchdog 热路径 → 复用 DB 元数据
- 热路径：watchdog 上报的变更路径及其祖先目录强制重分析
- ZIP：扫描阶段用内存 zip 列表缓存，避免重复解压列目录

### 2.5 容器封面继承

纯 `container` 且 `image_count=0` 的节点，扫描后从**第一个有封面的子节点**继承封面路径。用户也可手动指定封面（`cover_manual`），手动封面不被扫描覆盖。

### 2.6 Watchdog 防抖

- `watchdog` 递归监听 `GALLERY_ROOT`
- 忽略只读 `opened` / `closed_no_write` 事件
- 扫描进行中 + cooldown 内忽略事件
- 防抖合并后触发**增量扫描**，并传入 `changed_paths` 热路径

### 2.7 外站下载适配器

下载模块采用 **Adapter 注册表**（当前实现 `wnacg`）：

```
搜索/浏览/详情 → Adapter 解析 HTML/API
       ↓
generate-link（串行）→ CDN 签名 URL
       ↓
下载 ZIP → 解压到 cache → 移动到 gallery 目标路径
       ↓
run_scan(source=download) 入库
```

- 任务状态持久化到 `download_records`，服务重启后可恢复/标记 stale
- 内存队列控制并发；`generate-link` 与 CDN 下载分离限流
- 目标路径占用检测：已存在且非强制覆盖 → 立即完成并计为 skipped

---

## 3. 系统架构

```
┌──────────────────────────────────────────────────────────────────┐
│                     Browser (Vue 3 SPA)                           │
│  首页 · 画廊 · 阅读器 · 搜索 · 外站下载 · 管理后台                 │
└────────────────────────────┬─────────────────────────────────────┘
                             │ REST /api/*
┌────────────────────────────▼─────────────────────────────────────┐
│                        FastAPI (backend)                          │
│  nodes · search · tags · library · scan · download · settings     │
│  tasks · logs · health                                              │
├─────────────┬──────────────┬──────────────┬────────────┬─────────┤
│ Scanner     │ AlbumReader  │ Thumbnail    │ Watcher    │ Download│
│ Search FTS  │ Node move/   │ Archive      │ Jobs queue │ Adapters│
│             │ delete       │ reader       │            │         │
└──────┬──────┴──────┬───────┴──────┬───────┴─────┬──────┴────┬────┘
       │             │              │             │           │
       ▼             ▼              ▼             ▼           ▼
  gallery.db    GALLERY_ROOT    THUMB_DIR    inotify    download_cache/
  (SQLite+FTS5)  (源文件)       (webp)                    + logs/
```

**技术栈**

| 层级 | 选型 |
|------|------|
| 后端 | Python 3.12 · FastAPI · SQLAlchemy 2.x |
| 数据库 | SQLite + FTS5 虚拟表 |
| 文件监听 | watchdog 6.x |
| 图片 | Pillow（缩略图 WebP） |
| 外站下载 | httpx + curl_cffi（TLS 指纹） |
| 前端 | Vue 3 · Vite · Element Plus · TypeScript |
| 配置 | pydantic-settings · `.env` / `config.yaml` / `data/settings.json` |

---

## 4. 数据模型

### 4.1 ER 关系

```
nodes (自关联 parent_id)
  ├── node_tags ── tags
  ├── read_progress
  ├── recent_views
  ├── favorites
  └── search_index (FTS5, node_id)

scan_jobs          ← 扫描任务
task_logs          ← 管理任务（如重建缩略图）
download_records   ← 外站下载任务记录
```

### 4.2 核心表

#### `nodes`

| 字段 | 说明 |
|------|------|
| path | 相对 `GALLERY_ROOT` 的唯一路径 |
| node_type | `container` / `album` / `both` |
| source_type | `folder` / `zip` |
| image_count / subdir_count / archive_count | 统计字段 |
| cover_rel_path / cover_manual | 封面与是否手动指定 |
| dir_mtime | 增量扫描短路依据 |
| created_at | 最近添加排序依据 |

#### `read_progress` / `recent_views` / `favorites`

- 阅读进度：按 `node_id` 存当前页码
- 最近浏览：按 `viewed_at` 排序，有上限裁剪
- 收藏：按 `created_at` 排序，支持分页列表

#### `download_records`

| 字段 | 说明 |
|------|------|
| id | UUID 任务 ID |
| source / album_id / title | 外站来源与资源标识 |
| target_rel_path | 画廊内相对路径 |
| status | `pending` / `running` / `done` / `failed` |
| progress / message | 进度与状态文案 |
| saved_files / skipped_files | 写入/跳过文件数 |
| target_existed | 创建任务时目标是否已占用 |

列表接口按磁盘路径**实时计算** `size_bytes`（目标目录或缓存目录体积累计）。

#### `search_index` (FTS5)

索引节点名、路径、标签名；支持关键词 + 标签组合查询。

---

## 5. 扫描与图片读取

### 5.1 扫描流程

触发源：管理页 API / watchdog / 下载完成 / 新建目录

```
run_scan(source, mode, changed_paths?)
  → Scanner.scan_all()
  → 对比 DB：added / updated / removed
  → 同步 FTS、容器封面继承
  → 更新 scan_jobs
```

全局锁：同一时刻仅一个扫描任务，冲突返回 409。

### 5.2 图片列表与缩略图

- **列表**：文件夹 `iterdir` 或 ZIP entry 列表，**自然排序**
- **缓存**：`dir_mtime` + TTL（`album_list_cache_ttl`）
- **原图 / 缩略图**：Pillow 生成 WebP 缓存；ZIP 内图片读入内存返回
- **路径安全**：resolve 后必须在画廊根或节点目录内

---

## 6. REST API 概览

Base URL: `/api`  
生产环境由 FastAPI 同域托管静态资源；开发时 Vite 代理 `/api`。

### 6.1 节点 `/nodes`

| 能力 | 说明 |
|------|------|
| 列表 / 详情 / 祖先链 | `GET /nodes`、`/nodes/{id}`、`/nodes/{id}/ancestors` |
| 最近添加 | `GET /nodes/recent?since=&until=&offset=&limit=` |
| 批量查询 | `GET /nodes/batch?ids=` |
| 图片与封面 | `/images`、`/images/{i}/file|thumb`、`/cover/thumb`、`/cover/candidates` |
| 阅读进度 | `GET|PUT /nodes/{id}/progress`，批量 `GET /nodes/progress` |
| 编辑 | `PATCH` 节点类型、封面 |
| 移动 / 新建 / 删除 | `POST /move`、`/mkdir`、`/batch-delete` |

排序：`sort_by=name|mtime`，`sort_order=asc|desc`。

### 6.2 搜索 `/search`

- 关键词 FTS + 标签 ID 过滤
- 多标签支持 `tag_mode=and`

### 6.3 标签 `/tags`

- CRUD、分页、节点关联、批量加标

### 6.4 书库 `/library`

| 路径 | 说明 |
|------|------|
| `GET /recent` | 最近浏览节点列表 |
| `POST /recent/{node_id}` | 记录浏览 |
| `GET /favorites` | 收藏分页 |
| `POST /favorites/{node_id}` | 切换收藏 |

### 6.5 扫描 `/scan`

- `POST /trigger` 增量或全量
- `GET /status` 最近一次任务

### 6.6 外站下载 `/download`

| 路径 | 说明 |
|------|------|
| `GET /sources` | 可用来源（如 wnacg） |
| `GET /search`、`/browse`、`/detail` | 搜索与浏览 |
| `GET /cover`、`/preview`、`/previews` | 封面与预览图 |
| `POST /jobs`、`/jobs/batch` | 创建任务 |
| `GET /jobs/{id}` | 任务状态 |
| `POST /jobs/{id}/resume|retry|cancel|overwrite` | 续传/重试/取消/覆盖 |
| `GET /records` | 下载记录（含 `size_bytes`、页合计） |
| `DELETE /records/{id}` | 删除记录 |
| `POST /cache/clear`、`/proxy/test` | 缓存与代理测试 |

### 6.7 配置 `/settings`

- 读写运行参数（画廊路径、监听、日志、下载、最近列表上限等）
- `POST /rebuild-thumbs` 清空缩略图缓存

### 6.8 任务与日志

- `GET /tasks`、`POST /tasks/purge` — 扫描与管理任务记录
- `GET /logs/files`、`/logs/content` — 应用日志查看

### 6.9 健康检查

- `GET /health` → `{ "status": "ok" }`

---

## 7. 前端结构

### 7.1 路由

| 路径 | 页面 |
|------|------|
| `/` | 首页（最近添加 / 最近浏览 / 收藏预览） |
| `/recent-added` | 最近添加（按日分组） |
| `/recent-viewed`、`/favorites` | 最近浏览 / 收藏列表 |
| `/browse`、`/browse/:nodeId` | 画廊（侧栏树 + 网格 + 批量操作） |
| `/reader/:nodeId` | 阅读器 |
| `/search` | 搜索（无限滚动） |
| `/download` | 外站下载（搜索、浏览、详情、批量下载、记录抽屉） |
| `/admin/settings` | 系统配置 |
| `/admin/download` | 下载专用配置 |
| `/admin/tags` | 标签管理 |
| `/admin/tasks` | 任务记录与扫描 |
| `/admin/logs` | 应用日志 |

### 7.2 代码组织

```
frontend/src/
├── api/           # HTTP 客户端（nodes / library / download …）
├── types/         # 与后端 DTO 对齐的 TS 类型
├── views/         # 页面（目录内 index.vue）
├── components/    # AlbumGrid、LazyCover、ScrollViewer、DownloadRecordTable …
├── composables/   # 排序、收藏、下载记录、浏览滚动等
└── utils/         # 格式化、缩略图加载队列等
```

**画廊性能相关组件**

- `LazyCover`：Intersection Observer + 全局最多 4 路缩略图并发
- 进入文件夹时清空列表、滚动回顶、分批挂载节点（每批 36）
- 面包屑一次请求祖先链，标签/进度 idle 后加载

---

## 8. 配置

优先级：`data/settings.json` > `.env` > `config.yaml` > 默认值

| 变量 | 默认 | 说明 |
|------|------|------|
| `GALLERY_ROOT` | `./gallery` | 画廊根目录 |
| `THUMB_DIR` | `./data/thumbs` | 缩略图缓存 |
| `DATABASE_URL` | `sqlite:///./data/gallery.db` | 数据库 |
| `THUMB_MAX_SIZE` | `400` | 缩略图长边像素 |
| `WATCH_ENABLED` | `true` | 文件监听 |
| `WATCH_DEBOUNCE_SECONDS` | `3` | watchdog 防抖 |
| `ALBUM_LIST_CACHE_TTL` | `300` | 相册列表内存缓存 TTL |
| `RECENT_VIEW_LIMIT` / `RECENT_ADDED_LIMIT` | `20` | 首页与列表上限 |
| `LOG_DIR` / `LOG_FILE_*` | 见 config | 文件日志目录、大小、保留天数 |
| `DOWNLOAD_*` | 见 admin/download | 代理、并发、限速、缓存目录、API 域名 |
| `DOWNLOAD_USE_MOCK` | `true` | 开发/mock 模式（生产应关闭） |

Docker 典型卷映射：

| 宿主机 | 容器 | 说明 |
|--------|------|------|
| `./gallery` | `/data/gallery` | 图片源 |
| `./data` | `/app/data` | DB、缩略图、settings.json |
| （可选）`./logs` | `/data/logs` | 应用日志 |

---

## 9. 后端目录

```
backend/app/
├── api/              # 路由：nodes, search, tags, library, scan, download, settings, tasks, logs
├── db/               # models, session, 轻量 migration
├── schemas/          # Pydantic DTO
├── services/
│   ├── scanner.py           # 索引扫描
│   ├── album_reader.py      # 按需列图
│   ├── archive_reader.py    # ZIP 读取
│   ├── thumbnail.py           # WebP 缩略图
│   ├── watcher.py             # watchdog
│   ├── search.py              # FTS
│   ├── scan_runner.py         # 扫描单例锁
│   ├── node_move.py / node_delete.py / node_mkdir.py
│   ├── download/              # 外站下载（adapters, jobs, transfer, cache, records）
│   ├── logging_config.py / log_reader.py
│   └── task_log.py
├── config.py
└── main.py
```

---

## 10. 部署与开发

**Docker（推荐）**

```bash
docker pull yaliyhub/show-me-anime:latest
docker compose -f docker-compose.hub.yml up -d
```

首次使用在管理页触发扫描，或将图片放入 `gallery/` 后等待 watchdog 增量索引。

**本地开发**

```bash
# 后端
cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 前端
cd frontend && npm install && npm run dev
```

测试：`cd backend && pytest -q`

详见 [README.md](../README.md)。

---

## 11. 安全说明

- **无内置认证**：管理 API 与浏览 API 同等暴露，部署时需反向代理 + 鉴权或仅内网访问
- **路径安全**：图片与移动/删除接口校验 resolved 路径在允许范围内
- **删除语义**：`batch-delete` 会**永久删除**磁盘文件与数据库记录
- **外站下载**：依赖第三方站点与 CDN，需自行承担合规与网络风险；建议配置代理并限制外网暴露

---

## 12. 后续可扩展方向

- 用户认证与多用户隔离
- 更多压缩格式与外站 Adapter
- 画廊虚拟滚动 / 服务端分页（超大规模单目录）
- Alembic 正式迁移（当前为 SQLite 轻量 ALTER）
- 下载来源插件化配置 UI
