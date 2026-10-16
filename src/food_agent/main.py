"""進入點：uv run food-agent"""

from __future__ import annotations

import logging
import shutil
import sys

import discord

from food_agent.bot import FoodBot
from food_agent.config import PROJECT_ROOT, ConfigError, ensure_dirs, load_settings
from food_agent.ledger import Ledger
from food_agent.logs import setup_logging


def _setup_stdio() -> None:
    """Windows 終端機預設不是 UTF-8，印中文會當掉。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass


def main() -> None:
    _setup_stdio()
    try:
        settings = load_settings()
    except ConfigError as exc:
        print(f"[設定錯誤] {exc}", file=sys.stderr)
        raise SystemExit(1) from None

    if shutil.which("claude") is None:
        print("[設定錯誤] 找不到 claude 指令。請確認 Claude Code 已安裝，且 claude 在 PATH 裡。", file=sys.stderr)
        raise SystemExit(1)

    ensure_dirs(settings)
    setup_logging(settings.log_path)
    log = logging.getLogger("food_agent")
    log.info("DATA_DIR：%s，模型：%s", settings.data_dir, settings.claude_model)
    if settings.data_dir.is_relative_to(PROJECT_ROOT):
        log.warning(
            "DATA_DIR 在專案資料夾裡面。照片和紀錄不可以 commit，請確認它有被 .gitignore 擋住"
            "（git check-ignore -v %s）；建議改放到專案之外。",
            settings.data_dir,
        )

    bot = FoodBot(settings, Ledger(settings.ledger_path))
    try:
        bot.run(settings.discord_token, log_handler=None)
    except discord.LoginFailure:
        log.error("DISCORD_TOKEN 不正確。請到 Developer Portal 的 Bot 頁重設 token，貼進 .env。")
        raise SystemExit(1) from None
    except discord.PrivilegedIntentsRequired:
        log.error("還沒打開 Message Content Intent。請到 Developer Portal 的 Bot 頁打開它（見 docs/discord-bot-setup.md）。")
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
