from __future__ import annotations

import asyncio

from conftest import make_job
from food_agent.queueing import Admit, JobQueue


def test_queue_full():
    q = JobQueue(max_waiting=2, per_user_max=10)
    assert q.submit(make_job(uid=1)) is Admit.OK
    assert q.submit(make_job(uid=2)) is Admit.OK
    assert q.submit(make_job(uid=3)) is Admit.QUEUE_FULL


def test_per_user_limit():
    q = JobQueue(max_waiting=10, per_user_max=2)
    assert q.submit(make_job(uid=1)) is Admit.OK
    assert q.submit(make_job(uid=1)) is Admit.OK
    assert q.submit(make_job(uid=1)) is Admit.USER_LIMIT
    assert q.submit(make_job(uid=2)) is Admit.OK  # 別人不受影響


def test_one_at_a_time_in_order_and_survives_errors():
    async def scenario():
        q = JobQueue(max_waiting=10, per_user_max=10)
        running = 0
        max_running = 0
        order: list[str] = []

        async def handler(job):
            nonlocal running, max_running
            running += 1
            max_running = max(max_running, running)
            await asyncio.sleep(0.01)
            order.append(job.caption)
            running -= 1
            if job.caption == "boom":
                raise RuntimeError("one bad job")

        for caption in ("a", "boom", "c", "d"):
            assert q.submit(make_job(caption=caption, uid=ord(caption[0]))) is Admit.OK
        worker = asyncio.create_task(q.run(handler))
        await q._queue.join()
        worker.cancel()
        return order, max_running

    order, max_running = asyncio.run(scenario())
    assert order == ["a", "boom", "c", "d"]  # 依序；中間一則出錯，後面照常處理
    assert max_running == 1  # 同一時間只有一個


def test_slot_is_released_after_processing():
    async def scenario():
        q = JobQueue(max_waiting=10, per_user_max=1)
        done = asyncio.Event()

        async def handler(job):
            done.set()

        assert q.submit(make_job(uid=1)) is Admit.OK
        assert q.submit(make_job(uid=1)) is Admit.USER_LIMIT
        worker = asyncio.create_task(q.run(handler))
        await q._queue.join()
        worker.cancel()
        return q.submit(make_job(uid=1))

    assert asyncio.run(scenario()) is Admit.OK
