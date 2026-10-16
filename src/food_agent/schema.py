"""claude -p 的回覆格式，以及解析與驗證（docs/architecture.md 第 5 節）。

原則：任何不合格的輸出都丟出 AnalysisError，由呼叫端決定重試或回覆失敗，
不可以讓程式當掉，也不可以把不合格的結果寫進 Excel。
"""

from __future__ import annotations

import json
import math
import re
import unicodedata
from dataclasses import dataclass

from food_agent import config


class AnalysisError(Exception):
    """分析失敗（呼叫失敗、逾時、輸出不合格）。訊息只寫進 log，不顯示給上傳者。"""


# 傳給 claude -p --json-schema 的格式
RESULT_SCHEMA = {
    "type": "object",
    "properties": {
        "photos": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer"},
                    "is_food": {"type": "boolean"},
                    "label": {"type": ["string", "null"]},
                },
                "required": ["index", "is_food", "label"],
            },
        },
        "meal": {
            "type": ["object", "null"],
            "properties": {
                "name": {"type": "string"},
                "ingredients": {"type": "array", "items": {"type": "string"}},
                "weight_g": {"type": "number"},
                "kcal": {"type": "number"},
            },
            "required": ["name", "ingredients", "weight_g", "kcal"],
        },
    },
    "required": ["photos", "meal"],
}


@dataclass(frozen=True)
class PhotoVerdict:
    index: int  # 從 1 開始
    is_food: bool
    label: str  # 非食物時：它是什麼。食物時：空字串


@dataclass(frozen=True)
class Meal:
    name: str
    ingredients: tuple[str, ...]
    weight_g: int
    kcal: int


@dataclass(frozen=True)
class Analysis:
    photos: tuple[PhotoVerdict, ...]  # 依 index 排序
    meal: Meal | None  # 所有食物照片合起來的那一餐；沒有食物時是 None


def clean_text(value: str, max_chars: int) -> str:
    """去掉控制字元（換行變空白）、壓縮空白、前後去空白、截斷。"""
    out = []
    for ch in value:
        if unicodedata.category(ch) in ("Cc", "Cf", "Cs", "Co", "Cn"):
            out.append(" ")
        else:
            out.append(ch)
    text = re.sub(r"\s+", " ", "".join(out)).strip()
    return text[:max_chars].strip()


def _to_number(value: object, field_name: str, lo: int, hi: int) -> int:
    if isinstance(value, bool):
        raise AnalysisError(f"{field_name} 是 true/false，不是數字")
    if isinstance(value, (int, float)):
        num = float(value)
    elif isinstance(value, str):
        text = value.strip()
        if not re.fullmatch(r"\d+(\.\d+)?", text):
            raise AnalysisError(f"{field_name} 不是數字：{text[:30]!r}")
        num = float(text)
    else:
        raise AnalysisError(f"{field_name} 不是數字")
    if not math.isfinite(num):
        raise AnalysisError(f"{field_name} 不是有限的數字")
    result = int(round(num))
    if not lo <= result <= hi:
        raise AnalysisError(f"{field_name} 超出合理範圍 {lo}~{hi}：{result}")
    return result


def _extract_json_text(text: object) -> dict:
    """結構化欄位不存在時的備案：從文字結果裡找出第一段 JSON。"""
    if not isinstance(text, str):
        raise AnalysisError("輸出裡沒有結構化結果，也沒有文字結果")
    body = text.strip()
    body = re.sub(r"^```(?:json)?\s*|\s*```$", "", body, flags=re.IGNORECASE)
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        start, end = body.find("{"), body.rfind("}")
        if start < 0 or end <= start:
            raise AnalysisError("文字結果裡找不到 JSON") from None
        try:
            data = json.loads(body[start : end + 1])
        except json.JSONDecodeError as exc:
            raise AnalysisError(f"文字結果不是合法 JSON：{exc}") from None
    if not isinstance(data, dict):
        raise AnalysisError("JSON 最外層不是物件")
    return data


def parse_claude_output(raw: str, n_photos: int) -> Analysis:
    if len(raw) > config.CLAUDE_OUTPUT_MAX_CHARS:
        raise AnalysisError("claude 的輸出太長")
    try:
        outer = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AnalysisError(f"claude 的外層輸出不是合法 JSON：{exc}") from None
    if not isinstance(outer, dict):
        raise AnalysisError("claude 的外層輸出不是 JSON 物件")
    if outer.get("is_error"):
        raise AnalysisError(f"claude 回報錯誤：{str(outer.get('result'))[:200]}")

    data = outer.get("structured_output")
    if not isinstance(data, dict):
        data = _extract_json_text(outer.get("result"))
    return validate_analysis(data, n_photos)


def validate_analysis(data: dict, n_photos: int) -> Analysis:
    photos_raw = data.get("photos")
    if not isinstance(photos_raw, list) or len(photos_raw) != n_photos:
        raise AnalysisError(f"photos 的數量和照片張數 {n_photos} 對不上")

    verdicts: list[PhotoVerdict] = []
    for item in photos_raw:
        if not isinstance(item, dict):
            raise AnalysisError("photos 裡有不是物件的項目")
        index = item.get("index")
        if isinstance(index, bool) or not isinstance(index, int):
            raise AnalysisError("photos[].index 不是整數")
        is_food = item.get("is_food")
        if not isinstance(is_food, bool):
            raise AnalysisError("photos[].is_food 不是 true/false")
        label_raw = item.get("label")
        if label_raw is not None and not isinstance(label_raw, str):
            raise AnalysisError("photos[].label 不是文字")
        if is_food:
            label = ""
        else:
            label = clean_text(label_raw or "", config.LABEL_MAX_CHARS) or "不明物品"
        verdicts.append(PhotoVerdict(index=index, is_food=is_food, label=label))

    if sorted(v.index for v in verdicts) != list(range(1, n_photos + 1)):
        raise AnalysisError("photos 的編號沒有剛好涵蓋 1 到張數")
    verdicts.sort(key=lambda v: v.index)

    meal_raw = data.get("meal")
    any_food = any(v.is_food for v in verdicts)
    if any_food:
        if not isinstance(meal_raw, dict):
            raise AnalysisError("有食物照片，但 meal 不是物件")
        meal = _validate_meal(meal_raw)
    else:
        if meal_raw is not None:
            raise AnalysisError("沒有食物照片，但 meal 不是 null")
        meal = None
    return Analysis(photos=tuple(verdicts), meal=meal)


def _validate_meal(raw: dict) -> Meal:
    name_raw = raw.get("name")
    if not isinstance(name_raw, str):
        raise AnalysisError("meal.name 不是文字")
    name = clean_text(name_raw, config.NAME_MAX_CHARS) or "未命名"

    ingredients_raw = raw.get("ingredients")
    if not isinstance(ingredients_raw, list):
        raise AnalysisError("meal.ingredients 不是清單")
    ingredients: list[str] = []
    for item in ingredients_raw:
        if not isinstance(item, str):
            raise AnalysisError("meal.ingredients 裡有不是文字的項目")
        cleaned = clean_text(item, config.INGREDIENT_MAX_CHARS)
        if cleaned:
            ingredients.append(cleaned)
    ingredients = ingredients[: config.INGREDIENT_MAX_ITEMS]

    weight = _to_number(raw.get("weight_g"), "meal.weight_g", *config.WEIGHT_RANGE_G)
    kcal = _to_number(raw.get("kcal"), "meal.kcal", *config.KCAL_RANGE)
    return Meal(name=name, ingredients=tuple(ingredients), weight_g=weight, kcal=kcal)
