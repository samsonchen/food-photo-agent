"""存照片、命名（docs/architecture.md 第 9 節）。

這個檔案裡有一段防護：
  防護 3：食物名稱拿去當檔名前先清洗
前面先放一行「沒有防護時的預設寫法」，防護段落再覆蓋它。
"""

from __future__ import annotations

import itertools
import re
import unicodedata
from datetime import datetime
from pathlib import Path

from food_agent import config

ALLOWED_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".gif")
_RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
_MAX_COLLISIONS = 1000


class StorageError(Exception):
    pass


def sanitize_name(raw: str, max_chars: int = config.NAME_MAX_CHARS) -> str:
    """只留文字（含中日韓）、數字、-、_；其他字（/ \\ : * ? " < > | 空白 . 控制字元）都換成 _。"""
    text = unicodedata.normalize("NFKC", raw)
    text = re.sub(r"[^\w\-]", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    text = text[:max_chars].strip("_")
    if not text:
        return "未命名"
    if text.upper() in _RESERVED:
        text = f"_{text}"
    return text


def save_photo(data: bytes, ext: str, when: datetime, raw_name: str, photos_dir: Path) -> Path:
    """把照片存成「YYYY-MM-DD hh-mm-ss 名稱.副檔名」。撞名時在名稱後面加 -2、-3。回傳完整路徑。"""
    ext = ext.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise StorageError(f"不支援的副檔名：{ext}")
    stamp = when.strftime("%Y-%m-%d %H-%M-%S")

    # ---- 沒有防護 3 時的預設：直接用原名稱 ----
    safe_name = raw_name
    # ==== 防護 3：檔名清洗　開始 ====
    safe_name = sanitize_name(raw_name)  # 去掉 / \ .. 冒號等會讓路徑亂跑的字
    probe = (photos_dir / f"{stamp} {safe_name}{ext}").resolve()
    if not probe.is_relative_to(photos_dir.resolve()):  # 最後確認：完整路徑一定在照片資料夾裡面
        raise StorageError("檔名會讓照片存到照片資料夾之外，已拒絕")
    # ==== 防護 3 結束 ====

    for n in itertools.count(1):
        if n > _MAX_COLLISIONS:
            raise StorageError("同名檔案太多，無法命名")
        suffix = "" if n == 1 else f"-{n}"
        path = photos_dir / f"{stamp} {safe_name}{suffix}{ext}"
        try:
            with open(path, "xb") as f:  # "x"：檔案已存在就失敗，不會蓋掉別人的照片
                f.write(data)
            return path
        except FileExistsError:
            continue
    raise StorageError("無法命名")  # 不會走到這裡，讓型別檢查安心


def relative_to_data_dir(path: Path, data_dir: Path) -> str:
    """Excel 裡的「照片存放位置」：相對於 DATA_DIR 的路徑，用 /。"""
    return path.resolve().relative_to(data_dir.resolve()).as_posix()


def delete_files(paths: list[Path]) -> None:
    """失敗時把這一則已存的照片刪掉。"""
    for path in paths:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
