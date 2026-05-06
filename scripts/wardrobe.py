"""Wardrobe catalog management: load, filter, add items."""

import json
from pathlib import Path

CATALOG_PATH = Path(__file__).parent.parent / "wardrobe" / "catalog.json"


def load_catalog() -> dict:
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_catalog(catalog: dict):
    with open(CATALOG_PATH, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)


def get_all_items() -> list:
    catalog = load_catalog()
    return catalog.get("items", [])


def add_item(item: dict, auto_id: bool = True):
    """Add a clothing item to the catalog.

    If auto_id is True, generates an ID from category + incrementing number.
    """
    catalog = load_catalog()
    items = catalog.get("items", [])

    if auto_id:
        cat = item.get("category", "unknown")
        existing = [i for i in items if i.get("category") == cat]
        item["id"] = f"{cat}-{len(existing) + 1:03d}"

    items.append(item)
    catalog["items"] = items
    save_catalog(catalog)
    return item["id"]


def filter_by_weather(items: list, weather: dict) -> dict:
    """Filter items suitable for given weather, return grouped by category.

    Returns:
        {
            "top": [...],
            "bottom": [...],
            "outerwear": [...],
            "shoes": [...]
        }
    """
    # Use apparent (feels-like) temperature — accounts for wind chill / humidity
    feels_high = weather.get("temp_feels_high", weather["temp_high"])
    feels_low = weather.get("temp_feels_low", weather["temp_low"])
    temp_mid = (feels_high + feels_low) / 2

    grouped = {"top": [], "bottom": [], "outerwear": [], "shoes": []}

    # Determine warmth coarse filter
    warmth_min = None
    warmth_max = None
    if feels_low < 5:
        warmth_min = 3
    elif feels_low < 12:
        warmth_min = 2
    if feels_high >= 25:
        warmth_max = 2

    for item in items:
        cat = item.get("category", "")
        if cat not in grouped:
            continue

        temp_range = item.get("temp_range", [-100, 100])

        # Check if the item's temp range overlaps with the day's range
        if temp_range[0] > feels_high or temp_range[1] < feels_low:
            continue

        item_warmth = item.get("warmth")
        if item_warmth is not None:
            if warmth_min is not None and item_warmth < warmth_min:
                continue
            if warmth_max is not None and item_warmth > warmth_max:
                continue
            # Shoes are accessories — relaxed warmth filter
            if cat == "shoes":
                if warmth_min is not None and item_warmth < warmth_min - 1:
                    continue
                if warmth_max is not None and item_warmth > warmth_max + 1:
                    continue

        grouped[cat].append(item)

    return grouped


def get_catalog_stats() -> dict:
    """Return summary statistics of the wardrobe."""
    items = get_all_items()
    stats = {"total": len(items)}
    for item in items:
        cat = item.get("category", "other")
        stats[cat] = stats.get(cat, 0) + 1
    return stats
