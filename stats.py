"""
stats.py
Pure functions that turn raw Steam data into "Wrapped" facts.
Nothing here calls the network except get_genre_breakdown, which uses
a local cache file so we don't hammer Steam's rate-limited store API.
"""

import json
import os
import time
from steam_api import get_app_genres, get_player_achievements, get_global_achievement_percentages

GENRE_CACHE_FILE = "genre_cache.json"


def total_hours(games):
    """Total hours played across the whole library."""
    total_minutes = sum(g.get("playtime_forever", 0) for g in games)
    return round(total_minutes / 60, 1)


def game_count(games):
    """Total number of owned games."""
    return len(games)


def top_n_games(games, n=5):
    """
    Top N most-played games by total playtime.
    Returns list of dicts: [{name, hours}, ...] sorted descending.
    """
    sorted_games = sorted(games, key=lambda g: g.get("playtime_forever", 0), reverse=True)
    return [
        {
            "appid": g.get("appid"),
            "name": g["name"],
            "hours": round(g.get("playtime_forever", 0) / 60, 1),
        }
        for g in sorted_games[:n]
        if g.get("playtime_forever", 0) > 0
    ]


def backlog_games(games, threshold_minutes=60):
    """
    Games owned but barely touched (under threshold_minutes played).
    Returns list of dicts: [{name, minutes}, ...]
    """
    backlog = [
        {"name": g["name"], "minutes": g.get("playtime_forever", 0)}
        for g in games
        if g.get("playtime_forever", 0) < threshold_minutes
    ]
    return backlog


def longest_commitment(games):
    """The single game with the highest playtime. Returns dict or None."""
    if not games:
        return None
    top = max(games, key=lambda g: g.get("playtime_forever", 0))
    return {"name": top["name"], "hours": round(top.get("playtime_forever", 0) / 60, 1)}


def recently_active_games(games, n=5):
    """Games played in the last 2 weeks, sorted by recent playtime."""
    recent = [g for g in games if g.get("playtime_2weeks", 0) > 0]
    recent.sort(key=lambda g: g.get("playtime_2weeks", 0), reverse=True)
    return [
        {"name": g["name"], "hours_recent": round(g.get("playtime_2weeks", 0) / 60, 1)}
        for g in recent[:n]
    ]


def _load_genre_cache():
    if os.path.exists(GENRE_CACHE_FILE):
        with open(GENRE_CACHE_FILE, "r") as f:
            return json.load(f)
    return {}


def _save_genre_cache(cache):
    with open(GENRE_CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)


def get_genre_breakdown(games, max_games_to_check=60, sleep_between_calls=0.3):
    """
    Builds a {genre: total_hours} breakdown across the library.
    Uses a local JSON cache so re-runs don't re-hit the store API for
    games we've already looked up. Only checks the top-played games
    (max_games_to_check) to keep this fast and avoid rate limits -
    low playtime games barely move the needle anyway.
    """
    cache = _load_genre_cache()
    sorted_games = sorted(games, key=lambda g: g.get("playtime_forever", 0), reverse=True)
    games_to_check = sorted_games[:max_games_to_check]

    genre_hours = {}
    cache_updated = False

    for g in games_to_check:
        appid = str(g["appid"])
        hours = g.get("playtime_forever", 0) / 60
        if hours <= 0:
            continue

        if appid in cache:
            genres = cache[appid]
        else:
            genres = get_app_genres(appid)
            cache[appid] = genres
            cache_updated = True
            time.sleep(sleep_between_calls)  # be polite to Steam's rate limit

        for genre in genres:
            genre_hours[genre] = genre_hours.get(genre, 0) + hours

    if cache_updated:
        _save_genre_cache(cache)

    # Round for display, sort descending
    genre_hours = {k: round(v, 1) for k, v in genre_hours.items()}
    return dict(sorted(genre_hours.items(), key=lambda x: x[1], reverse=True))


def find_rarest_achievement(games, max_games_to_check=10):
    """
    Looks through your top-played games for the achievement you've
    unlocked with the lowest global completion percentage - your
    biggest "flex" stat. Returns a dict or None if nothing found.
    """
    sorted_games = sorted(games, key=lambda g: g.get("playtime_forever", 0), reverse=True)
    candidates = sorted_games[:max_games_to_check]

    rarest = None

    for g in candidates:
        appid = g["appid"]
        my_achievements = get_player_achievements(appid)
        unlocked = [a["apiname"] for a in my_achievements if a.get("achieved") == 1]
        if not unlocked:
            continue

        global_percents = get_global_achievement_percentages(appid)
        if not global_percents:
            continue

        for apiname in unlocked:
            percent = global_percents.get(apiname)
            if percent is None:
                continue
            if rarest is None or percent < rarest["percent"]:
                rarest = {
                    "game": g["name"],
                    "achievement": apiname,
                    "percent": round(percent, 2),
                }

    return rarest


def get_badge(computed_stats):
    """
    Simple rule-based badge assignment. Order matters - first match wins.
    computed_stats expects keys: total_hours, game_count, top_games,
    backlog, longest.
    """
    total = computed_stats.get("total_hours", 0)
    count = computed_stats.get("game_count", 0)
    backlog_count = len(computed_stats.get("backlog", []))
    top_games = computed_stats.get("top_games", [])

    top_game_hours = top_games[0]["hours"] if top_games else 0
    dominance_ratio = (top_game_hours / total) if total > 0 else 0

    if dominance_ratio > 0.5:
        return "The One-Game Wonder"
    if backlog_count > 20:
        return "The Backlog Builder"
    if count > 150:
        return "The Collector"
    if total > 2000:
        return "The Veteran"
    if total < 100:
        return "The Casual"
    return "The Balanced Gamer"


def compute_all_stats(games, include_genres=True, include_achievements=True):
    """
    Convenience function that runs everything and returns one dict
    ready to hand to the card generator.
    """
    stats = {
        "total_hours": total_hours(games),
        "game_count": game_count(games),
        "top_games": top_n_games(games),
        "backlog": backlog_games(games),
        "longest": longest_commitment(games),
        "recent": recently_active_games(games),
    }

    if include_genres:
        stats["genres"] = get_genre_breakdown(games)

    if include_achievements:
        stats["rarest_achievement"] = find_rarest_achievement(games)

    stats["badge"] = get_badge(stats)
    return stats


if __name__ == "__main__":
    # Manual test - run `python stats.py` after steam_api.py works.
    from steam_api import get_owned_games

    games = get_owned_games()
    stats = compute_all_stats(games, include_genres=False, include_achievements=False)
    print(json.dumps(stats, indent=2))
