"""排隊：一次只處理一則訊息（docs/architecture.md 第 7 節）。

固定一個工作者從頭開始一則一則處理，所以同一時間只會有一個 claude -p，
Excel 也不會被兩個人同時寫。
"""

from __future__ import annotations

import asyncio
import enum
import logging
from collections import Counter
from collections.abc import Awaitable, Callable

from food_agent import config
from food_agent.models import Job

log = logging.getLogger("food_agent.queue")


class Admit(enum.Enum):
    OK = "ok"
    QUEUE_FULL = "queue_full"
    USER_LIMIT = "user_limit"


class JobQueue:
    def __init__(
        self,
        max_waiting: int = config.QUEUE_MAX_WAITING,
        per_user_max: int = config.PER_USER_MAX,
    ):
        self._queue: asyncio.Queue[Job] = asyncio.Queue()
        self._max_waiting = max_waiting
        self._per_user_max = per_user_max
        self._in_system: Counter[int] = Counter()  # 每個人在佇列裡的訊息數（含正在處理的）
        self._running = 0

    @property
    def waiting(self) -> int:
        """還在等的訊息數（不含正在處理的）。"""
        return self._queue.qsize()

    @property
    def running(self) -> int:
        """正在處理的訊息數，只會是 0 或 1。"""
        return self._running

    def submit(self, job: Job) -> Admit:
        if self._in_system[job.uploader_id] >= self._per_user_max:
            return Admit.USER_LIMIT
        if self._queue.qsize() >= self._max_waiting:
            return Admit.QUEUE_FULL
        self._in_system[job.uploader_id] += 1
        self._queue.put_nowait(job)
        return Admit.OK

    async def run(self, handler: Callable[[Job], Awaitable[None]]) -> None:
        """工作者。一則出錯只影響那一則，不會讓整個迴圈停掉。"""
        while True:
            job = await self._queue.get()
            self._running = 1
            try:
                await handler(job)
            except Exception:
                log.exception("處理一則訊息時發生未預期的錯誤，已略過，繼續處理下一則")
            finally:
                self._running = 0
                self._in_system[job.uploader_id] -= 1
                if self._in_system[job.uploader_id] <= 0:
                    del self._in_system[job.uploader_id]
                self._queue.task_done()
