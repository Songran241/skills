"""Outfit recommendation engine.

Combines weather data, wardrobe items, and dressing rules to produce outfit recommendations.
"""

import json
from pathlib import Path
from weather import get_weather
from wardrobe import get_all_items, filter_by_weather

REFERENCES_DIR = Path(__file__).parent.parent / "references"

# ── Color definitions ──────────────────────────────────────────────

NEUTRAL_COLORS = {"黑", "白", "灰", "藏蓝", "卡其", "军绿", "米白", "深灰", "浅灰", "炭灰"}
WARM_COLORS = {"棕", "驼", "酒红", "姜黄", "橙色", "土黄", "砖红", "咖啡", "巧克力", "燕麦"}
COOL_COLORS = {"深蓝", "灰蓝", "墨绿", "紫", "靛蓝", "雾蓝", "灰绿"}


def _classify_color(color: str) -> str:
    for palette, name in [(NEUTRAL_COLORS, "neutral"), (WARM_COLORS, "warm"), (COOL_COLORS, "cool")]:
        if color in palette:
            return name
    return "neutral"


# ── Temperature layer determination ─────────────────────────────────

def _determine_layers(temp_feels_avg: float) -> dict:
    """Determine required layers based on felt temperature."""
    if temp_feels_avg < -5:
        return {"layers": 3, "description": "三层+", "outer_thickness": (4, 5), "mid_thickness": (3, 4), "inner_thickness": (2, 3)}
    elif temp_feels_avg < 5:
        return {"layers": 3, "description": "三层", "outer_thickness": (4, 5), "mid_thickness": (3, 4), "inner_thickness": (2, 3)}
    elif temp_feels_avg < 12:
        return {"layers": 2, "description": "两层半", "outer_thickness": (3, 4), "inner_thickness": (2, 3)}
    elif temp_feels_avg < 18:
        return {"layers": 2, "description": "两层", "outer_thickness": (2, 3), "inner_thickness": (2, 2)}
    elif temp_feels_avg < 25:
        return {"layers": 1, "description": "单层+", "inner_thickness": (1, 2)}
    elif temp_feels_avg < 32:
        return {"layers": 1, "description": "单层", "inner_thickness": (1, 1)}
    else:
        return {"layers": 1, "description": "极简", "inner_thickness": (1, 1)}


# ── Style templates ─────────────────────────────────────────────────

STYLE_TEMPLATES = {
    "minimal": {
        "name": "极简通勤",
        "formula": "纯色上装 + 直筒裤/深色牛仔裤 + 简洁鞋",
        "color_rule": "neutral_only",
        "avoid": ["pattern", "large_logo"],
    },
    "japanese-casual": {
        "name": "日系盐系",
        "formula": "宽松上装 + 阔腿裤/宽直筒裤 + 帆布鞋",
        "color_rule": "low_saturation",
        "prefer_fit": ["宽松", "阔腿", "直筒"],
        "prefer_bulk": [1, 2],
    },
    "city-boy": {
        "name": "City Boy",
        "formula": "Oversized上装 + 短裤/宽松牛仔裤 + 厚底板鞋",
        "color_rule": "neutral_plus_accent",
        "prefer_bulk": [2, 3],
    },
    "techwear": {
        "name": "轻机能",
        "formula": "防水外套 + 工装裤 + 户外鞋",
        "color_rule": "dark_neutral",
        "require": {"outerwear": {"waterproof": True}},
    },
    "smart-casual": {
        "name": "简约精致",
        "formula": "针织衫/Polo + 西裤/斜纹裤 + 乐福鞋",
        "color_rule": "neutral_only",
    },
    "athleisure": {
        "name": "运动休闲",
        "formula": "运动上装 + 慢跑裤/运动短裤 + 跑鞋",
        "color_rule": "neutral_plus_accent",
        "prefer_warmth": [1, 2],
    },
}


