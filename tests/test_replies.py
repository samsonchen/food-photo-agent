from __future__ import annotations

from conftest import food_analysis, non_food_analysis
from food_agent import config, replies


def test_food_reply_has_every_required_part():
    text = replies.build_success("<@1>", food_analysis(kcal=1234), 2345, False)
    for needle in ("這是食物：牛肉麵", "成份：麵條、牛肉", "估計重量：約 550 公克", "估計熱量：約 1,234 大卡",
                   "當日已攝取熱量：2,345 大卡", "會有誤差"):
        assert needle in text


def test_non_food_reply():
    text = replies.build_success("<@1>", non_food_analysis("一隻貓"), 100, False)
    assert "你傳的不是食物，是一隻貓。" in text and "當日已攝取熱量：100 大卡" in text
    assert "估計熱量" not in text


def test_markdown_and_mentions_from_model_are_neutralised():
    text = replies.build_success("<@1>", food_analysis(name="@everyone **粗體** [x](http://evil.example)"), 1, False)
    assert "@everyone" not in text.replace("@​everyone", "")
    assert "**粗體**" not in text
    assert "\\[x]" in text  # [ 前面有跳脫符號，不會變成可點的連結


def test_reply_never_exceeds_discord_limit():
    from food_agent.schema import Analysis, PhotoVerdict

    long_label = "字" * 5000
    big = Analysis(photos=tuple(PhotoVerdict(i, False, long_label) for i in range(1, 6)), meal=None)
    assert len(replies.build_success("<@1>", big, 0, False)) <= config.DISCORD_MESSAGE_MAX_CHARS
