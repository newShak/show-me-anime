"""自然排序测试。"""

from app.utils.natural_sort import sorted_image_names


def test_numeric_order():
    assert sorted_image_names(["10.jpg", "2.jpg", "1.jpg", "100.jpg"]) == [
        "1.jpg",
        "2.jpg",
        "10.jpg",
        "100.jpg",
    ]


def test_zero_padded_order():
    assert sorted_image_names(["0010.jpg", "0002.jpg", "0001.jpg"]) == [
        "0001.jpg",
        "0002.jpg",
        "0010.jpg",
    ]


def test_page_prefix_order():
    assert sorted_image_names(["page10.jpg", "page2.jpg", "page1.jpg"]) == [
        "page1.jpg",
        "page2.jpg",
        "page10.jpg",
    ]