def _rank_styles(weather: dict, preferences: list) -> list:
    """Return a ranked list of 2-3 style keys suitable for current weather and user preferences."""
    rain = weather["rain_prob"] > 50
    wind = weather["wind_speed"] > 8
    temp = (weather["temp_feels_high"] + weather["temp_feels_low"]) / 2

    primary = None
    secondary_pool = []

    # Determine primary style (best weather match)
    if rain:
        primary = "techwear"
    elif wind and temp < 18:
        primary = "techwear"
    elif temp < 12:
        primary = next((p for p in preferences if p in ["japanese-casual", "smart-casual"]), "smart-casual")
    elif temp < 25:
        primary = next((p for p in preferences if p in ["minimal", "japanese-casual", "city-boy"]), "minimal")
    else:
        primary = next((p for p in ["minimal", "city-boy", "athleisure"] if p in preferences), "minimal")

    # Build secondary pool: user-preferred styles that suit the weather, excluding primary
    ranked = [primary]

    # Temperature-appropriate styles that aren't the primary
    if temp < 5:
        eligible = ["smart-casual", "japanese-casual"]
    elif temp < 12:
        eligible = ["smart-casual", "minimal", "japanese-casual", "techwear"]
    elif temp < 18:
        eligible = ["minimal", "japanese-casual", "city-boy", "techwear", "smart-casual"]
    elif temp < 25:
        eligible = ["minimal", "japanese-casual", "city-boy", "athleisure", "smart-casual", "techwear"]
    else:
        eligible = ["minimal", "city-boy", "athleisure", "japanese-casual"]

    # Secondary: prefer user-preferred styles, then fall back to any eligible
    for pref in preferences:
        if pref in eligible and pref not in ranked:
            ranked.append(pref)
            if len(ranked) >= 3:
                return ranked

    for style in eligible:
        if style not in ranked:
            ranked.append(style)
            if len(ranked) >= 3:
                return ranked

    return ranked


# ── Color combination scoring ───────────────────────────────────────

def _score_color_combo(top_colors: list, bottom_colors: list, outer_colors: list, shoe_colors: list) -> tuple:
    """Score a color combination. Returns (score, reasoning). Higher is better."""
    all_colors = top_colors + bottom_colors + outer_colors + shoe_colors
    top_main = top_colors[0] if top_colors else "未知"
    bottom_main = bottom_colors[0] if bottom_colors else "未知"
    outer_main = outer_colors[0] if outer_colors else None
    shoe_main = shoe_colors[0] if shoe_colors else "未知"

    top_class = _classify_color(top_main)
    bottom_class = _classify_color(bottom_main)

    non_neutral = sum(1 for c in all_colors if _classify_color(c) != "neutral")

    score = 5
    reasons = []

    if non_neutral > 1:
        score -= non_neutral - 1
        if non_neutral > 1:
            reasons.append(f"有{non_neutral}个非中性色，可精简")

    if top_class == bottom_class and top_main != bottom_main:
        score += 2
        reasons.append("同色系渐变")
    elif top_class != bottom_class and top_class != "neutral" and bottom_class != "neutral":
        reasons.append("冷暖对比")

    if non_neutral == 0:
        score += 1
        reasons.append("全中性色安全搭配")

    if outer_main and _classify_color(outer_main) == "neutral":
        score += 1
        reasons.append(f"{outer_main}外套做中性基底")

    if shoe_main in all_colors[:3]:
        score += 1
        reasons.append("鞋色与上下装呼应")

    if {top_main, bottom_main} == {"黑", "棕"}:
        score -= 2
        reasons.append("黑棕明度接近，轮廓模糊")
    if {top_main, bottom_main} in [{"红", "绿"}, {"亮蓝", "亮橙"}]:
        score -= 3
        reasons.append("强对比色冲突")

    return score, "; ".join(reasons) if reasons else "基本协调"


# ── Layering compatibility ──────────────────────────────────────────

_LAYER_FIT_MATRIX = {
    1: {"修身": True, "常规": True, "宽松": True},
    2: {"修身": False, "常规": True, "宽松": True},
    3: {"修身": False, "常规": False, "宽松": True},
}


