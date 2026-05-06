"""Weather data fetcher using Open-Meteo API (free, no API key required)."""

import json
import ssl
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError

CONFIG_PATH = Path(__file__).parent.parent / "config.json"

WMO_CODES = {
    0: "晴",
    1: "大部晴",
    2: "多云",
    3: "阴",
    45: "雾",
    48: "冻雾",
    51: "小毛毛雨",
    53: "毛毛雨",
    55: "大毛毛雨",
    61: "小雨",
    63: "中雨",
    65: "大雨",
    71: "小雪",
    73: "中雪",
    75: "大雪",
    80: "阵雨",
    81: "中等阵雨",
    82: "强阵雨",
    95: "雷暴",
}


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_weather(lat: float = None, lon: float = None) -> dict:
    """Fetch tomorrow's weather from Open-Meteo.

    Returns a dict with:
        date, temp_high, temp_low, apparent_high, apparent_low,
        temp_feels_high, temp_feels_low, rain_prob, rain_sum,
        humidity, wind_speed, wind_gust, weather_code, weather_text,
        uv_index, daylight_hours, temp_range_large,
        needs_waterproof, needs_windproof, needs_breathable
    """
    if lat is None or lon is None:
        cfg = load_config()
        lat = cfg["location"]["latitude"]
        lon = cfg["location"]["longitude"]

    params = (
        f"latitude={lat}&longitude={lon}"
        f"&daily=temperature_2m_max,temperature_2m_min,apparent_temperature_max,"
        f"apparent_temperature_min,precipitation_probability_max,precipitation_sum,"
        f"weather_code,uv_index_max,wind_speed_10m_max,wind_gusts_10m_max,"
        f"daylight_duration,sunshine_duration"
        f"&timezone=auto&forecast_days=2"
    )
    url = f"https://api.open-meteo.com/v1/forecast?{params}"

    ctx = ssl.create_default_context()
    req = Request(url, headers={"User-Agent": "IntelliOutfit/1.0"})

    try:
        with urlopen(req, context=ctx, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except URLError as e:
        raise RuntimeError(f"天气 API 请求失败: {e}")

    daily = data["daily"]

    # Use tomorrow's data (index 1)
    idx = 1
    weather_code = daily["weather_code"][idx]

    result = {
        "date": daily["time"][idx],
        "temp_high": daily["temperature_2m_max"][idx],
        "temp_low": daily["temperature_2m_min"][idx],
        "apparent_high": daily["apparent_temperature_max"][idx],
        "apparent_low": daily["apparent_temperature_min"][idx],
        "rain_prob": daily["precipitation_probability_max"][idx],
        "rain_sum": daily["precipitation_sum"][idx],
        "wind_speed": daily["wind_speed_10m_max"][idx],
        "wind_gust": daily["wind_gusts_10m_max"][idx],
        "weather_code": weather_code,
        "weather_text": WMO_CODES.get(weather_code, f"未知({weather_code})"),
        "uv_index": daily["uv_index_max"][idx],
        "daylight_hours": round(daily["daylight_duration"][idx] / 3600, 1),
    }

    # Compute apparent temp range (feels-like, accounts for wind chill / humidity)
    result["temp_feels_high"] = result["apparent_high"]
    result["temp_feels_low"] = result["apparent_low"]

    # Determine key modifiers
    result["needs_waterproof"] = result["rain_prob"] > 50
    result["needs_windproof"] = result["wind_speed"] > 8
    result["needs_breathable"] = result.get("humidity", 0) > 80
    result["temp_range_large"] = (result["temp_high"] - result["temp_low"]) > 10

    return result


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 3:
        w = get_weather(float(sys.argv[1]), float(sys.argv[2]))
    else:
        w = get_weather()
    print(json.dumps(w, ensure_ascii=False, indent=2))
