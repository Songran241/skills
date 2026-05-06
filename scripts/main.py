#!/usr/bin/env python3
"""IntelliOutfit CLI — called by Claude Code skill for outfit recommendations."""

import json
import sys
from pathlib import Path

# Ensure scripts/ is on the import path for flat imports
sys.path.insert(0, str(Path(__file__).parent))

from weather import get_weather
from wardrobe import get_all_items, add_item, get_catalog_stats
from recommender import recommend


def cmd_recommend():
    """Output outfit recommendations as JSON."""
    weather = get_weather()
    results = recommend(weather=weather)

    output = {
        "weather": {
            "date": weather["date"],
            "temp_high": weather["temp_high"],
            "temp_low": weather["temp_low"],
            "temp_feels_high": weather.get("temp_feels_high", weather["temp_high"]),
            "temp_feels_low": weather.get("temp_feels_low", weather["temp_low"]),
            "weather": weather["weather_text"],
            "rain_prob": weather["rain_prob"],
            "wind_speed": weather["wind_speed"],
            "uv_index": weather["uv_index"],
            "temp_range_large": weather["temp_range_large"],
            "needs_waterproof": weather["needs_waterproof"],
            "needs_windproof": weather["needs_windproof"],
        },
        "recommendations": results,
    }

    print(json.dumps(output, ensure_ascii=False, indent=2))


def cmd_weather():
    """Output weather data as JSON."""
    weather = get_weather()
    print(json.dumps(weather, ensure_ascii=False, indent=2))


def cmd_wardrobe():
    """Output wardrobe statistics as JSON."""
    stats = get_catalog_stats()
    items = get_all_items()
    print(json.dumps({"stats": stats, "items": items}, ensure_ascii=False, indent=2))


def cmd_add():
    """Add a clothing item from JSON data passed via stdin or --data arg."""
    data = None

    for i, arg in enumerate(sys.argv):
        if arg == "--data" and i + 1 < len(sys.argv):
            data = json.loads(sys.argv[i + 1])
            break

    if data is None:
        data = json.loads(sys.stdin.read())

    item_id = add_item(data)
    print(json.dumps({"status": "ok", "id": item_id}, ensure_ascii=False))


def main():
    if len(sys.argv) < 2:
        print("Usage: main.py <recommend|weather|wardrobe|add>", file=sys.stderr)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "recommend":
        cmd_recommend()
    elif cmd == "weather":
        cmd_weather()
    elif cmd == "wardrobe":
        cmd_wardrobe()
    elif cmd == "add":
        cmd_add()
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