def _check_layer_fit(inner_bulk: int, outer_fit: str) -> bool:
    """Check if an inner layer can physically fit under an outer layer."""
    if inner_bulk is None:
        return True
    row = _LAYER_FIT_MATRIX.get(inner_bulk, {})
    return row.get(outer_fit, True)


# ── Warmth coherence scoring ─────────────────────────────────────────

def _score_warmth_coherence(weather: dict, combo: dict) -> tuple:
    """Score whether the outfit's total warmth matches weather needs."""
    feels_low = weather.get("temp_feels_low", weather.get("temp_low", 10))
    temp_range_large = weather.get("temp_range_large", False)

    total_warmth = 0
    for role in ["outer", "top", "bottom"]:
        item = combo.get(role)
        if item and item.get("warmth"):
            total_warmth += item["warmth"]

    if feels_low < -5:
        ideal_min, ideal_max = 10, 15
    elif feels_low < 5:
        ideal_min, ideal_max = 7, 12
    elif feels_low < 12:
        ideal_min, ideal_max = 5, 9
    elif feels_low < 18:
        ideal_min, ideal_max = 3, 6
    elif feels_low < 25:
        ideal_min, ideal_max = 1, 4
    else:
        ideal_min, ideal_max = 0, 2

    score = 0
    reasons = []

    if total_warmth < ideal_min:
        penalty = (ideal_min - total_warmth) * 2
        score -= penalty
        reasons.append(f"总保暖值{total_warmth}偏低(建议{ideal_min}-{ideal_max})")
    elif total_warmth > ideal_max:
        penalty = (total_warmth - ideal_max) * 2
        score -= penalty
        reasons.append(f"总保暖值{total_warmth}偏高(建议{ideal_min}-{ideal_max})")
    else:
        score += 1
        reasons.append(f"保暖适中({total_warmth})")

    if temp_range_large and combo.get("outer") and combo["outer"].get("warmth", 0) >= 2:
        score += 1
        reasons.append("可脱卸外层应对温差")

    return score, "; ".join(reasons) if reasons else "保暖基本合适"


# ── Style consistency scoring ───────────────────────────────────────

_STYLE_SHOE_MATCH = {
    "minimal":          {"sneakers": True, "loafers": True, "boots": False, "sandals": False},
    "japanese-casual":  {"sneakers": True, "loafers": True, "boots": False, "sandals": False},
    "city-boy":         {"sneakers": True, "loafers": False, "boots": False, "sandals": False},
    "techwear":         {"sneakers": True, "boots": True, "loafers": False, "sandals": False},
    "smart-casual":     {"loafers": True, "sneakers": True, "boots": False, "sandals": False},
    "athleisure":       {"sneakers": True, "loafers": False, "boots": False, "sandals": False},
}

_STYLE_OUTER_MATCH = {
    "minimal":          {"jacket": True, "blazer": True, "coat": True, "hoodie": False, "windbreaker": True},
    "japanese-casual":  {"coat": True, "blazer": True, "jacket": False, "hoodie": False, "windbreaker": True},
    "city-boy":         {"hoodie": True, "jacket": True, "coat": False, "blazer": False, "windbreaker": True},
    "techwear":         {"jacket": True, "windbreaker": True, "vest": True, "coat": False, "blazer": False, "hoodie": False},
    "smart-casual":     {"blazer": True, "coat": True, "jacket": True, "hoodie": False, "windbreaker": False},
    "athleisure":       {"hoodie": True, "jacket": True, "coat": False, "blazer": False, "windbreaker": True},
}


