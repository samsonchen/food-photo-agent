"""讀取 .env 設定，以及各種預設上限（見 docs/architecture.md 第 11 節與附錄 A）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from dotenv import dotenv_values

REQUIRED_KEYS = ("DISCORD_TOKEN", "CHANNEL_ID", "CLAUDE_MODEL", "DATA_DIR")

# ---- 預設上限（附錄 A），不是需求，實測後可以調整 ----
CLAUDE_TIMEOUT_S = 120  # 單次 claude -p 逾時秒數
MAX_ATTEMPTS = 2  # 每則訊息最多呼叫 claude -p 的次數（第一次加一次重試）
CLAUDE_OUTPUT_MAX_CHARS = 1_000_000

MAX_PHOTOS_PER_MESSAGE = 5
QUEUE_MAX_WAITING = 10  # 佇列最多同時等待的訊息數
PER_USER_MAX = 2  # 每個人同時最多在佇列裡（含正在處理的）的訊息數
MAX_FILE_BYTES = 10 * 1024 * 1024

CAPTION_MAX_CHARS = 200  # 上傳者備註
NAME_MAX_CHARS = 30  # 食物名稱
LABEL_MAX_CHARS = 30  # 非食物是什麼
INGREDIENT_MAX_ITEMS = 20
INGREDIENT_MAX_CHARS = 30
WEIGHT_RANGE_G = (1, 10_000)
KCAL_RANGE = (0, 10_000)

EXCEL_RETRY_TIMES = 5
EXCEL_RETRY_WAIT_S = 3

DISCORD_MESSAGE_MAX_CHARS = 2000

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class ConfigError(Exception):
    """設定缺漏或格式不對。訊息會直接顯示給使用者看。"""


@dataclass(frozen=True)
class Settings:
    # repr=False：token 不會被 print 或寫進 log
    discord_token: str = field(repr=False)
    channel_id: int
    claude_model: str
    data_dir: Path

    @property
    def photos_dir(self) -> Path:
        return self.data_dir / "photos"

    @property
    def ledger_path(self) -> Path:
        return self.data_dir / "food_log.xlsx"

    @property
    def log_path(self) -> Path:
        return self.data_dir / "agent.log"


def load_settings(env_path: Path | None = None) -> Settings:
    """從 .env 讀設定。用 dotenv_values 而不是 load_dotenv：
    token 只留在 Settings 裡，不會進到 os.environ，也就不會被 claude 子程序繼承。"""
    path = env_path or PROJECT_ROOT / ".env"
    if not path.is_file():
        raise ConfigError(f"找不到設定檔 {path}。請先建立 .env（見 .env.example）。")

    values = {k: (v or "").strip() for k, v in dotenv_values(path).items()}
    missing = [k for k in REQUIRED_KEYS if not values.get(k)]
    if missing:
        raise ConfigError(f".env 裡這些項目沒有填：{'、'.join(missing)}")

    channel_raw = values["CHANNEL_ID"]
    if not channel_raw.isdigit():
        raise ConfigError("CHANNEL_ID 必須是純數字（Discord 頻道的 ID）。")

    data_dir = Path(values["DATA_DIR"]).expanduser().resolve()
    return Settings(
        discord_token=values["DISCORD_TOKEN"],
        channel_id=int(channel_raw),
        claude_model=values["CLAUDE_MODEL"],
        data_dir=data_dir,
    )


def ensure_dirs(settings: Settings) -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.photos_dir.mkdir(parents=True, exist_ok=True)
