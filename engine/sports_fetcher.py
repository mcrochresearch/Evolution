#!/usr/bin/env python3
"""
SPORTS DATA FETCHER — Real odds from real sources.

Fetches calibrated probabilities from ESPN, odds APIs, and public
Elo databases. Disk-cached to avoid API hammering.

Data sources:
- ESPN API: Free, no key needed. Pre-game win probabilities + scores.
- The Odds API: Aggregated sportsbook lines from 50+ bookmakers.
  Free tier: 500 requests/month. Key via ODDS_API_KEY env var.
- Elo databases: Static ratings fetched from public sources (538 GitHub, etc.)

Usage:
    python engine/sports_fetcher.py espn <sport> [--date YYYY-MM-DD]
    python engine/sports_fetcher.py odds <sport> [--market h2h|spreads|totals]
    python engine/sports_fetcher.py evaluate <sport> <event_id> <market_prices_json> [bankroll]
    python engine/sports_fetcher.py list-sports
    python engine/sports_fetcher.py clear-cache [--older-than-days N]
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
    from engine.sports_edge import (
        elo_win_probability, devig_odds, aggregate_sources,
        compute_sports_edge, evaluate_sports_signal,
        HOME_ADVANTAGE, CONFIDENCE_SPORTS_SINGLE,
        CONFIDENCE_SPORTS_MULTI, CONFIDENCE_SPORTS_STRONG,
    )
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from stats import now
    from sports_edge import (
        elo_win_probability, devig_odds, aggregate_sources,
        compute_sports_edge, evaluate_sports_signal,
        HOME_ADVANTAGE, CONFIDENCE_SPORTS_SINGLE,
        CONFIDENCE_SPORTS_MULTI, CONFIDENCE_SPORTS_STRONG,
    )

STATE_DIR = Path(os.environ.get("EVOLUTION_STATE_DIR", "evolution/.state"))
CACHE_DIR = STATE_DIR / "sports_cache"

# --- API Config ---
ESPN_API_BASE = "https://site.api.espn.com/apis/site/v2/sports"
ODDS_API_BASE = "https://api.the-odds-api.com/v4/sports"
ODDS_API_KEY = os.environ.get("ODDS_API_KEY", "")

REQUEST_TIMEOUT = 15
MAX_RETRIES = 3
RETRY_BACKOFF = [1, 2, 4]
CACHE_TTL_HOURS = 2  # Sports odds move fast — shorter TTL than weather

# ESPN sport slugs → API paths
ESPN_SPORTS = {
    "nfl": "football/nfl",
    "nba": "basketball/nba",
    "mlb": "baseball/mlb",
    "nhl": "hockey/nhl",
    "ncaaf": "football/college-football",
    "ncaab": "basketball/mens-college-basketball",
    "soccer_epl": "soccer/eng.1",
    "soccer_mls": "soccer/usa.1",
    "soccer_champions": "soccer/uefa.champions",
    "mma_ufc": "mma/ufc",
    "tennis_atp": "tennis/atp",
}

# The Odds API sport keys
ODDS_SPORTS = {
    "nfl": "americanfootball_nfl",
    "nba": "basketball_nba",
    "mlb": "baseball_mlb",
    "nhl": "icehockey_nhl",
    "ncaaf": "americanfootball_ncaaf",
    "ncaab": "basketball_ncaab",
    "soccer_epl": "soccer_epl",
    "soccer_mls": "soccer_usa_mls",
    "mma_ufc": "mma_mixed_martial_arts",
    "tennis_atp": "tennis_atp_french_open",
}


def _http_get(url: str, headers: dict = None) -> dict:
    """HTTP GET with retries."""
    last_error = None
    hdrs = {"User-Agent": "Evolution/1.0", "Accept": "application/json"}
    if headers:
        hdrs.update(headers)
    for attempt in range(MAX_RETRIES):
        try:
            req = urllib.request.Request(url, headers=hdrs)
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_BACKOFF[attempt])
    raise ConnectionError(f"Failed after {MAX_RETRIES} attempts: {last_error}")


def _cache_key(source: str, sport: str, extra: str = "") -> str:
    raw = f"{source}_{sport}_{extra}_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def _cache_path(source: str, sport: str, extra: str = "") -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    key = _cache_key(source, sport, extra)
    return CACHE_DIR / f"sports_{key}.json"


def _is_cache_valid(cache_file: Path) -> bool:
    if not cache_file.exists():
        return False
    try:
        with open(cache_file) as f:
            data = json.load(f)
        cached_at = data.get("fetched_at", "")
        if not cached_at:
            return False
        cached_dt = datetime.fromisoformat(cached_at.replace("Z", "+00:00"))
        if cached_dt.tzinfo is None:
            cached_dt = cached_dt.replace(tzinfo=timezone.utc)
        age = datetime.now(timezone.utc) - cached_dt
        return age.total_seconds() < CACHE_TTL_HOURS * 3600
    except (json.JSONDecodeError, ValueError, IOError):
        return False


def _save_cache(cache_file: Path, data: dict):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(cache_file, "w") as f:
            json.dump(data, f, indent=2)
    except IOError:
        pass


# ============================================================================
# ESPN FETCHER
# ============================================================================

def fetch_espn_scoreboard(sport: str, date: str = None) -> dict:
    """Fetch ESPN scoreboard with win probabilities.

    ESPN's API is free, no key required. Returns upcoming and live games
    with pre-game win probabilities when available.

    Args:
        sport: Sport key (nfl, nba, mlb, nhl, soccer_epl, etc.)
        date: Optional date filter (YYYYMMDD format for ESPN).

    Returns:
        Dict with list of events and parsed probabilities.
    """
    espn_path = ESPN_SPORTS.get(sport)
    if not espn_path:
        return {"error": f"Unknown sport '{sport}'. Available: {list(ESPN_SPORTS.keys())}"}

    cache_file = _cache_path("espn", sport, date or "today")
    if _is_cache_valid(cache_file):
        with open(cache_file) as f:
            return json.load(f)

    url = f"{ESPN_API_BASE}/{espn_path}/scoreboard"
    if date:
        url += f"?dates={date.replace('-', '')}"

    try:
        raw = _http_get(url)
    except ConnectionError as e:
        return {"error": f"ESPN API failed: {e}"}

    events = []
    for event in raw.get("events", []):
        try:
            ev = _parse_espn_event(event, sport)
            if ev:
                events.append(ev)
        except (KeyError, TypeError, ValueError):
            continue

    result = {
        "sport": sport,
        "source": "espn",
        "events": events,
        "count": len(events),
        "fetched_at": now(),
    }

    _save_cache(cache_file, result)
    return result


def _parse_espn_event(event: dict, sport: str) -> dict:
    """Parse a single ESPN event into our standard format."""
    competitions = event.get("competitions", [{}])
    if not competitions:
        return None
    comp = competitions[0]

    competitors = comp.get("competitors", [])
    if len(competitors) < 2:
        return None

    # ESPN puts home team first sometimes, away first other times
    teams = []
    home_idx = None
    for i, c in enumerate(competitors):
        team_info = {
            "name": c.get("team", {}).get("displayName", c.get("team", {}).get("name", f"Team {i}")),
            "abbreviation": c.get("team", {}).get("abbreviation", ""),
            "is_home": c.get("homeAway") == "home",
            "score": c.get("score", "0"),
            "record": c.get("records", [{}])[0].get("summary", "") if c.get("records") else "",
        }
        if team_info["is_home"]:
            home_idx = i
        teams.append(team_info)

    # Extract win probability if available
    # ESPN provides this in the "predictor" or "winprobability" section
    situation = comp.get("situation", {})
    probabilities = comp.get("odds", [])

    team_a_prob = None
    team_b_prob = None

    # Try predictor
    predictor = event.get("predictor", comp.get("predictor", {}))
    if predictor:
        home_prob = predictor.get("homeTeam", {}).get("gameProjection")
        away_prob = predictor.get("awayTeam", {}).get("gameProjection")
        if home_prob is not None:
            home_prob = float(home_prob) / 100.0
            away_prob = float(away_prob) / 100.0 if away_prob else 1.0 - home_prob
            if home_idx == 0:
                team_a_prob = home_prob
                team_b_prob = away_prob
            else:
                team_a_prob = away_prob
                team_b_prob = home_prob

    # Try odds section for sportsbook lines
    odds_data = None
    if probabilities:
        odds_entry = probabilities[0] if isinstance(probabilities, list) else probabilities
        spread = odds_entry.get("spread")
        over_under = odds_entry.get("overUnder")
        details = odds_entry.get("details", "")
        odds_data = {
            "spread": spread,
            "over_under": over_under,
            "details": details,
            "provider": odds_entry.get("provider", {}).get("name", ""),
        }

        # Convert spread to implied probability if no predictor
        if team_a_prob is None and spread is not None:
            try:
                spread_val = float(spread)
                # Rough spread-to-probability conversion
                # NFL: each point ≈ 2.7% win probability
                # NBA: each point ≈ 1.5% win probability
                # Each spread point ≈ X% win probability shift
                pct_per_point = {"nfl": 0.027, "nba": 0.015, "mlb": 0.04, "nhl": 0.035}.get(sport, 0.025)
                home_edge = -spread_val * pct_per_point
                home_prob = 0.5 + home_edge
                home_prob = max(0.05, min(0.95, home_prob))
                if home_idx == 0:
                    team_a_prob = round(home_prob, 4)
                    team_b_prob = round(1.0 - home_prob, 4)
                else:
                    team_a_prob = round(1.0 - home_prob, 4)
                    team_b_prob = round(home_prob, 4)
            except (ValueError, TypeError):
                pass

    status = event.get("status", {}).get("type", {})
    game_status = status.get("name", "STATUS_SCHEDULED")
    game_time = event.get("date", "")

    return {
        "event_id": event.get("id", ""),
        "name": event.get("name", f"{teams[0]['name']} vs {teams[1]['name']}"),
        "teams": teams,
        "home_team_idx": home_idx,
        "status": game_status,
        "game_time": game_time,
        "probabilities": {
            "team_a": team_a_prob,
            "team_b": team_b_prob,
            "source": "espn_predictor" if predictor else "espn_spread",
        } if team_a_prob is not None else None,
        "odds": odds_data,
        "sport": sport,
    }


# ============================================================================
# THE ODDS API FETCHER
# ============================================================================

def fetch_odds_api(sport: str, market: str = "h2h", regions: str = "us") -> dict:
    """Fetch sportsbook odds from The Odds API.

    Requires ODDS_API_KEY environment variable (free tier: 500 req/month).
    Returns odds from 50+ bookmakers with vig.

    Args:
        sport: Sport key (nfl, nba, etc.)
        market: "h2h" (moneyline), "spreads", "totals"
        regions: "us", "eu", "uk", "au"

    Returns:
        Dict with events and bookmaker odds.
    """
    if not ODDS_API_KEY:
        return {
            "error": "ODDS_API_KEY not set. Get a free key at https://the-odds-api.com",
            "events": [],
        }

    odds_key = ODDS_SPORTS.get(sport)
    if not odds_key:
        return {"error": f"Unknown sport '{sport}'. Available: {list(ODDS_SPORTS.keys())}"}

    cache_file = _cache_path("odds_api", sport, market)
    if _is_cache_valid(cache_file):
        with open(cache_file) as f:
            return json.load(f)

    url = (
        f"{ODDS_API_BASE}/{odds_key}/odds"
        f"?apiKey={ODDS_API_KEY}"
        f"&regions={regions}"
        f"&markets={market}"
        f"&oddsFormat=american"
    )

    try:
        raw = _http_get(url)
    except ConnectionError as e:
        return {"error": f"Odds API failed: {e}"}

    if not isinstance(raw, list):
        return {"error": "Unexpected API response", "raw": raw}

    events = []
    for event in raw:
        try:
            ev = _parse_odds_event(event, sport, market)
            if ev:
                events.append(ev)
        except (KeyError, TypeError, ValueError):
            continue

    result = {
        "sport": sport,
        "market": market,
        "source": "the_odds_api",
        "events": events,
        "count": len(events),
        "fetched_at": now(),
    }

    _save_cache(cache_file, result)
    return result


def _parse_odds_event(event: dict, sport: str, market: str) -> dict:
    """Parse a single Odds API event."""
    teams = [
        {"name": event.get("home_team", ""), "is_home": True},
        {"name": event.get("away_team", ""), "is_home": False},
    ]

    # Aggregate odds across bookmakers
    bookmaker_odds = []
    for bm in event.get("bookmakers", []):
        bm_name = bm.get("key", bm.get("title", "unknown"))
        for mkt in bm.get("markets", []):
            if mkt.get("key") != market:
                continue
            outcomes = mkt.get("outcomes", [])
            if len(outcomes) >= 2:
                odds_map = {}
                for o in outcomes:
                    odds_map[o["name"]] = o.get("price", 0)

                bookmaker_odds.append({
                    "bookmaker": bm_name,
                    "odds": odds_map,
                })

    if not bookmaker_odds:
        return None

    # Compute consensus by devigging each bookmaker then averaging
    all_fair_probs = []
    team_names = [teams[0]["name"], teams[1]["name"]]

    for bm in bookmaker_odds:
        odds_list = [bm["odds"].get(t, 0) for t in team_names]
        if all(o != 0 for o in odds_list):
            devigged = devig_odds(odds_list, odds_format="american")
            if "fair_probs" in devigged:
                all_fair_probs.append({
                    "name": bm["bookmaker"],
                    "probs": devigged["fair_probs"],
                    "weight": 1.0,
                })

    # Aggregate
    consensus = None
    if all_fair_probs:
        # Weight sharp books higher
        sharp_books = {"pinnacle", "betfair", "matchbook", "smarkets"}
        for s in all_fair_probs:
            if any(sharp in s["name"].lower() for sharp in sharp_books):
                s["weight"] = 2.0

        consensus = aggregate_sources(all_fair_probs)

    return {
        "event_id": event.get("id", ""),
        "name": f"{teams[1]['name']} @ {teams[0]['name']}",
        "teams": team_names,
        "home_team": teams[0]["name"],
        "away_team": teams[1]["name"],
        "status": "upcoming",
        "commence_time": event.get("commence_time", ""),
        "bookmaker_count": len(bookmaker_odds),
        "consensus": consensus,
        "bookmaker_odds": bookmaker_odds[:5],  # Top 5 for display
        "sport": sport,
    }


# ============================================================================
# COMBINED EVALUATION
# ============================================================================

def fetch_and_evaluate(
    sport: str,
    event_id: str = None,
    market_prices: list = None,
    bankroll: float = 0,
) -> dict:
    """Fetch from all available sources and evaluate edge for an event.

    Combines ESPN probabilities + Odds API devigged lines into a
    multi-source consensus, then computes edge vs Polymarket prices.

    Args:
        sport: Sport key.
        event_id: Specific event to evaluate (matches ESPN event_id).
        market_prices: Polymarket prices [team_a, team_b].
        bankroll: For Kelly sizing.

    Returns:
        Full evaluation with sources, consensus, and trade signals.
    """
    sources = []

    # 1. Fetch ESPN
    espn_data = fetch_espn_scoreboard(sport)
    espn_event = None
    if "events" in espn_data:
        for ev in espn_data["events"]:
            if event_id and ev.get("event_id") == event_id:
                espn_event = ev
                break
            elif not event_id and ev.get("probabilities"):
                espn_event = ev  # Take first event with probabilities
                break

    if espn_event and espn_event.get("probabilities"):
        probs = espn_event["probabilities"]
        if probs.get("team_a") is not None:
            sources.append({
                "name": "espn",
                "probs": [probs["team_a"], probs["team_b"]],
                "weight": 1.0,
            })

    # 2. Fetch Odds API
    odds_data = fetch_odds_api(sport)
    odds_event = None
    if "events" in odds_data:
        for ev in odds_data["events"]:
            if event_id and ev.get("event_id") == event_id:
                odds_event = ev
                break
            elif espn_event and not event_id:
                # Match by team names
                espn_teams = set(t["name"] for t in espn_event.get("teams", []))
                odds_teams = set(ev.get("teams", []))
                if espn_teams & odds_teams:
                    odds_event = ev
                    break

    if odds_event and odds_event.get("consensus"):
        consensus = odds_event["consensus"]
        if consensus.get("consensus_probs"):
            sources.append({
                "name": "odds_consensus",
                "probs": consensus["consensus_probs"],
                "weight": 1.5,  # Higher weight — aggregated from many books
            })

    # 3. Build evaluation
    if not sources:
        return {
            "error": "No probability data available for this event",
            "sport": sport,
            "event_id": event_id,
            "espn_available": espn_event is not None,
            "odds_available": odds_event is not None,
        }

    # Get team labels
    labels = []
    if espn_event:
        labels = [t["name"] for t in espn_event.get("teams", [])]
    elif odds_event:
        labels = odds_event.get("teams", ["Team A", "Team B"])

    # Aggregate sources
    consensus = aggregate_sources(sources)

    if market_prices is None:
        # No market prices — just return the consensus
        return {
            "sport": sport,
            "event": espn_event or odds_event,
            "sources": [{s["name"]: s["probs"]} for s in sources],
            "consensus": consensus,
            "labels": labels,
            "note": "Provide market_prices to compute edge",
            "fetched_at": now(),
        }

    # Compute edge
    edge = compute_sports_edge(
        consensus["consensus_probs"],
        market_prices,
        consensus["confidence"],
        labels,
    )

    result = {
        "sport": sport,
        "event": espn_event or odds_event,
        "sources": [{s["name"]: s["probs"]} for s in sources],
        "consensus": consensus,
        "labels": labels,
        "edge_analysis": edge,
        "fetched_at": now(),
    }

    # Run through pipeline if bankroll provided
    if bankroll > 0 and edge.get("actionable_trades"):
        try:
            from engine.trade_pipeline import evaluate_signal
        except ImportError:
            from trade_pipeline import evaluate_signal

        pipeline_results = []
        for trade in edge["actionable_trades"]:
            sig = {
                "market_id": f"{sport}_{trade.get('label', '')}",
                "category": "sports",
                "fair_prob": trade["fair_prob"],
                "market_price": trade["market_price"],
                "confidence": consensus["confidence"],
                "bankroll": bankroll,
            }
            pipeline_results.append(evaluate_signal(sig))

        result["pipeline_results"] = pipeline_results
        result["trades_approved"] = sum(1 for r in pipeline_results if r.get("action") == "TRADE")

    return result


def list_available_sports() -> dict:
    """List all supported sports with availability info."""
    sports = {}
    for key in sorted(set(list(ESPN_SPORTS.keys()) + list(ODDS_SPORTS.keys()))):
        sports[key] = {
            "espn": key in ESPN_SPORTS,
            "odds_api": key in ODDS_SPORTS,
            "odds_api_available": bool(ODDS_API_KEY) and key in ODDS_SPORTS,
        }
    return {
        "sports": sports,
        "odds_api_configured": bool(ODDS_API_KEY),
        "note": "Set ODDS_API_KEY env var for sportsbook odds (free: 500 req/month)",
    }


def clear_cache(older_than_days: int = 0) -> dict:
    """Clear cached sports data."""
    if not CACHE_DIR.exists():
        return {"cleared": 0}
    cleared = 0
    cutoff = time.time() - (older_than_days * 86400) if older_than_days > 0 else float("inf")
    for f in CACHE_DIR.glob("sports_*.json"):
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
        if cmd == "espn":
            if len(sys.argv) < 3:
                print(json.dumps({"error": "Usage: espn <sport> [--date YYYY-MM-DD]"}))
                sys.exit(1)
            sport = sys.argv[2]
            date = None
            if "--date" in sys.argv:
                idx = sys.argv.index("--date")
                date = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else None
            result = fetch_espn_scoreboard(sport, date)
            print(json.dumps(result, indent=2))

        elif cmd == "odds":
            if len(sys.argv) < 3:
                print(json.dumps({"error": "Usage: odds <sport> [--market h2h|spreads|totals]"}))
                sys.exit(1)
            sport = sys.argv[2]
            market = "h2h"
            if "--market" in sys.argv:
                idx = sys.argv.index("--market")
                market = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else "h2h"
            result = fetch_odds_api(sport, market)
            print(json.dumps(result, indent=2))

        elif cmd == "evaluate":
            if len(sys.argv) < 3:
                print(json.dumps({"error": "Usage: evaluate <sport> [event_id] [market_prices_json] [bankroll]"}))
                sys.exit(1)
            sport = sys.argv[2]
            event_id = sys.argv[3] if len(sys.argv) > 3 and not sys.argv[3].startswith("[") else None
            prices_idx = 4 if event_id else 3
            prices = json.loads(sys.argv[prices_idx]) if len(sys.argv) > prices_idx and sys.argv[prices_idx].startswith("[") else None
            bankroll_idx = prices_idx + 1
            bankroll = float(sys.argv[bankroll_idx]) if len(sys.argv) > bankroll_idx else 0
            result = fetch_and_evaluate(sport, event_id, prices, bankroll)
            print(json.dumps(result, indent=2))

        elif cmd == "list-sports":
            result = list_available_sports()
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
