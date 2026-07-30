"""目录扫描：仅索引集合（nodes），不逐张图片入库。"""

import time
import zipfile
from pathlib import Path

from sqlalchemy.orm import Session

from app import constants
from app.config import Settings, get_settings
from app.db.models import Node, ScanJob
from app.services.archive_reader import list_archive_images
from app.services.search import remove_node_search
from app.services.node_admin import sync_node_search_index
from app.utils.natural_sort import sorted_image_names
from app.utils.paths import archive_display_name, is_archive_file, is_image_file, rel_path


class Scanner:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    def scan_all(self, db: Session) -> ScanJob:
        job = ScanJob(status=constants.SCAN_RUNNING, started_at=time.time())
        db.add(job)
        db.commit()
        db.refresh(job)

        try:
            metas = self._collect_disk_nodes()
            metas.sort(key=lambda item: item["path"].count("/"))
            existing = {node.path: node for node in db.query(Node).all()}
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
                else:
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
                    remove_node_search(db, node.id)
                    db.delete(node)
                    job.removed += 1

            job.status = constants.SCAN_DONE
            job.finished_at = time.time()
            job.message = "scan completed"
            db.commit()
            db.refresh(job)
            return job
        except Exception as exc:
            job.status = constants.SCAN_FAILED
            job.finished_at = time.time()
            job.message = str(exc)
            db.commit()
            db.refresh(job)
            raise

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

    def _collect_disk_nodes(self) -> list[dict]:
        root = self.settings.gallery_root
        result: list[dict] = []

        for dirpath, _dirnames, filenames in root.walk(top_down=True):
            current = Path(dirpath)
            meta = self._analyze_dir(root, current)
            if meta and meta["path"]:
                result.append(meta)
            for fname in filenames:
                if is_archive_file(fname):
                    archive_meta = self._analyze_archive(root, current / fname)
                    if archive_meta:
                        result.append(archive_meta)

        return result

    def _analyze_archive(self, root: Path, archive_path: Path) -> dict | None:
        rel = rel_path(root, archive_path)
        try:
            images = list_archive_images(archive_path)
        except (OSError, zipfile.BadZipFile):
            return None
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
            "dir_mtime": archive_path.stat().st_mtime,
        }

    def _analyze_dir(self, root: Path, current: Path) -> dict | None:
        rel = "" if current == root else rel_path(root, current)
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

        return {
            "path": rel,
            "name": root.name if not rel else current.name,
            "node_type": node_type,
            "source_type": constants.SOURCE_FOLDER,
            "image_count": len(images),
            "subdir_count": len(subdirs),
            "cover_rel_path": images[0] if images else None,
            "dir_mtime": current.stat().st_mtime,
        }
