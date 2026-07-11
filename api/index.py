from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import sys

# Add the parent directory to sys.path so we can import our existing modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from steam_api import get_player_summary, get_owned_games
from stats import compute_all_stats
from card_generator import generate_card

app = Flask(__name__)
CORS(app)

@app.route('/api/generate', methods=['POST', 'GET'])
def generate():
    if request.method == 'POST':
        data = request.get_json()
        steam_id = data.get('steam_id')
    else:
        steam_id = request.args.get('steam_id')

    if not steam_id:
        return jsonify({"error": "Steam ID or Vanity URL is required"}), 400

    try:
        # Fetch data
        profile = get_player_summary(steam_id)
        if not profile:
            return jsonify({"error": f"Could not find Steam profile for '{steam_id}'"}), 404

        resolved_steam_id = profile.get("steamid")
        games = get_owned_games(resolved_steam_id)
        if not games:
            return jsonify({"error": "No games found or profile is private."}), 404

        # Compute stats
        stats = compute_all_stats(games, steam_id=resolved_steam_id)

        # Generate base64 images
        base64_images = generate_card(profile, stats, return_base64=True)

        return jsonify({
            "success": True,
            "profile": {
                "name": profile.get("personaname"),
                "avatar": profile.get("avatarfull")
            },
            "images": base64_images
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# Required for Vercel to pick it up
if __name__ == '__main__':
    app.run(debug=True, port=5328)
