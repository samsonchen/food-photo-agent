from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from food_agent.config import Settings, ensure_dirs
from food_agent.models import Job
from food_agent.schema import Analysis, Meal, PhotoVerdict


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    s = Settings(
        discord_token="TEST-TOKEN-NOT-REAL",
        channel_id=123,
        claude_model="sonnet",
        data_dir=tmp_path / "food-data",
    )
    ensure_dirs(s)
    return s


class FakePhoto:
    def __init__(self, data: bytes = b"\xff\xd8\xff fake jpeg", ext: str = ".jpg"):
        self._data = data
        self.ext = ext
        self.size = len(data)

    async def read(self) -> bytes:
        return self._data


def make_job(n_photos: int = 1, caption: str = "", name: str = "小明", uid: int = 1,
             when: datetime | None = None, truncated: bool = False) -> Job:
    return Job(
        sources=[FakePhoto() for _ in range(n_photos)],
        caption=caption,
        uploader_name=name,
        uploader_id=uid,
        when=(when or datetime(2026, 10, 15, 12, 30, 45)).astimezone(),
        truncated=truncated,
    )


def food_analysis(name: str = "牛肉麵", kcal: int = 650, n: int = 1) -> Analysis:
    return Analysis(
        photos=tuple(PhotoVerdict(i, True, "") for i in range(1, n + 1)),
        meal=Meal(name=name, ingredients=("麵條", "牛肉"), weight_g=550, kcal=kcal),
    )


def non_food_analysis(label: str = "一隻貓") -> Analysis:
    return Analysis(photos=(PhotoVerdict(1, False, label),), meal=None)