def _score_style_consistency(style_key: str, combo: dict) -> tuple:
    """Check whether shoe and outerwear match the style template."""
    score = 0
    reasons = []

    shoe = combo.get("shoe")
    if shoe:
        shoe_sub = shoe.get("subcategory", "")
        shoe_ok = _STYLE_SHOE_MATCH.get(style_key, {}).get(shoe_sub)
        if shoe_ok is False:
            score -= 3
            reasons.append(f"{style_key}风格与{shoe_sub}鞋不搭")
        elif shoe_ok is True:
            score += 1
            reasons.append("鞋与风格统一")

    outer = combo.get("outer")
    if outer:
        outer_sub = outer.get("subcategory", "")
        outer_ok = _STYLE_OUTER_MATCH.get(style_key, {}).get(outer_sub)
        if outer_ok is False:
            score -= 3
            reasons.append(f"{style_key}风格与{outer_sub}外层冲突")
        elif outer_ok is True:
            score += 0

    return score, "; ".join(reasons) if reasons else "风格基本统一"


# ── Main recommendation logic ───────────────────────────────────────

def recommend(weather: dict = None, preferences: list = None) -> list:
    """Generate outfit recommendations.

    Args:
        weather: Weather dict from weather.get_weather(). If None, fetches automatically.
        preferences: List of preferred style keys. If None, reads from config.

    Returns:
        List of up to 3 outfit dicts, each with:
            outfit: list of {role, item_name, image, colors, ...}
            style: style template name
            reason: explanation
            score: overall score
    """
    if weather is None:
        weather = get_weather()

    if preferences is None:
        config_path = Path(__file__).parent.parent / "config.json"
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        preferences = cfg.get("preferences", {}).get("style_bias", ["minimal"])

    items = get_all_items()
    if not items:
        return [{"outfit": [], "style": "无", "reason": "衣橱为空，请先通过 /add-clothes 添加衣物", "score": 0}]

    temp_avg = (weather["temp_feels_high"] + weather["temp_feels_low"]) / 2
    layers = _determine_layers(temp_avg)

    grouped = filter_by_weather(items, weather)

    tops = grouped.get("top", [])
    bottoms = grouped.get("bottom", [])
    outerwear = grouped.get("outerwear", [])
    shoes = grouped.get("shoes", [])

    need_outer = layers.get("layers", 1) >= 2 or weather["needs_waterproof"]
    if need_outer and weather["needs_waterproof"]:
        outerwear = [o for o in outerwear if o.get("waterproof")] or outerwear
    if need_outer and weather["needs_windproof"]:
        outerwear = [o for o in outerwear if o.get("windproof")] or outerwear

    style_keys = _rank_styles(weather, preferences)

    results = []
    used_tops = set()
    used_outers = set()
    used_shoes = set()

    for style_key in style_keys:
        style = STYLE_TEMPLATES.get(style_key, STYLE_TEMPLATES["minimal"])

        combinations = []
        for top in tops[:5]:
            for bottom in bottoms[:5]:
                for shoe in shoes[:4]:
                    outer_list = outerwear[:3] if (need_outer and outerwear) else [None]
                    for outer in outer_list:
                        combo = {"top": top, "bottom": bottom, "shoe": shoe}
                        if outer:
                            combo["outer"] = outer

                        if outer and top.get("bulk") and outer.get("fit"):
                            if not _check_layer_fit(top["bulk"], outer["fit"]):
                                continue

                        color_score, color_reason = _score_color_combo(
                            top.get("colors", []),
                            bottom.get("colors", []),
                            outer.get("colors", []) if outer else [],
                            shoe.get("colors", []),
                        )

                        style_bonus = 0
                        if style_key == "japanese-casual":
                            if top.get("fit") in ["宽松", "阔腿"]:
                                style_bonus += 1
                            if bottom.get("fit") in ["阔腿", "直筒", "宽松"]:
                                style_bonus += 1

                        prefer_bulk = style.get("prefer_bulk")
                        if prefer_bulk and top.get("bulk") in prefer_bulk:
                            style_bonus += 1
                        prefer_warmth = style.get("prefer_warmth")
                        if prefer_warmth and top.get("warmth") in prefer_warmth:
                            style_bonus += 0

                        warmth_score, warmth_reason = _score_warmth_coherence(weather, combo)
                        style_consistency_score, style_consistency_reason = _score_style_consistency(style_key, combo)

                        total_score = color_score + style_bonus + warmth_score + style_consistency_score

                        # Bonus for using previously unused items (diversity across styles)
                        diversity_bonus = 0
                        if results:  # Only apply after first style
                            if top["id"] not in used_tops:
                                diversity_bonus += 5
                            if outer and outer["id"] not in used_outers:
                                diversity_bonus += 3
                            if shoe["id"] not in used_shoes:
                                diversity_bonus += 3
                            if top["id"] in used_tops:
                                diversity_bonus -= 3  # mild penalty, not a hard ban
                        total_score += diversity_bonus

                        parts = [p for p in [color_reason, warmth_reason, style_consistency_reason] if p]
                        full_reason = "; ".join(parts)
                        combinations.append((total_score, full_reason, combo))

        if not combinations:
            continue

        combinations.sort(key=lambda x: x[0], reverse=True)

        # Pick best combo for this style, avoiding top duplication within same style
        seen_tops_in_style = set()
        best_combo = None
        for score, reason, combo in combinations:
            if combo["top"]["id"] in seen_tops_in_style:
                continue
            seen_tops_in_style.add(combo["top"]["id"])
            best_combo = (score, reason, combo)
            break

        if best_combo is None:
            continue

        score, reason, combo = best_combo
        used_tops.add(combo["top"]["id"])
        if combo.get("outer"):
            used_outers.add(combo["outer"]["id"])
        used_shoes.add(combo["shoe"]["id"])

        outfit_items = []
        if combo.get("outer"):
            outfit_items.append({
                "role": "outer", "item_name": combo["outer"]["name"],
                "image": combo["outer"].get("image", ""), "colors": combo["outer"].get("colors", []),
                "material": combo["outer"].get("material", ""),
            })
        outfit_items.append({
            "role": "top", "item_name": combo["top"]["name"],
            "image": combo["top"].get("image", ""), "colors": combo["top"].get("colors", []),
            "material": combo["top"].get("material", ""),
        })
        outfit_items.append({
            "role": "bottom", "item_name": combo["bottom"]["name"],
            "image": combo["bottom"].get("image", ""), "colors": combo["bottom"].get("colors", []),
        })
        outfit_items.append({
            "role": "shoes", "item_name": combo["shoe"]["name"],
            "image": combo["shoe"].get("image", ""), "colors": combo["shoe"].get("colors", []),
        })

        results.append({
            "outfit": outfit_items,
            "style": style["name"],
            "style_formula": style.get("formula", ""),
            "color_reason": reason,
            "layer_plan": layers["description"],
            "score": score,
            "alerts": _generate_alerts(weather, combo),
        })

        if len(results) >= 2:
            break

    return results


def _generate_alerts(weather: dict, combo: dict) -> list:
    """Generate practical alerts for the outfit."""
    alerts = []

    if weather["rain_prob"] > 50:
        has_waterproof = combo.get("outer") and combo["outer"].get("waterproof")
        shoe_is_safe = combo["shoe"].get("subcategory") in ["boots", "loafers"]
        if not has_waterproof:
            alerts.append(f"降雨概率{weather['rain_prob']}%，建议带伞或选防水外套")
        if not shoe_is_safe:
            alerts.append("雨天建议穿皮鞋/靴子，避免帆布鞋")

    if weather["temp_range_large"]:
        alerts.append(f"早晚温差大({weather['temp_low']}~{weather['temp_high']}°C)，可叠穿方便穿脱")

    if weather["wind_speed"] > 10:
        if combo.get("outer") and not combo["outer"].get("windproof"):
            alerts.append(f"风力较强({weather['wind_speed']}m/s)，建议选防风外层")

    if weather["uv_index"] and weather["uv_index"] > 7:
        alerts.append(f"紫外线强(UV {weather['uv_index']})，建议防晒或薄外套")

    return alerts
