#!/usr/bin/env python3
"""
OPEN-METEO FORECAST FETCHER — Real data, not LLM guessing.

Fetches calibrated weather forecasts from Open-Meteo's free API and converts
them into the format weather_edge.py expects. Includes disk caching to avoid
hammering the API and to enable offline backtesting.

Open-Meteo provides:
- Hourly/daily temperature forecasts (2m above ground)
- Min/max/mean temperature per day
- Ensemble model spread (uncertainty estimate)
- No API key required, generous rate limits

Usage:
    python engine/weather_fetcher.py fetch <lat> <lon> [--date YYYY-MM-DD]
    python engine/weather_fetcher.py fetch-range <lat> <lon> <start_date> <end_date>
    python engine/weather_fetcher.py cached <lat> <lon> <date>
    python engine/weather_fetcher.py evaluate <lat> <lon> <date> <bucket_edges_json> <market_prices_json> [bankroll]
    python engine/weather_fetcher.py clear-cache [--older-than-days N]
"""

import json
import hashlib
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, timezone, timedelta

try:
    from engine.stats import now
    from engine.weather_edge import (
        compute_weather_edge, compute_bucket_probabilities,
        get_forecast_uncertainty, CONFIDENCE_WEATHER,
    )
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from stats import now
    from weather_edge import (
        compute_weather_edge, compute_bucket_probabilities,
        get_forecast_uncertainty, CONFIDENCE_WEATHER,
    )

STATE_DIR = Path(os.environ.get("EVOLUTION_STATE_DIR", "evolution/.state"))
CACHE_DIR = STATE_DIR / "weather_cache"

# --- Constants ---
OPEN_METEO_BASE = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_ENSEMBLE = "https://ensemble-api.open-meteo.com/v1/ensemble"
REQUEST_TIMEOUT = 15           # seconds
CACHE_TTL_HOURS = 6            # Re-fetch if cache older than 6 hours
MAX_RETRIES = 3
RETRY_BACKOFF = [1, 2, 4]     # seconds between retries


