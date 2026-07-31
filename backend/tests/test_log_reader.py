"""日志读取工具测试。"""

from pathlib import Path

from app.services.log_reader import list_log_files, read_log_content, resolve_log_file


def test_resolve_log_file_rejects_traversal(tmp_path):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    try:
        resolve_log_file(log_dir, "../etc/passwd")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_read_log_tail_and_append(tmp_path):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    path = log_dir / "app.log"
    path.write_text("a\nb\nc\n", encoding="utf-8")

    first = read_log_content(path, tail_lines=2, offset=0)
    assert "b" in first["content"] and "c" in first["content"]
    assert first["append"] is False

    path.write_text("a\nb\nc\nd\n", encoding="utf-8")
    second = read_log_content(path, tail_lines=2, offset=first["offset"])
    assert second["append"] is True
    assert "d" in second["content"]


def test_list_log_files(tmp_path):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    (log_dir / "app.log").write_text("x\n", encoding="utf-8")
    (log_dir / "app.log.2026-07-31").write_text("y\n", encoding="utf-8")
    names = {item["name"] for item in list_log_files(log_dir)}
    assert names == {"app.log", "app.log.2026-07-31"}
