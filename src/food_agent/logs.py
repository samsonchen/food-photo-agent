"""log 設定（docs/architecture.md 第 4 節「處理過程的 log」）。

同一則訊息的所有紀錄開頭都有 [#編號]（訊息 ID 的最後 6 位），用 contextvars 帶著走，
所以不用在每個函式之間傳來傳去，在 asyncio.to_thread 裡寫的 log 也帶得到。
"""

from __future__ import annotations

import logging
import logging.handlers
import sys
from contextvars import ContextVar
from pathlib import Path

job_tag: ContextVar[str] = ContextVar("job_tag", default="")

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(tag)s%(message)s"
LOG_MAX_BYTES = 5 * 1024 * 1024
LOG_BACKUP_COUNT = 3


def tag_for(message_id: int) -> str:
    return f"#{str(message_id)[-6:]}"


class TagFilter(logging.Filter):
    """在每筆紀錄上補一個 tag 欄位：有編號時是「[#123456] 」，沒有時是空字串。"""

    def filter(self, record: logging.LogRecord) -> bool:
        tag = job_tag.get()
        record.tag = f"[{tag}] " if tag else ""
        return True


def setup_logging(log_path: Path) -> list[logging.Handler]:
    """同時輸出到終端機和 log 檔（超過 5 MB 自動換檔，保留 3 份舊檔）。回傳建立的 handler，方便測試時移除。"""
    formatter = logging.Formatter(LOG_FORMAT)
    handlers: list[logging.Handler] = [
        logging.StreamHandler(sys.stdout),
        logging.handlers.RotatingFileHandler(
            log_path, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT, encoding="utf-8"
        ),
    ]
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    for handler in handlers:
        handler.setFormatter(formatter)
        handler.addFilter(TagFilter())  # 掛在 handler 上，所以連 discord 等套件的紀錄也有 tag 欄位
        root.addHandler(handler)
    logging.getLogger("discord").setLevel(logging.WARNING)
    logging.getLogger("discord.client").setLevel(logging.ERROR)  # 擋掉「沒裝語音套件」的警告，這個專案不用語音
    return handlers
