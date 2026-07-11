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


def get_owned_games(steam_id=None):
    """
    Fetch the full list of owned games with playtime.
    Returns a list of dicts: [{appid, name, playtime_forever, playtime_2weeks}, ...]
    """
    sid = steam_id or STEAM_ID
    if not API_KEY or not sid:
        raise SteamAPIError("Missing STEAM_API_KEY or steam_id")

    url = f"{BASE_URL}/IPlayerService/GetOwnedGames/v0001/"
    params = {
        "key": API_KEY,
        "steamid": sid,
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


def resolve_vanity_url(vanity_url):
    """
    Resolve a Steam vanity URL name to a 64-bit Steam ID.
    Returns the Steam ID string, or None if it fails.
    """
    url = f"{BASE_URL}/ISteamUser/ResolveVanityURL/v0001/"
    params = {"key": API_KEY, "vanityurl": vanity_url}
    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        if data.get("response", {}).get("success") == 1:
            return data["response"]["steamid"]
    except Exception:
        pass
    return None

def get_player_summary(steam_id=None):
    """
    Fetch basic profile info: display name, avatar URL, profile URL.
    Returns a dict: {steamid, personaname, avatarfull, profileurl}
    """
    sid = steam_id or STEAM_ID
    if not API_KEY or not sid:
        raise SteamAPIError("Missing STEAM_API_KEY or steam_id")

    # If the user pasted a full URL, extract the last path segment
    if "/" in sid:
        sid = [p for p in sid.split("/") if p][-1]

    # If it's not a 17-digit number, assume it's a vanity URL
    if not (sid.isdigit() and len(sid) == 17):
        resolved = resolve_vanity_url(sid)
        if resolved:
            sid = resolved
        else:
            raise SteamAPIError(f"Could not resolve vanity URL '{sid}' to a Steam ID.")

    url = f"{BASE_URL}/ISteamUser/GetPlayerSummaries/v0002/"
    params = {"key": API_KEY, "steamids": sid}
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    players = data.get("response", {}).get("players", [])
    if not players:
        raise SteamAPIError("Could not fetch player summary. Check your STEAM_ID.")

    p = players[0]
    return {
        "steamid": p.get("steamid", sid),
        "personaname": p.get("personaname", "Unknown Player"),
        "avatarfull": p.get("avatarfull", ""),
        "profileurl": p.get("profileurl", ""),
    }


def get_player_achievements(appid, steam_id=None):
    """
    Fetch the player's unlocked achievements for a single game.
    Returns a list of dicts: [{apiname, achieved, name, description}, ...]
    Returns [] if the game has no achievements or stats are private.
    """
    sid = steam_id or STEAM_ID
    if not API_KEY or not sid:
        return []

    url = f"{BASE_URL}/ISteamUserStats/GetPlayerAchievements/v0001/"
    params = {"key": API_KEY, "steamid": sid, "appid": appid}
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
