"""處理一則訊息的完整流程：下載 → 分析 → 存照片 → 建檔 → 組回覆（docs/architecture.md 第 4 節）。

這裡不碰 Discord，只回傳「成功或失敗」加「要回覆的文字」，所以可以不連 Discord 就測試。
任何一步失敗都走同一條路：刪掉這一則已存的照片、Excel 不新增列、回覆失敗訊息。
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path

from food_agent import replies
from food_agent.analyzer import analyze
from food_agent.config import Settings
from food_agent.ledger import Ledger, LedgerBusyError, LedgerError, LedgerRow
from food_agent.models import Job, PhotoFile
from food_agent.schema import Analysis, AnalysisError
from food_agent.storage import StorageError, delete_files, relative_to_data_dir, save_photo

log = logging.getLogger("food_agent.pipeline")

AnalyzeFn = Callable[[list[PhotoFile], str, Settings], Awaitable[Analysis]]


@dataclass(frozen=True)
class Outcome:
    ok: bool
    text: str


async def process_job(
    job: Job,
    settings: Settings,
    ledger: Ledger,
    analyze_fn: AnalyzeFn = analyze,
) -> Outcome:
    saved: list[Path] = []
    mention = f"<@{job.uploader_id}>"
    when = job.when.astimezone().replace(tzinfo=None)  # 本機時間，Excel 不收帶時區的時間
    try:
        photos = [PhotoFile(data=await s.read(), ext=s.ext) for s in job.sources]
        log.info("下載完成：%d 張，共 %.0f KB", len(photos), sum(len(p.data) for p in photos) / 1024)

        try:
            analysis = await analyze_fn(photos, job.caption, settings)
        except AnalysisError as exc:
            log.error("分析失敗（上傳者 %s）：%s", job.uploader_id, exc)
            return Outcome(False, replies.FAIL_ANALYSIS)

        meal = analysis.meal
        for verdict in analysis.photos:
            if not verdict.is_food:
                log.info("分析結果：第 %d 張不是食物，是 %s", verdict.index, verdict.label)
        if meal is not None:
            log.info(
                "分析結果：食物 %s（成份 %d 項），約 %d 公克、%d 大卡",
                meal.name, len(meal.ingredients), meal.weight_g, meal.kcal,
            )
        rows: list[LedgerRow] = []
        food_rel: list[str] = []
        non_food_rows: list[LedgerRow] = []
        for verdict, photo in zip(analysis.photos, photos):
            if verdict.is_food:
                assert meal is not None  # validate_analysis 已保證
                path = save_photo(photo.data, photo.ext, when, meal.name, settings.photos_dir)
                saved.append(path)
                food_rel.append(relative_to_data_dir(path, settings.data_dir))
                log.info("已存照片：%s", food_rel[-1])
            else:
                path = save_photo(
                    photo.data, photo.ext, when, f"不是食物_{verdict.label}", settings.photos_dir
                )
                saved.append(path)
                log.info("已存照片：%s", relative_to_data_dir(path, settings.data_dir))
                non_food_rows.append(
                    LedgerRow(
                        when=when,
                        uploader=job.uploader_name,
                        name="不是食物",
                        ingredients=verdict.label,
                        weight_g=None,
                        kcal=None,
                        photo_paths=[relative_to_data_dir(path, settings.data_dir)],
                    )
                )
        if meal is not None:
            rows.append(
                LedgerRow(
                    when=when,
                    uploader=job.uploader_name,
                    name=meal.name,
                    ingredients="、".join(meal.ingredients),
                    weight_g=meal.weight_g,
                    kcal=meal.kcal,
                    photo_paths=food_rel,
                )
            )
        rows += non_food_rows

        try:
            total = await asyncio.to_thread(ledger.append, rows)
        except LedgerBusyError as exc:
            log.error("%s", exc)
            delete_files(saved)
            log.info("已刪除這一則已存的 %d 張照片", len(saved))
            return Outcome(False, replies.FAIL_LEDGER)
        log.info("已寫入 Excel：%d 列，當日已攝取熱量 %d 大卡", len(rows), total)

        text = replies.build_success(mention, analysis, total, job.truncated)
        return Outcome(True, text)

    except (LedgerError, StorageError) as exc:
        log.error("建檔失敗（上傳者 %s）：%s", job.uploader_id, exc)
        delete_files(saved)
        log.info("已刪除這一則已存的 %d 張照片", len(saved))
        return Outcome(False, replies.FAIL_ANALYSIS)
    except Exception:
        log.exception("處理訊息時發生未預期的錯誤（上傳者 %s）", job.uploader_id)
        delete_files(saved)
        log.info("已刪除這一則已存的 %d 張照片", len(saved))
        return Outcome(False, replies.FAIL_ANALYSIS)