def _cache_key(lat: float, lon: float, date: str) -> str:
    """Generate a stable cache key for a location+date."""
    raw = f"{lat:.4f}_{lon:.4f}_{date}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def _cache_path(lat: float, lon: float, date: str) -> Path:
    """Get the cache file path for a forecast."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    key = _cache_key(lat, lon, date)
    return CACHE_DIR / f"forecast_{key}.json"


def _is_cache_valid(cache_file: Path) -> bool:
    """Check if a cached forecast is still fresh enough."""
    if not cache_file.exists():
        return False
    try:
        with open(cache_file) as f:
            data = json.load(f)
        cached_at = data.get("fetched_at", "")
        if not cached_at:
            return False
        cached_dt = datetime.fromisoformat(cached_at.replace("Z", "+00:00"))
        age = datetime.now(timezone.utc) - cached_dt
        return age.total_seconds() < CACHE_TTL_HOURS * 3600
    except (json.JSONDecodeError, ValueError, IOError):
        return False


def _http_get(url: str) -> dict:
    """Make an HTTP GET request with retries and exponential backoff."""
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Evolution/1.0"})
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_BACKOFF[attempt])
    raise ConnectionError(f"Failed after {MAX_RETRIES} attempts: {last_error}")


def fetch_forecast(lat: float, lon: float, date: str = None) -> dict:
    """Fetch temperature forecast from Open-Meteo API.

    Args:
        lat: Latitude (-90 to 90).
        lon: Longitude (-180 to 180).
        date: Target date (YYYY-MM-DD). Defaults to tomorrow.

    Returns:
        Dict with forecast data including:
        - temperature_mean: Forecasted mean temperature in °C
        - temperature_min: Forecasted min
        - temperature_max: Forecasted max
        - forecast_sigma: Estimated uncertainty (°C)
        - days_ahead: How many days from now
        - raw: Full API response for debugging
    """
    if date is None:
        date = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%d")

    # Check cache first
    cache_file = _cache_path(lat, lon, date)
    if _is_cache_valid(cache_file):
        with open(cache_file) as f:
            return json.load(f)

    # Compute days ahead
    try:
        target = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        days_ahead = max(0, (target - datetime.now(timezone.utc)).days)
    except ValueError:
        days_ahead = 1

    # Fetch from Open-Meteo standard API
    params = (
        f"?latitude={lat}&longitude={lon}"
        f"&daily=temperature_2m_max,temperature_2m_min,temperature_2m_mean"
        f"&start_date={date}&end_date={date}"
        f"&timezone=auto"
    )
    url = OPEN_METEO_BASE + params

    try:
        raw = _http_get(url)
    except ConnectionError as e:
        return {"error": f"API request failed: {e}", "lat": lat, "lon": lon, "date": date}

    # Parse response
    daily = raw.get("daily", {})
    dates = daily.get("time", [])
    maxs = daily.get("temperature_2m_max", [])
    mins = daily.get("temperature_2m_min", [])
    means = daily.get("temperature_2m_mean", [])

    if not dates:
        return {"error": "No forecast data returned", "raw": raw}

    # Find our target date in the response
    idx = 0
    for i, d in enumerate(dates):
        if d == date:
            idx = i
            break

    t_max = maxs[idx] if idx < len(maxs) and maxs[idx] is not None else None
    t_min = mins[idx] if idx < len(mins) and mins[idx] is not None else None
    t_mean = means[idx] if idx < len(means) and means[idx] is not None else None

    # If mean is not provided, compute from min/max
    if t_mean is None and t_max is not None and t_min is not None:
        t_mean = (t_max + t_min) / 2.0

    if t_mean is None:
        return {"error": "Could not extract temperature from response", "raw": raw}

    # Estimate sigma from min/max range (roughly ±2σ covers min to max)
    if t_max is not None and t_min is not None:
        range_sigma = (t_max - t_min) / 4.0  # Approximate: range ≈ 4σ
    else:
        range_sigma = None

    # Use the larger of: range-based sigma or lead-time based sigma
    lead_sigma = get_forecast_uncertainty(days_ahead)
    if range_sigma is not None:
        sigma = max(range_sigma, lead_sigma)
    else:
        sigma = lead_sigma

    result = {
        "lat": lat,
        "lon": lon,
        "date": date,
        "days_ahead": days_ahead,
        "temperature_mean": round(t_mean, 1),
        "temperature_min": round(t_min, 1) if t_min is not None else None,
        "temperature_max": round(t_max, 1) if t_max is not None else None,
        "forecast_sigma": round(sigma, 2),
        "lead_time_sigma": round(lead_sigma, 2),
        "range_sigma": round(range_sigma, 2) if range_sigma is not None else None,
        "timezone": raw.get("timezone", ""),
        "fetched_at": now(),
        "source": "open-meteo",
        "cached": False,
    }

    # Try to get ensemble spread for better sigma estimate
    try:
        ensemble_result = _fetch_ensemble_sigma(lat, lon, date)
        if ensemble_result and "ensemble_sigma" in ensemble_result:
            result["ensemble_sigma"] = ensemble_result["ensemble_sigma"]
            result["ensemble_members"] = ensemble_result.get("ensemble_members", 0)
            # Use ensemble sigma if available (most accurate)
            result["forecast_sigma"] = round(
                max(ensemble_result["ensemble_sigma"], lead_sigma), 2
            )
    except Exception:
        pass  # Ensemble is optional enhancement

    # Cache the result
    result["cached"] = True
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(cache_file, "w") as f:
            json.dump(result, f, indent=2)
    except IOError:
        pass

    result["cached"] = False
    return result


def _fetch_ensemble_sigma(lat: float, lon: float, date: str) -> dict:
    """Fetch ensemble model spread for better uncertainty estimation.

    Uses Open-Meteo's ensemble API which provides ~50 model runs.
    The spread of the ensemble gives a calibrated uncertainty.
    """
    params = (
        f"?latitude={lat}&longitude={lon}"
        f"&daily=temperature_2m_mean"
        f"&start_date={date}&end_date={date}"
        f"&models=icon_seamless"
    )
    url = OPEN_METEO_ENSEMBLE + params

    try:
        raw = _http_get(url)
    except ConnectionError:
        return None

    # Parse ensemble members
    daily = raw.get("daily", {})
    means = daily.get("temperature_2m_mean", [])

    if not means or not isinstance(means, list):
        return None

    # For ensemble API, means might be a list of lists (one per member)
    # or a single list. Handle both.
    if isinstance(means[0], list):
        # Multiple members
        values = [m[0] for m in means if m and m[0] is not None]
    else:
        values = [m for m in means if m is not None]

    if len(values) < 3:
        return None

    # Compute standard deviation of ensemble
    mean_val = sum(values) / len(values)
    variance = sum((v - mean_val) ** 2 for v in values) / (len(values) - 1)
    import math
    sigma = math.sqrt(variance)

    return {
        "ensemble_sigma": round(sigma, 2),
        "ensemble_mean": round(mean_val, 1),
        "ensemble_members": len(values),
    }


def fetch_range(lat: float, lon: float, start_date: str, end_date: str) -> list:
    """Fetch forecasts for a date range.

    Returns a list of forecast dicts, one per day.
    """
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    results = []
    current = start
    while current <= end:
        date_str = current.strftime("%Y-%m-%d")
        result = fetch_forecast(lat, lon, date_str)
        results.append(result)
        current += timedelta(days=1)

    return results


def evaluate_with_fetch(
    lat: float,
    lon: float,
    date: str,
    bucket_edges: list,
    market_prices: list,
    bankroll: float = 0,
) -> dict:
    """Fetch forecast + compute edge in one call.

    This is the convenience function that does:
    1. Fetch forecast from Open-Meteo (with caching)
    2. Compute bucket probabilities
    3. Compare against market prices
    4. Return full edge analysis

    Args:
        lat, lon: Location coordinates.
        date: Target date (YYYY-MM-DD).
        bucket_edges: Temperature bucket boundaries.
        market_prices: Current Polymarket prices per bucket.
        bankroll: Optional bankroll for sizing.

    Returns:
        Dict with forecast data + edge analysis.
    """
    forecast = fetch_forecast(lat, lon, date)

    if "error" in forecast:
        return forecast

    edge_result = compute_weather_edge(
        forecast_mean=forecast["temperature_mean"],
        days_ahead=forecast["days_ahead"],
        bucket_edges=bucket_edges,
        market_prices=market_prices,
        custom_sigma=forecast["forecast_sigma"],
    )

    if "error" in edge_result:
        return {**forecast, **edge_result}

    # If bankroll provided, size positions via trade pipeline
    if bankroll > 0:
        try:
            from engine.trade_pipeline import evaluate_weather_market
        except ImportError:
            from trade_pipeline import evaluate_weather_market

        pipeline_result = evaluate_weather_market(
            forecast_mean=forecast["temperature_mean"],
            days_ahead=forecast["days_ahead"],
            bucket_edges=bucket_edges,
            market_prices=market_prices,
            bankroll=bankroll,
        )
        return {
            "forecast": forecast,
            "edge_analysis": edge_result,
            "pipeline": pipeline_result,
        }

    return {
        "forecast": forecast,
        "edge_analysis": edge_result,
    }


def clear_cache(older_than_days: int = 0):
    """Clear cached forecasts.

    Args:
        older_than_days: Only clear cache files older than this many days.
            0 = clear all.
    """
    if not CACHE_DIR.exists():
        return {"cleared": 0}

    cleared = 0
    cutoff = time.time() - (older_than_days * 86400) if older_than_days > 0 else float("inf")

    for f in CACHE_DIR.glob("forecast_*.json"):
        try:
            if older_than_days == 0 or f.stat().st_mtime < cutoff:
                f.unlink()
                cleared += 1
        except OSError:
            continue

    return {"cleared": cleared}


# ============================================================================
# CLI
# ============================================================================

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    try:
        if cmd == "fetch":
            if len(sys.argv) < 4:
                print(json.dumps({"error": "Usage: fetch <lat> <lon> [--date YYYY-MM-DD]"}))
                sys.exit(1)
            lat = float(sys.argv[2])
            lon = float(sys.argv[3])
            date = None
            if "--date" in sys.argv:
                idx = sys.argv.index("--date")
                date = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else None
            result = fetch_forecast(lat, lon, date)
            print(json.dumps(result, indent=2))

        elif cmd == "fetch-range":
            if len(sys.argv) < 6:
                print(json.dumps({"error": "Usage: fetch-range <lat> <lon> <start_date> <end_date>"}))
                sys.exit(1)
            results = fetch_range(float(sys.argv[2]), float(sys.argv[3]),
                                  sys.argv[4], sys.argv[5])
            print(json.dumps({"forecasts": results, "count": len(results)}, indent=2))

        elif cmd == "cached":
            if len(sys.argv) < 5:
                print(json.dumps({"error": "Usage: cached <lat> <lon> <date>"}))
                sys.exit(1)
            cache_file = _cache_path(float(sys.argv[2]), float(sys.argv[3]), sys.argv[4])
            if cache_file.exists():
                with open(cache_file) as f:
                    print(f.read())
            else:
                print(json.dumps({"error": "No cached forecast found"}))
                sys.exit(1)

        elif cmd == "evaluate":
            if len(sys.argv) < 7:
                print(json.dumps({"error": "Usage: evaluate <lat> <lon> <date> <bucket_edges_json> <market_prices_json> [bankroll]"}))
                sys.exit(1)
            bankroll = float(sys.argv[7]) if len(sys.argv) > 7 else 0
            result = evaluate_with_fetch(
                lat=float(sys.argv[2]),
                lon=float(sys.argv[3]),
                date=sys.argv[4],
                bucket_edges=json.loads(sys.argv[5]),
                market_prices=json.loads(sys.argv[6]),
                bankroll=bankroll,
            )
            print(json.dumps(result, indent=2))

        elif cmd == "clear-cache":
            days = 0
            if "--older-than-days" in sys.argv:
                idx = sys.argv.index("--older-than-days")
                days = int(sys.argv[idx + 1])
            result = clear_cache(days)
            print(json.dumps(result))

        else:
            print(json.dumps({"error": f"Unknown command: {cmd}"}))
            sys.exit(1)

    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
