"""目录扫描：仅索引集合（nodes），不逐张图片入库。"""

import logging
import time
import zipfile
from pathlib import Path

from sqlalchemy.orm import Session

from app import constants
from app.config import Settings, get_settings
from app.db.models import Node, ScanJob
from app.services.archive_reader import list_archive_images
from app.services.node_admin import sync_node_search_index
from app.services.search import remove_node_search
from app.utils.natural_sort import natural_sort_key, sorted_image_names
from app.utils.paths import archive_display_name, is_archive_file, is_image_file, rel_path

logger = logging.getLogger(__name__)


class Scanner:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._archive_cache: dict[str, tuple[float, list[str]]] = {}
        self._skipped_deep = 0
        self._incremental = True

    def scan_all(
        self,
        db: Session,
        source: str = "manual",
        changed_paths: list[str] | None = None,
        mode: str = constants.SCAN_MODE_INCREMENTAL,
    ) -> ScanJob:
        job = ScanJob(
            status=constants.SCAN_RUNNING,
            source=source,
            mode=mode,
            started_at=time.time(),
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        try:
            existing = {node.path: node for node in db.query(Node).all()}
            self._skipped_deep = 0
            self._archive_cache.clear()
            self._incremental = mode == constants.SCAN_MODE_INCREMENTAL

            logger.info(
                "scan job_id=%s mode=%s collecting nodes from %s",
                job.id,
                mode,
                self.settings.gallery_root,
            )
            metas = self._collect_disk_nodes(existing, changed_paths)
            logger.info(
                "scan job_id=%s found %d nodes on disk skipped_deep=%d",
                job.id,
                len(metas),
                self._skipped_deep,
            )
            metas.sort(key=lambda item: item["path"].count("/"))
            seen: set[str] = set()

            for meta in metas:
                path_str = meta["path"]
                seen.add(path_str)
                parent_id = self._resolve_parent_id(db, path_str)
                node = existing.get(path_str)

                if node is None:
                    node = Node(
                        name=meta["name"],
                        path=path_str,
                        parent_id=parent_id,
                        node_type=meta["node_type"],
                        source_type=meta["source_type"],
                        image_count=meta["image_count"],
                        subdir_count=meta["subdir_count"],
                        cover_rel_path=meta["cover_rel_path"],
                        dir_mtime=meta["dir_mtime"],
                    )
                    db.add(node)
                    db.flush()
                    job.added += 1
                    sync_node_search_index(db, node)
                    continue

                changed = (
                    node.name != meta["name"]
                    or node.node_type != meta["node_type"]
                    or node.source_type != meta["source_type"]
                    or node.parent_id != parent_id
                    or node.image_count != meta["image_count"]
                    or node.subdir_count != meta["subdir_count"]
                    or node.cover_rel_path != meta["cover_rel_path"]
                    or node.dir_mtime != meta["dir_mtime"]
                )
                if changed:
                    node.name = meta["name"]
                    node.node_type = meta["node_type"]
                    node.source_type = meta["source_type"]
                    node.parent_id = parent_id
                    node.image_count = meta["image_count"]
                    node.subdir_count = meta["subdir_count"]
                    node.cover_rel_path = meta["cover_rel_path"]
                    node.dir_mtime = meta["dir_mtime"]
                    node.updated_at = time.time()
                    job.updated += 1
                    sync_node_search_index(db, node)

            for path_str, node in existing.items():
                if path_str not in seen:
                    logger.debug("scan job_id=%s removing node path=%s", job.id, path_str)
                    remove_node_search(db, node.id)
                    db.delete(node)
                    job.removed += 1

            self._apply_container_covers(db, job)

            job.status = constants.SCAN_DONE
            job.finished_at = time.time()
            skipped = f", skipped_deep={self._skipped_deep}" if self._incremental else ""
            job.message = f"scan completed (mode={mode}{skipped})"
            db.commit()
            db.refresh(job)
            logger.info(
                "scan job_id=%s indexed added=%s updated=%s removed=%s skipped_deep=%s",
                job.id,
                job.added,
                job.updated,
                job.removed,
                self._skipped_deep,
            )
            return job
        except Exception as exc:
            logger.exception("scan job_id=%s failed: %s", job.id, exc)
            job.status = constants.SCAN_FAILED
            job.finished_at = time.time()
            job.message = str(exc)
            db.commit()
            db.refresh(job)
            raise

    @staticmethod
    def _meta_from_node(node: Node) -> dict:
        return {
            "path": node.path,
            "name": node.name,
            "node_type": node.node_type,
            "source_type": node.source_type,
            "image_count": node.image_count,
            "subdir_count": node.subdir_count,
            "cover_rel_path": node.cover_rel_path,
            "dir_mtime": node.dir_mtime,
        }

    def _hot_paths(self, root: Path, changed_paths: list[str] | None) -> set[str]:
        if not changed_paths:
            return set()
        root = root.resolve()
        hot: set[str] = set()
        for raw in changed_paths:
            p = Path(raw)
            p = p.resolve() if p.is_absolute() else (root / p).resolve()
            if not str(p).startswith(str(root)):
                continue
            rel = p.relative_to(root).as_posix()
            if rel == ".":
                rel = ""
            parts = rel.split("/") if rel else []
            for i in range(len(parts) + 1):
                hot.add("/".join(parts[:i]))
        return hot

    def _resolve_parent_id(self, db: Session, path_str: str) -> int | None:
        if not path_str:
            return None
        parent_path = str(Path(path_str).parent.as_posix())
        if parent_path == ".":
            parent_path = ""
        if not parent_path:
            return None
        parent = db.query(Node).filter(Node.path == parent_path).first()
        return parent.id if parent else None

    def _apply_container_covers(self, db: Session, job: ScanJob) -> None:
        """纯容器目录无本地图片时，继承第一个有封面的子节点。"""
        nodes = db.query(Node).all()
        children: dict[int | None, list[Node]] = {}
        for node in nodes:
            children.setdefault(node.parent_id, []).append(node)
        for items in children.values():
            items.sort(key=lambda n: natural_sort_key(n.name))

        containers = [
            n for n in nodes if n.node_type == constants.CONTAINER and n.image_count == 0
        ]
        containers.sort(key=lambda n: n.path.count("/"), reverse=True)

        for node in containers:
            inherited = None
            for child in children.get(node.id, []):
                inherited = self._pick_child_cover(child)
                if inherited:
                    break
            if node.cover_rel_path == inherited:
                continue
            node.cover_rel_path = inherited
            node.updated_at = time.time()
            job.updated += 1

    @staticmethod
    def _pick_child_cover(child: Node) -> str | None:
        if child.source_type == constants.SOURCE_ZIP:
            if not child.cover_rel_path:
                return None
            return f"{Path(child.path).name}::{child.cover_rel_path}"
        if not child.cover_rel_path:
            return None
        return f"{child.name}/{child.cover_rel_path}"

    def _collect_disk_nodes(
        self,
        existing: dict[str, Node],
        changed_paths: list[str] | None = None,
    ) -> list[dict]:
        root = self.settings.gallery_root
        hot_paths = self._hot_paths(root, changed_paths)
        result: list[dict] = []

        for dirpath, _dirnames, filenames in root.walk(top_down=True):
            current = Path(dirpath)
            meta = self._analyze_dir(root, current, existing, hot_paths)
            if meta and meta["path"]:
                result.append(meta)
            for fname in filenames:
                if is_archive_file(fname):
                    archive_meta = self._analyze_archive(root, current / fname, existing, hot_paths)
                    if archive_meta:
                        result.append(archive_meta)

        return result

    def _use_cached_meta(
        self,
        rel: str,
        mtime: float,
        source_type: str,
        existing: dict[str, Node],
        hot_paths: set[str],
    ) -> dict | None:
        if not self._incremental or rel in hot_paths:
            return None
        node = existing.get(rel)
        if node is None or node.source_type != source_type or node.dir_mtime != mtime:
            return None
        self._skipped_deep += 1
        return self._meta_from_node(node)

    def _analyze_archive(
        self,
        root: Path,
        archive_path: Path,
        existing: dict[str, Node],
        hot_paths: set[str],
    ) -> dict | None:
        rel = rel_path(root, archive_path)
        try:
            mtime = archive_path.stat().st_mtime
        except OSError as exc:
            logger.warning("skip archive path=%s error=%s", rel, exc)
            return None

        cached_meta = self._use_cached_meta(rel, mtime, constants.SOURCE_ZIP, existing, hot_paths)
        if cached_meta:
            return cached_meta

        cached = self._archive_cache.get(rel) if self._incremental else None
        if cached and cached[0] == mtime:
            images = cached[1]
        else:
            try:
                images = list_archive_images(archive_path)
            except (OSError, zipfile.BadZipFile) as exc:
                logger.warning("skip archive path=%s error=%s", rel, exc)
                return None
            if self._incremental:
                self._archive_cache[rel] = (mtime, images)

        if not images:
            return None
        return {
            "path": rel,
            "name": archive_display_name(archive_path.name),
            "node_type": constants.ALBUM,
            "source_type": constants.SOURCE_ZIP,
            "image_count": len(images),
            "subdir_count": 0,
            "cover_rel_path": images[0],
            "dir_mtime": mtime,
        }

    def _analyze_dir(
        self,
        root: Path,
        current: Path,
        existing: dict[str, Node],
        hot_paths: set[str],
    ) -> dict | None:
        rel = "" if current == root else rel_path(root, current)
        if rel:
            try:
                mtime = current.stat().st_mtime
            except OSError:
                return None
            cached_meta = self._use_cached_meta(rel, mtime, constants.SOURCE_FOLDER, existing, hot_paths)
            if cached_meta:
                return cached_meta

        entries = list(current.iterdir())
        subdirs = [entry.name for entry in entries if entry.is_dir()]
        archives = [entry.name for entry in entries if entry.is_file() and is_archive_file(entry.name)]
        images = sorted_image_names(
            [entry.name for entry in entries if entry.is_file() and is_image_file(entry.name)]
        )

        if not subdirs and not images and not archives:
            return None
        if not rel and not images and (subdirs or archives):
            return None

        if images and subdirs:
            node_type = constants.BOTH
        elif images:
            node_type = constants.ALBUM
        else:
            node_type = constants.CONTAINER

        cover = images[0] if images else None
        if node_type == constants.CONTAINER and not cover:
            prev = existing.get(rel)
            if prev and prev.cover_rel_path:
                cover = prev.cover_rel_path

        return {
            "path": rel,
            "name": root.name if not rel else current.name,
            "node_type": node_type,
            "source_type": constants.SOURCE_FOLDER,
            "image_count": len(images),
            "subdir_count": len(subdirs),
            "cover_rel_path": cover,
            "dir_mtime": current.stat().st_mtime,
        }
