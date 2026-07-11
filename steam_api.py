"""
steam_api.py
All functions that talk to Steam's Web API.
Nothing in this file processes or interprets data - it just fetches raw JSON.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("STEAM_API_KEY")
STEAM_ID = os.getenv("STEAM_ID")

BASE_URL = "http://api.steampowered.com"
STORE_URL = "https://store.steampowered.com/api/appdetails"


class SteamAPIError(Exception):
    """Raised when the Steam API returns something we can't use."""
    pass


def _check_config():
    if not API_KEY or not STEAM_ID:
        raise SteamAPIError(
            "Missing STEAM_API_KEY or STEAM_ID. Copy .env.example to .env "
            "and fill in your values."
        )


def get_owned_games():
    """
    Fetch the full list of owned games with playtime.
    Returns a list of dicts: [{appid, name, playtime_forever, playtime_2weeks}, ...]
    """
    _check_config()
    url = f"{BASE_URL}/IPlayerService/GetOwnedGames/v0001/"
    params = {
        "key": API_KEY,
        "steamid": STEAM_ID,
        "format": "json",
        "include_appinfo": True,
        "include_played_free_games": True,
    }
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    response_block = data.get("response", {})
    if "games" not in response_block:
        raise SteamAPIError(
            "No games returned. This usually means the profile's game "
            "details are set to Private. Go to Steam > Settings > Privacy "
            "Settings and set 'Game details' to Public."
        )

    return response_block["games"]


def get_player_summary():
    """
    Fetch basic profile info: display name, avatar URL, profile URL.
    Returns a dict: {personaname, avatarfull, profileurl}
    """
    _check_config()
    url = f"{BASE_URL}/ISteamUser/GetPlayerSummaries/v0002/"
    params = {"key": API_KEY, "steamids": STEAM_ID}
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    players = data.get("response", {}).get("players", [])
    if not players:
        raise SteamAPIError("Could not fetch player summary. Check your STEAM_ID.")

    p = players[0]
    return {
        "personaname": p.get("personaname", "Unknown Player"),
        "avatarfull": p.get("avatarfull", ""),
        "profileurl": p.get("profileurl", ""),
    }


def get_player_achievements(appid):
    """
    Fetch the player's unlocked achievements for a single game.
    Returns a list of dicts: [{apiname, achieved, name, description}, ...]
    Returns [] if the game has no achievements or stats are private.
    """
    _check_config()
    url = f"{BASE_URL}/ISteamUserStats/GetPlayerAchievements/v0001/"
    params = {"key": API_KEY, "steamid": STEAM_ID, "appid": appid}
    try:
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code != 200:
            return []
        data = resp.json()
        return data.get("playerstats", {}).get("achievements", [])
    except (requests.RequestException, ValueError):
        return []


def get_global_achievement_percentages(appid):
    """
    Fetch global unlock percentages for every achievement in a game.
    Returns a dict: {apiname: percent}
    """
    url = f"{BASE_URL}/ISteamUserStats/GetGlobalAchievementPercentagesForApp/v0002/"
    params = {"gameid": appid}
    try:
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code != 200:
            return {}
        data = resp.json()
        achievements = data.get("achievementpercentages", {}).get("achievements", [])
        return {a["name"]: float(a["percent"]) for a in achievements}
    except (requests.RequestException, ValueError, KeyError):
        return {}


def get_app_genres(appid):
    """
    Fetch genre tags for a single game from the store API.
    Returns a list of genre name strings, e.g. ["Action", "FPS"]
    Returns [] on failure (rate limited, delisted app, etc).
    NOTE: this endpoint is rate-limited by Steam (~200 requests/5min),
    so callers should cache results (see stats.py's genre cache logic).
    """
    params = {"appids": appid}
    try:
        resp = requests.get(STORE_URL, params=params, timeout=10)
        if resp.status_code != 200:
            return []
        data = resp.json()
        app_data = data.get(str(appid), {})
        if not app_data.get("success"):
            return []
        genres = app_data.get("data", {}).get("genres", [])
        return [g["description"] for g in genres]
    except (requests.RequestException, ValueError, KeyError):
        return []


if __name__ == "__main__":
    # Quick manual test - run `python steam_api.py` to sanity check your setup.
    games = get_owned_games()
    print(f"Found {len(games)} owned games.")
    for g in sorted(games, key=lambda x: x.get("playtime_forever", 0), reverse=True)[:5]:
        hours = g.get("playtime_forever", 0) / 60
        print(f"  {g['name']}: {hours:.1f} hours")

    profile = get_player_summary()
    print(f"\nProfile: {profile['personaname']}")
