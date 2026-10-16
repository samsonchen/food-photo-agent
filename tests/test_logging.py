from __future__ import annotations

import asyncio
import logging

from conftest import food_analysis, make_job, non_food_analysis
from food_agent import logs
from food_agent.analyzer import analyze
from food_agent.ledger import Ledger
from food_agent.models import PhotoFile
from food_agent.pipeline import process_job
from food_agent.queueing import JobQueue

GOOD = (
    '{"total_cost_usd": 0.0123, "structured_output": {"photos": [{"index": 1, "is_food": true, "label": null}],'
    ' "meal": {"name": "牛肉麵", "ingredients": ["麵"], "weight_g": 500, "kcal": 600}}}'
)


def _messages(caplog):
    return [r.getMessage() for r in caplog.records]


def test_success_path_is_fully_logged(settings, caplog):
    caplog.set_level(logging.INFO)

    async def fake_analyze(photos, caption, s):
        return food_analysis()

    asyncio.run(process_job(make_job(n_photos=2), settings, Ledger(settings.ledger_path), analyze_fn=fake_analyze))
    text = "\n".join(_messages(caplog))
    for needle in ("下載完成：2 張", "分析結果：食物 牛肉麵", "已存照片：photos/", "已寫入 Excel：1 列，當日已攝取熱量 650 大卡"):
        assert needle in text


def test_non_food_result_is_logged(settings, caplog):
    caplog.set_level(logging.INFO)

    async def fake_analyze(photos, caption, s):
        return non_food_analysis("馬克杯")

    asyncio.run(process_job(make_job(), settings, Ledger(settings.ledger_path), analyze_fn=fake_analyze))
    assert "第 1 張不是食物，是 馬克杯" in "\n".join(_messages(caplog))


def test_failure_reason_is_logged_and_cleanup_noted(settings, caplog):
    caplog.set_level(logging.INFO)

    async def boom(photos, caption, s):
        raise RuntimeError("something odd")

    asyncio.run(process_job(make_job(), settings, Ledger(settings.ledger_path), analyze_fn=boom))
    text = "\n".join(_messages(caplog))
    assert "處理訊息時發生未預期的錯誤" in text and "已刪除這一則已存的 0 張照片" in text
    assert any(r.exc_info for r in caplog.records)  # 完整的錯誤堆疊也有記


def test_claude_call_is_logged_with_cost(settings, caplog):
    caplog.set_level(logging.INFO)

    async def runner(inv):
        return 0, GOOD, ""

    asyncio.run(analyze([PhotoFile(b"x", ".jpg")], "", settings, claude_bin="claude", runner=runner))
    text = "\n".join(_messages(caplog))
    assert "呼叫 claude -p（第 1/2 次，模型 sonnet，1 張照片）" in text
    assert "claude -p 完成：耗時" in text and "$0.0123" in text


def test_bad_claude_output_is_logged_as_warning(settings, caplog):
    caplog.set_level(logging.INFO)

    async def runner(inv):
        return 0, "not json", ""

    try:
        asyncio.run(analyze([PhotoFile(b"x", ".jpg")], "", settings, claude_bin="claude", runner=runner))
    except Exception:
        pass
    warnings = [r for r in caplog.records if r.levelname == "WARNING"]
    assert len(warnings) == 2 and "不合格" in warnings[0].getMessage()


def test_tag_filter_adds_job_tag():
    flt = logs.TagFilter()
    rec = logging.LogRecord("x", logging.INFO, "f", 1, "hello", None, None)
    flt.filter(rec)
    assert rec.tag == ""
    token = logs.job_tag.set(logs.tag_for(1234567890123456789))
    try:
        flt.filter(rec)
        assert rec.tag == "[#456789] "
    finally:
        logs.job_tag.reset(token)


def test_setup_logging_writes_file_and_terminal_with_tag(tmp_path, capsys):
    path = tmp_path / "agent.log"
    handlers = logs.setup_logging(path)
    try:
        token = logs.job_tag.set("#111222")
        logging.getLogger("food_agent.test").info("收到：測試")
        logs.job_tag.reset(token)
        logging.getLogger("food_agent.test").info("沒有編號")
        for h in handlers:
            h.flush()
        content = path.read_text(encoding="utf-8")
        assert "food_agent.test: [#111222] 收到：測試" in content
        assert "food_agent.test: 沒有編號" in content
        assert "[#111222] 收到：測試" in capsys.readouterr().out  # 終端機也有
    finally:
        for h in handlers:
            logging.getLogger().removeHandler(h)
            h.close()


def test_job_tag_follows_into_threads(settings, caplog):
    """寫 Excel 在 asyncio.to_thread 裡面，那裡的 log 也要帶著編號。"""
    seen = []

    async def go():
        token = logs.job_tag.set("#777888")
        try:
            await asyncio.to_thread(lambda: seen.append(logs.job_tag.get()))
        finally:
            logs.job_tag.reset(token)

    asyncio.run(go())
    assert seen == ["#777888"]


def test_queue_exposes_running_and_waiting():
    async def scenario():
        q = JobQueue()
        seen = {}

        async def handler(job):
            seen["running"], seen["waiting"] = q.running, q.waiting

        q.submit(make_job(uid=1))
        q.submit(make_job(uid=2))
        assert (q.running, q.waiting) == (0, 2)
        worker = asyncio.create_task(q.run(handler))
        await q._queue.join()
        worker.cancel()
        return seen, q.running

    seen, after = asyncio.run(scenario())
    assert seen["running"] == 1 and after == 0


def test_token_never_appears_in_logs(settings, caplog):
    caplog.set_level(logging.DEBUG)

    async def fake_analyze(photos, caption, s):
        return food_analysis()

    asyncio.run(process_job(make_job(), settings, Ledger(settings.ledger_path), analyze_fn=fake_analyze))
    assert settings.discord_token not in "\n".join(_messages(caplog))
    assert settings.discord_token not in repr(settings)
