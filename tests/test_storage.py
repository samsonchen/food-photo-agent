from __future__ import annotations

from datetime import datetime

import pytest

from food_agent.storage import (
    StorageError,
    delete_files,
    relative_to_data_dir,
    sanitize_name,
    save_photo,
)

WHEN = datetime(2026, 10, 15, 12, 30, 45)


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("牛肉麵", "牛肉麵"),
        ("beef noodle", "beef_noodle"),
        ("a/b\\c:d*e?f\"g<h>i|j", "a_b_c_d_e_f_g_h_i_j"),
        ("..\\..\\Windows\\evil", "Windows_evil"),
        ("../../etc/passwd", "etc_passwd"),
        ("C:\\x.jpg", "C_x_jpg"),
        ("", "未命名"),
        ("....", "未命名"),
        ("///", "未命名"),
        ("CON", "_CON"),
        ("com1", "_com1"),
        ("牛肉：麵", "牛肉_麵"),  # 全形冒號
        ("x" * 100, "x" * 30),
    ],
)
def test_sanitize_name(raw, expected):
    assert sanitize_name(raw) == expected


def test_save_photo_basic_name(settings):
    p = save_photo(b"abc", ".jpg", WHEN, "牛肉麵", settings.photos_dir)
    assert p.name == "2026-10-15 12-30-45 牛肉麵.jpg"
    assert p.read_bytes() == b"abc"
    assert relative_to_data_dir(p, settings.data_dir) == "photos/2026-10-15 12-30-45 牛肉麵.jpg"


def test_same_second_collision_adds_suffix(settings):
    names = [save_photo(b"x", ".jpg", WHEN, "牛肉麵", settings.photos_dir).name for _ in range(3)]
    assert names == [
        "2026-10-15 12-30-45 牛肉麵.jpg",
        "2026-10-15 12-30-45 牛肉麵-2.jpg",
        "2026-10-15 12-30-45 牛肉麵-3.jpg",
    ]


def test_collision_does_not_overwrite(settings):
    first = save_photo(b"first", ".jpg", WHEN, "x", settings.photos_dir)
    save_photo(b"second", ".jpg", WHEN, "x", settings.photos_dir)
    assert first.read_bytes() == b"first"


@pytest.mark.parametrize("evil", ["..\\..\\evil", "../../evil", "C:\\Windows\\evil", "a/b/c", "..", "x\x00y"])
def test_path_tricks_stay_inside_photos_dir(settings, evil):
    p = save_photo(b"x", ".jpg", WHEN, evil, settings.photos_dir)
    assert p.resolve().parent == settings.photos_dir.resolve()
    # 照片資料夾之外沒有多出任何檔案
    outside = [f for f in settings.data_dir.rglob("*") if f.is_file() and f.parent != settings.photos_dir]
    assert outside == []


def test_extension_whitelist(settings):
    with pytest.raises(StorageError):
        save_photo(b"x", ".exe", WHEN, "x", settings.photos_dir)
    p = save_photo(b"x", ".PNG", WHEN, "x", settings.photos_dir)
    assert p.suffix == ".png"


def test_delete_files(settings):
    p = save_photo(b"x", ".jpg", WHEN, "x", settings.photos_dir)
    delete_files([p, settings.photos_dir / "not-there.jpg"])
    assert not p.exists()
