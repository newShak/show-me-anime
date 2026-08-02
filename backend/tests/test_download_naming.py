"""下载文件夹命名测试。"""

from app.services.download.naming import album_folder_name


def test_keeps_cjk_and_brackets():
    title = "[蒼山哲]老舗温泉旅館の若女将は"
    assert album_folder_name(title, "12345") == title


def test_strips_html_tags():
    assert album_folder_name("<em>Hello</em> World", "1") == "Hello-World"


def test_empty_title_uses_album_prefix():
    assert album_folder_name("", "374814") == "album-374814"
    assert album_folder_name("<br>", "374814") == "album-374814"


def test_pure_numeric_slug_gets_suffix():
    assert album_folder_name("5", "999") == "5-999"
    assert album_folder_name("374814", "374814") == "album-374814"
    assert album_folder_name("[5]", "999") == "[5]"


def test_truncates_long_title():
    long_title = "あ" * 80
    assert len(album_folder_name(long_title, "x")) == 60
