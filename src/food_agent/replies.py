"""回覆上傳者的文字（docs/architecture.md 第 10 節）。"""

from __future__ import annotations

import discord

from food_agent import config
from food_agent.schema import Analysis

FAIL_ANALYSIS = "分析失敗，請再傳一次"
FAIL_FORMAT = "這個圖片格式我讀不了（支援 JPG、PNG、WebP、GIF）。沒有記錄。"
FAIL_TOO_BIG = f"檔案太大（上限 {config.MAX_FILE_BYTES // (1024 * 1024)} MB），沒有記錄。"
FAIL_LEDGER = "記錄檔現在寫不進去，這次沒有記錄。請稍後重傳。"
REJECT_QUEUE_FULL = "目前排隊的人太多，這張沒有收。請稍後再傳。"
REJECT_USER_LIMIT = f"你還有 {config.PER_USER_MAX} 則在處理中，請等處理完再傳。"


def _esc(text: str) -> str:
    """模型產生的文字放進回覆前，先把 Discord 的格式符號和 @ 提及處理掉。"""
    return discord.utils.escape_mentions(discord.utils.escape_markdown(text, ignore_links=False))


def build_success(mention: str, analysis: Analysis, total_kcal: int, truncated: bool) -> str:
    n_photos = len(analysis.photos)
    multi = n_photos > 1
    food_idx = [p.index for p in analysis.photos if p.is_food]
    non_food = [p for p in analysis.photos if not p.is_food]

    lines = [mention]
    meal = analysis.meal
    if meal is not None:
        if multi:
            head = f"食物（第 {'、'.join(map(str, food_idx))} 張）：{_esc(meal.name)}"
        else:
            head = f"這是食物：{_esc(meal.name)}"
        ingredients = "、".join(_esc(i) for i in meal.ingredients) or "（未列出）"
        lines += [
            head,
            f"成份：{ingredients}",
            f"估計重量：約 {meal.weight_g:,} 公克",
            f"估計熱量：約 {meal.kcal:,} 大卡",
        ]
    for p in non_food:
        if multi:
            lines.append(f"第 {p.index} 張不是食物，是{_esc(p.label)}。")
        else:
            lines.append(f"你傳的不是食物，是{_esc(p.label)}。")
    if non_food:
        lines.append("不是食物的照片已存檔，熱量沒有計入。")

    lines.append(f"當日已攝取熱量：{total_kcal:,} 大卡（整個頻道今天的合計）")
    if meal is not None:
        lines.append("（重量與熱量是用照片估的，會有誤差）")
    if truncated:
        lines.append(f"一次最多處理 {config.MAX_PHOTOS_PER_MESSAGE} 張，其餘沒有處理。")

    text = "\n".join(lines)
    limit = config.DISCORD_MESSAGE_MAX_CHARS - 10
    return text if len(text) <= limit else text[:limit] + "…"
