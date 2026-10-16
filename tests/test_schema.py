from __future__ import annotations

import json

import pytest

from food_agent.schema import AnalysisError, parse_claude_output, validate_analysis


def _wrap(structured: object = None, result: object = None, **extra) -> str:
    outer = {"is_error": False, "type": "result", **extra}
    if structured is not None:
        outer["structured_output"] = structured
    if result is not None:
        outer["result"] = result
    return json.dumps(outer, ensure_ascii=False)


FOOD = {
    "photos": [{"index": 1, "is_food": True, "label": None}],
    "meal": {"name": "牛肉麵", "ingredients": ["麵條", "牛肉"], "weight_g": 550, "kcal": 650},
}
NON_FOOD = {"photos": [{"index": 1, "is_food": False, "label": "一隻貓"}], "meal": None}


def test_valid_food():
    a = parse_claude_output(_wrap(FOOD), 1)
    assert a.meal and a.meal.name == "牛肉麵" and a.meal.kcal == 650 and a.meal.weight_g == 550
    assert a.photos[0].is_food


def test_valid_non_food():
    a = parse_claude_output(_wrap(NON_FOOD), 1)
    assert a.meal is None
    assert a.photos[0].label == "一隻貓"


def test_non_food_without_label_gets_default():
    data = {"photos": [{"index": 1, "is_food": False, "label": None}], "meal": None}
    assert validate_analysis(data, 1).photos[0].label == "不明物品"


def test_food_label_is_ignored():
    data = json.loads(json.dumps(FOOD))
    data["photos"][0]["label"] = "牛肉麵"
    assert validate_analysis(data, 1).photos[0].label == ""


def test_numeric_strings_are_accepted():
    data = json.loads(json.dumps(FOOD))
    data["meal"]["kcal"] = "650"
    data["meal"]["weight_g"] = "550.4"
    a = validate_analysis(data, 1)
    assert a.meal.kcal == 650 and a.meal.weight_g == 550


@pytest.mark.parametrize("bad", ["約 650", "N/A", "", None, True, -5, 10**9, float("inf"), float("nan"), [650], "1e3"])
def test_bad_numbers_are_rejected(bad):
    for field in ("kcal", "weight_g"):
        data = json.loads(json.dumps(FOOD))
        data["meal"][field] = bad
        with pytest.raises(AnalysisError):
            validate_analysis(data, 1)


def test_mixed_photos():
    data = {
        "photos": [
            {"index": 2, "is_food": False, "label": "貓"},
            {"index": 1, "is_food": True, "label": None},
        ],
        "meal": FOOD["meal"],
    }
    a = validate_analysis(data, 2)
    assert [p.index for p in a.photos] == [1, 2]  # 依編號排序


@pytest.mark.parametrize(
    "data",
    [
        {"photos": [], "meal": None},  # 張數對不上
        {"photos": [{"index": 1, "is_food": True, "label": None}], "meal": None},  # 有食物卻沒有 meal
        {"photos": [{"index": 1, "is_food": False, "label": "貓"}], "meal": FOOD["meal"]},  # 沒食物卻有 meal
        {"photos": [{"index": 2, "is_food": False, "label": "貓"}], "meal": None},  # 編號不對
        {"photos": [{"index": 1, "is_food": "yes", "label": None}], "meal": None},  # is_food 不是布林
        {"photos": "oops", "meal": None},
        {"photos": [{"index": 1, "is_food": True, "label": None}], "meal": {"name": 5, "ingredients": [], "weight_g": 1, "kcal": 1}},
        {"photos": [{"index": 1, "is_food": True, "label": None}], "meal": {"name": "x", "ingredients": "麵", "weight_g": 1, "kcal": 1}},
    ],
)
def test_structure_errors(data):
    with pytest.raises(AnalysisError):
        validate_analysis(data, 1)


@pytest.mark.parametrize("raw", ["", "not json", "[1,2]", "null", "{", '{"is_error": true, "result": "boom"}'])
def test_outer_output_errors(raw):
    with pytest.raises(AnalysisError):
        parse_claude_output(raw, 1)


def test_fallback_to_result_text_with_code_fence():
    text = "```json\n" + json.dumps(FOOD, ensure_ascii=False) + "\n```"
    a = parse_claude_output(_wrap(result=text), 1)
    assert a.meal.name == "牛肉麵"


def test_fallback_finds_json_inside_prose():
    text = "好的，結果如下：" + json.dumps(NON_FOOD, ensure_ascii=False) + " 以上。"
    assert parse_claude_output(_wrap(result=text), 1).meal is None


def test_no_structured_and_no_result():
    with pytest.raises(AnalysisError):
        parse_claude_output(_wrap(), 1)


def test_text_is_cleaned_and_truncated():
    data = json.loads(json.dumps(FOOD))
    data["meal"]["name"] = "牛\n肉\x00麵" + "很長" * 50
    data["meal"]["ingredients"] = ["  麵  條 ", "", "x" * 100]
    a = validate_analysis(data, 1)
    assert "\n" not in a.meal.name and "\x00" not in a.meal.name
    assert len(a.meal.name) <= 30
    assert a.meal.ingredients[0] == "麵 條"
    assert all(len(i) <= 30 for i in a.meal.ingredients) and len(a.meal.ingredients) == 2


def test_empty_name_becomes_default():
    data = json.loads(json.dumps(FOOD))
    data["meal"]["name"] = "   "
    assert validate_analysis(data, 1).meal.name == "未命名"
