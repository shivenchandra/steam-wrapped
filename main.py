"""
main.py
Entry point. Run `python main.py` to generate your Steam Wrapped card.
"""

import sys
from steam_api import get_owned_games, get_player_summary, SteamAPIError
from stats import compute_all_stats
from card_generator import generate_card


def main():
    print("Fetching your Steam library...")
    try:
        games = get_owned_games()
        profile = get_player_summary()
    except SteamAPIError as e:
        print(f"\nError: {e}")
        sys.exit(1)

    print(f"Found {len(games)} games for {profile['personaname']}.")
    print("Crunching stats (this may take a moment - genre and achievement "
          "lookups are rate-limited by Steam)...")

    stats = compute_all_stats(games)

    print("Generating cards...")
    paths = generate_card(profile, stats)

    print(f"\nDone! Your Steam Wrapped cards are at:")
    for p in paths:
        print(f"  → {p}")


if __name__ == "__main__":
    main()
