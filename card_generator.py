"""
card_generator.py
Renders a Playcope-inspired Steam Wrapped poster card as a PNG using Pillow.
"""

import os
from io import BytesIO

import requests
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps, ImageStat


CARD_WIDTH = 1080
CARD_HEIGHT = 1350

BLACK = "#262626"
INK = "#f3f2ec"
PAPER = "#ebe9df"
MUTED = "#d3d1c8"
YELLOW = "#f2c300"
RED = "#ff4b32"

FONT_DIR = "fonts"
FONT_BOLD_PATH = os.path.join(FONT_DIR, "bold.ttf")
FONT_REGULAR_PATH = os.path.join(FONT_DIR, "regular.ttf")

SYSTEM_HEAVY_FONTS = [
    r"C:\Windows\Fonts\ariblk.ttf",
    r"C:\Windows\Fonts\seguisb.ttf",
    r"C:\Windows\Fonts\arialbd.ttf",
]
SYSTEM_BOLD_FONTS = [
    r"C:\Windows\Fonts\seguisb.ttf",
    r"C:\Windows\Fonts\arialbd.ttf",
]
SYSTEM_REGULAR_FONTS = [
    r"C:\Windows\Fonts\segoeui.ttf",
    r"C:\Windows\Fonts\arial.ttf",
]


def _load_font(path, size, weight="regular"):
    weight_axis = {"heavy": 800, "bold": 700, "regular": 400}
    axis_value = weight_axis.get(weight, 400)
    if weight == "heavy":
        candidates = [path, *SYSTEM_HEAVY_FONTS]
    elif weight == "bold":
        candidates = [path, *SYSTEM_BOLD_FONTS]
    else:
        candidates = [path, *SYSTEM_REGULAR_FONTS]
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            font = ImageFont.truetype(candidate, size)
            try:
                font.set_variation_by_axes([axis_value])
            except (AttributeError, OSError):
                pass  # not a variable font, use as-is
            return font
    return ImageFont.load_default()


def _clean(text):
    return str(text).replace("™", "").replace("â„¢", "").strip()


def _text_size(draw, text, font):
    box = draw.textbbox((0, 0), str(text), font=font)
    return box[2] - box[0], box[3] - box[1]


def _fit_text(draw, text, font, max_width):
    text = _clean(text)
    if _text_size(draw, text, font)[0] <= max_width:
        return text
    while text and _text_size(draw, text + "...", font)[0] > max_width:
        text = text[:-1]
    return text.rstrip() + "..."


def _fit_font(draw, text, max_width, start_size, min_size=18, weight="heavy"):
    text = _clean(text)
    for size in range(start_size, min_size - 1, -2):
        font = _load_font(FONT_BOLD_PATH, size, weight)
        if _text_size(draw, text, font)[0] <= max_width:
            return font
    return _load_font(FONT_BOLD_PATH, min_size, weight)


def _wrap_text(draw, text, font, max_width, max_lines=2):
    words = _clean(text).split()
    lines = []
    current = ""
    for word in words:
        probe = f"{current} {word}".strip()
        if _text_size(draw, probe, font)[0] <= max_width:
            current = probe
            continue
        if current:
            lines.append(current)
        current = word
        if len(lines) == max_lines:
            break
    if current and len(lines) < max_lines:
        lines.append(current)
    if len(lines) == max_lines and len(" ".join(lines).split()) < len(words):
        lines[-1] = _fit_text(draw, lines[-1], font, max_width)
    return lines


def _draw_text(draw, xy, text, font, fill=INK, stroke=2, stroke_fill="#111111"):
    draw.text(xy, text, font=font, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)


def _draw_centered(draw, box, text, font, fill=BLACK, stroke=0):
    x1, y1, x2, y2 = box
    tw, th = _text_size(draw, text, font)
    draw.text(
        (x1 + (x2 - x1 - tw) / 2, y1 + (y2 - y1 - th) / 2 - 2),
        text,
        font=font,
        fill=fill,
        stroke_width=stroke,
        stroke_fill="#111111",
    )


def _fetch_image(url):
    try:
        resp = requests.get(url, timeout=12)
        resp.raise_for_status()
        return Image.open(BytesIO(resp.content)).convert("RGB")
    except (requests.RequestException, OSError):
        return None


def _fetch_avatar(url, size=188):
    img = _fetch_image(url) if url else None
    if img is None:
        return None
    img = ImageOps.fit(img, (size, size), Image.Resampling.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
    img = img.convert("RGBA")
    img.putalpha(mask)
    return img


def _is_blank_art(img):
    stat = ImageStat.Stat(img.convert("L"))
    low, high = stat.extrema[0]
    return high - low < 12


def _steam_art(appid, size, centering=(0.5, 0.35)):
    if not appid:
        return None
    urls = [
        f"https://cdn.akamai.steamstatic.com/steam/apps/{appid}/capsule_616x353.jpg",
        f"https://cdn.akamai.steamstatic.com/steam/apps/{appid}/header.jpg",
        f"https://cdn.akamai.steamstatic.com/steam/apps/{appid}/library_hero.jpg",
    ]
    for url in urls:
        img = _fetch_image(url)
        if img is None:
            continue
        img = ImageOps.fit(img, size, Image.Resampling.LANCZOS, centering=centering)
        if _is_blank_art(img):
            continue
        img = ImageEnhance.Contrast(img).enhance(1.08)
        img = ImageEnhance.Color(img).enhance(1.08)
        return img
    return None


def _poster_frame(draw, box, fill=None, outline=INK, width=4):
    if fill:
        draw.rectangle(box, fill=fill)
    draw.rectangle(box, outline=outline, width=width)


def _label(draw, box, text, font, inverted=False):
    fill = BLACK if inverted else PAPER
    text_fill = PAPER if inverted else BLACK
    draw.rectangle(box, fill=fill)
    draw.rectangle(box, outline=BLACK if not inverted else PAPER, width=2)
    label = _fit_text(draw, text, font, box[2] - box[0] - 24)
    _draw_centered(draw, box, label, font, fill=text_fill, stroke=0)


def _game_art_tile(base, box, game, font):
    draw = ImageDraw.Draw(base)
    art = _steam_art(game.get("appid"), (box[2] - box[0], box[3] - box[1]))
    _poster_frame(draw, [box[0] - 4, box[1] - 4, box[2] + 4, box[3] + 4], fill=INK, outline=INK, width=1)
    if art:
        base.paste(art, (box[0], box[1]))
        return
    draw.rectangle(box, fill=BLACK)
    draw.polygon([(box[0], box[1]), (box[2], box[1]), (box[0], box[3])], fill=YELLOW)
    draw.polygon([(box[2], box[1]), (box[2], box[3]), (box[0] + 40, box[3])], fill=RED)
    draw.rectangle([box[0] + 8, box[1] + 8, box[2] - 8, box[3] - 8], outline=INK, width=2)
    _draw_centered(draw, box, _fit_text(draw, game.get("name", "Game"), font, box[2] - box[0] - 20), font, fill=INK)


# ─── Card backgrounds ───────────────────────────────────────────────


def _draw_bg_overview(draw):
    """Background for the overview card."""
    draw.rectangle([0, 0, CARD_WIDTH, CARD_HEIGHT], fill=BLACK)
    # Vertical bar accent
    draw.rectangle([506, 0, 548, 380], fill=INK)
    draw.polygon([(548, 0), (660, 0), (548, 158)], fill=BLACK)
    draw.polygon([(548, 206), (660, 132), (660, 340), (548, 414)], fill=BLACK)
    # Top-left arcs
    draw.arc([-80, -110, 260, 260], 310, 100, fill=INK, width=4)
    draw.arc([-40, -70, 300, 300], 310, 100, fill=INK, width=3)
    # Top-right concentric circles
    for i in range(5):
        draw.arc(
            [708 + i * 30, 26 + i * 24, 1160 - i * 15, 350 + i * 38],
            184, 346, fill=INK, width=4,
        )
    # Bottom-right yellow accent
    draw.pieslice([886, 1050, 1358, 1450], 110, 250, fill=YELLOW)
    draw.pieslice([924, 1088, 1320, 1414], 110, 250, fill=BLACK)
    for i in range(3):
        draw.arc(
            [910 + i * 44, 1086 + i * 44, 1362 - i * 18, 1456 - i * 18],
            110, 250, fill=INK, width=12,
        )


def _draw_bg_games(draw):
    """Background for the top games card."""
    draw.rectangle([0, 0, CARD_WIDTH, CARD_HEIGHT], fill=BLACK)
    # Checkered strip top-left
    tile = 38
    for r in range(4):
        for c in range(5):
            if (r + c) % 2 == 0:
                draw.rectangle(
                    [c * tile, r * tile, (c + 1) * tile, (r + 1) * tile],
                    fill=INK,
                )
    # Bottom-left wavy arcs
    draw.arc([-80, 1120, 260, 1380], 310, 100, fill=INK, width=4)
    draw.arc([-40, 1160, 300, 1420], 310, 100, fill=INK, width=3)
    # Bottom-right yellow accent
    draw.pieslice([886, 1050, 1358, 1450], 110, 250, fill=YELLOW)
    draw.pieslice([924, 1088, 1320, 1414], 110, 250, fill=BLACK)
    for i in range(3):
        draw.arc(
            [910 + i * 44, 1086 + i * 44, 1362 - i * 18, 1456 - i * 18],
            110, 250, fill=INK, width=12,
        )


def _draw_bg_stats(draw):
    """Background for the stats card."""
    draw.rectangle([0, 0, CARD_WIDTH, CARD_HEIGHT], fill=BLACK)
    # Top-right concentric arcs
    for i in range(4):
        draw.arc(
            [780 + i * 35, -60 + i * 30, 1220 - i * 15, 300 + i * 35],
            180, 350, fill=INK, width=4,
        )
    # Bottom-right yellow accent
    draw.pieslice([886, 1050, 1358, 1450], 110, 250, fill=YELLOW)
    draw.pieslice([924, 1088, 1320, 1414], 110, 250, fill=BLACK)
    for i in range(3):
        draw.arc(
            [910 + i * 44, 1086 + i * 44, 1362 - i * 18, 1456 - i * 18],
            110, 250, fill=INK, width=12,
        )
    # Bottom-left wavy lines
    draw.line(
        [(30, 1280), (200, 1250), (400, 1290), (580, 1260)],
        fill=INK, width=3,
    )
    draw.line(
        [(30, 1290), (200, 1260), (400, 1300), (580, 1270)],
        fill=INK, width=2,
    )


# ─── Card 1: Overview ───────────────────────────────────────────────


def _generate_overview(profile, stats, output_path):
    """Card 1: Most played game, player name, total hours."""
    img = Image.new("RGB", (CARD_WIDTH, CARD_HEIGHT), BLACK)
    draw = ImageDraw.Draw(img)
    _draw_bg_overview(draw)

    font_label = _load_font(FONT_BOLD_PATH, 30, "heavy")
    font_hours = _load_font(FONT_BOLD_PATH, 110, "heavy")
    font_hrs = _load_font(FONT_BOLD_PATH, 48, "heavy")
    font_badge = _load_font(FONT_BOLD_PATH, 30, "heavy")
    font_stat_num = _load_font(FONT_BOLD_PATH, 56, "heavy")
    font_stat_lbl = _load_font(FONT_REGULAR_PATH, 22, "regular")
    font_small = _load_font(FONT_REGULAR_PATH, 18, "regular")

    top_games = stats.get("top_games", [])
    hero = top_games[0] if top_games else {}

    # ── Hero game art (bigger) ──
    art = _steam_art(hero.get("appid"), (560, 350), centering=(0.5, 0.42))
    hero_box = [60, 80, 620, 430]
    _poster_frame(draw, [55, 75, 625, 435], fill=INK, outline=INK, width=1)
    if art:
        img.paste(art, (hero_box[0], hero_box[1]))
    else:
        _game_art_tile(img, hero_box, hero, font_small)

    # ── Avatar ──
    avatar = _fetch_avatar(profile.get("avatarfull", ""), size=210)
    draw.ellipse([738, 80, 968, 310], outline=INK, width=5)
    if avatar:
        img.paste(avatar, (748, 90), avatar)

    # ── Player name box ──
    player = _clean(profile.get("personaname", "Player"))
    player_box = [640, 360, 1030, 480]
    draw.rectangle(player_box, fill=BLACK, outline=INK, width=4)
    fitted_player = _fit_font(
        draw, player, player_box[2] - player_box[0] - 40, 54, 32,
    )
    _draw_centered(
        draw, player_box, player, fitted_player, fill=INK, stroke=2,
    )
    # Wavy underline
    draw.line(
        [(640, 500), (790, 480), (930, 510), (1030, 484)],
        fill=INK, width=4,
    )
    draw.line(
        [(640, 510), (790, 490), (930, 520), (1030, 494)],
        fill=INK, width=2,
    )

    # ── Most Played Game ──
    draw.text(
        (70, 470), "Most Played Game", font=font_label,
        fill=INK, stroke_width=2, stroke_fill="#111111",
    )
    title = _clean(hero.get("name", "Top Game"))
    fitted_title = _fit_font(draw, title, 540, 72, 40)
    draw.text(
        (70, 530), title, font=fitted_title,
        fill=INK, stroke_width=3, stroke_fill="#111111",
    )

    # ── Total Hours (large & dramatic) ──
    draw.text(
        (70, 680), "Total Hours", font=font_label,
        fill=INK, stroke_width=2, stroke_fill="#111111",
    )
    hours_text = f"{stats.get('total_hours', 0):,.0f}"
    draw.text(
        (70, 740), hours_text, font=font_hours,
        fill=INK, stroke_width=3, stroke_fill="#111111",
    )
    hrs_x = 70 + _text_size(draw, hours_text, font_hours)[0] + 18
    draw.text(
        (hrs_x, 790), "hrs", font=font_hrs,
        fill=INK, stroke_width=2, stroke_fill="#111111",
    )

    # ── Mini stat boxes ──
    game_count = str(stats.get("game_count", 0))
    backlog_count = str(len(stats.get("backlog", [])))

    # Game count
    draw.text(
        (70, 940), game_count, font=font_stat_num,
        fill=INK, stroke_width=3, stroke_fill="#111111",
    )
    gc_w = _text_size(draw, game_count, font_stat_num)[0]
    draw.text(
        (70, 1000), "Games Owned", font=font_stat_lbl,
        fill=MUTED, stroke_width=1, stroke_fill="#111111",
    )

    # Separator dot
    sep_x = 70 + gc_w + 80
    draw.ellipse([sep_x, 960, sep_x + 8, 968], fill=MUTED)

    # Backlog count
    draw.text(
        (sep_x + 40, 940), backlog_count, font=font_stat_num,
        fill=INK, stroke_width=3, stroke_fill="#111111",
    )
    draw.text(
        (sep_x + 40, 1000), "Untouched", font=font_stat_lbl,
        fill=MUTED, stroke_width=1, stroke_fill="#111111",
    )

    # ── Badge ──
    badge = _clean(stats.get("badge", "Steam Gamer")).replace("The ", "")
    _label(draw, [70, 1080, 480, 1132], badge, font_badge)

    # ── Footer ──
    draw.text(
        (42, 1316), "STEAM-WRAPPED", font=font_small,
        fill=INK, stroke_width=1, stroke_fill="#111111",
    )

    img = img.filter(ImageFilter.UnsharpMask(radius=1, percent=110, threshold=3))
    img.save(output_path, quality=95)
    return output_path


# ─── Card 2: Top Games ──────────────────────────────────────────────


def _generate_games(stats, output_path):
    """Card 2: Top 5 most-played games list."""
    img = Image.new("RGB", (CARD_WIDTH, CARD_HEIGHT), BLACK)
    draw = ImageDraw.Draw(img)
    _draw_bg_games(draw)

    font_label = _load_font(FONT_BOLD_PATH, 30, "heavy")
    font_rank = _load_font(FONT_BOLD_PATH, 56, "heavy")
    font_name = _load_font(FONT_BOLD_PATH, 34, "heavy")
    font_hours = _load_font(FONT_REGULAR_PATH, 22, "regular")
    font_small = _load_font(FONT_REGULAR_PATH, 18, "regular")

    # Header
    _label(draw, [340, 50, 740, 106], "Our Top Games", font_label)

    top_games = stats.get("top_games", [])
    row_h = 190
    top_y = 160

    for i, game in enumerate(top_games[:5], start=1):
        y = top_y + (i - 1) * row_h

        # Rank number
        _draw_text(
            draw, (60, y + 28), str(i), font_rank, fill=INK, stroke=3,
        )

        # Game art thumbnail (bigger)
        _game_art_tile(img, [150, y + 8, 320, y + 120], game, font_small)

        # Game name
        name = _fit_text(draw, game.get("name", "Game"), font_name, 640)
        _draw_text(draw, (350, y + 22), name, font_name, fill=INK, stroke=2)

        # Hours played
        _draw_text(
            draw, (352, y + 72),
            f"{game.get('hours', 0):.0f} hours played",
            font_hours, fill=INK, stroke=1,
        )

        # Subtle separator
        if i < len(top_games[:5]):
            draw.line(
                [(60, y + row_h - 22), (1020, y + row_h - 22)],
                fill="#3a3a3a", width=1,
            )

    # Footer
    draw.text(
        (42, 1316), "STEAM-WRAPPED", font=font_small,
        fill=INK, stroke_width=1, stroke_fill="#111111",
    )

    img = img.filter(ImageFilter.UnsharpMask(radius=1, percent=110, threshold=3))
    img.save(output_path, quality=95)
    return output_path


# ─── Card 3: Stats & Achievement ────────────────────────────────────


def _generate_stats(stats, output_path):
    """Card 3: Steam stats summary and rarest achievement."""
    img = Image.new("RGB", (CARD_WIDTH, CARD_HEIGHT), BLACK)
    draw = ImageDraw.Draw(img)
    _draw_bg_stats(draw)

    font_label = _load_font(FONT_BOLD_PATH, 30, "heavy")
    font_rank = _load_font(FONT_BOLD_PATH, 48, "heavy")
    font_item = _load_font(FONT_BOLD_PATH, 38, "heavy")
    font_ach_label = _load_font(FONT_BOLD_PATH, 34, "heavy")
    font_ach = _load_font(FONT_REGULAR_PATH, 28, "regular")
    font_small = _load_font(FONT_REGULAR_PATH, 18, "regular")

    # Header
    _label(draw, [320, 50, 760, 106], "Your Steam Stats", font_label)

    rows = [
        ("1", f"{stats.get('game_count', 0)} Games"),
        ("2", f"{len(stats.get('backlog', []))} Untouched"),
        ("3", _clean(stats.get("badge", "Steam Wrapped")).replace("The ", "")),
        ("4", "All-Time Recap"),
    ]
    row_h = 120
    top_y = 170

    for i, (rank, value) in enumerate(rows):
        y = top_y + i * row_h
        _draw_text(draw, (80, y + 14), rank, font_rank, fill=INK, stroke=3)
        value = _fit_text(draw, value, font_item, 800)
        _draw_text(draw, (160, y + 20), value, font_item, fill=INK, stroke=2)
        if i < len(rows) - 1:
            draw.line(
                [(80, y + row_h - 12), (1000, y + row_h - 12)],
                fill="#3a3a3a", width=1,
            )

    # ── Rarest Achievement ──
    ach_y = top_y + len(rows) * row_h + 80
    rarest = stats.get("rarest_achievement")
    if rarest:
        _label(
            draw, [80, ach_y, 480, ach_y + 52],
            "Rarest Achievement", font_label,
        )
        achievement = f"{rarest['achievement']} ({rarest['game']})"
        for j, line in enumerate(
            _wrap_text(draw, achievement, font_ach, 860, 2)
        ):
            draw.text(
                (80, ach_y + 80 + j * 40), line, font=font_ach,
                fill=INK, stroke_width=1, stroke_fill="#111111",
            )
        draw.text(
            (80, ach_y + 170),
            f"Only {rarest['percent']}% unlocked it",
            font=font_small, fill=YELLOW,
            stroke_width=1, stroke_fill="#111111",
        )

    # Footer
    draw.text(
        (42, 1316), "STEAM-WRAPPED", font=font_small,
        fill=INK, stroke_width=1, stroke_fill="#111111",
    )

    img = img.filter(ImageFilter.UnsharpMask(radius=1, percent=110, threshold=3))
    img.save(output_path, quality=95)
    return output_path


# ─── Public API ──────────────────────────────────────────────────────


def generate_card(profile, stats, output_dir="output"):
    """Generate all three Steam Wrapped cards. Returns list of paths."""
    os.makedirs(output_dir, exist_ok=True)
    paths = [
        _generate_overview(
            profile, stats, os.path.join(output_dir, "card_overview.png"),
        ),
        _generate_games(
            stats, os.path.join(output_dir, "card_top_games.png"),
        ),
        _generate_stats(
            stats, os.path.join(output_dir, "card_stats.png"),
        ),
    ]
    return paths


if __name__ == "__main__":
    fake_profile = {"personaname": "Deadshot", "avatarfull": ""}
    fake_stats = {
        "total_hours": 536.4,
        "game_count": 42,
        "backlog": [{}] * 27,
        "badge": "The One-Game Wonder",
        "top_games": [
            {"appid": 730, "name": "Counter-Strike 2", "hours": 308},
            {"appid": 1293830, "name": "Forza Horizon 4", "hours": 52},
            {"appid": 2807960, "name": "Battlefield 6", "hours": 48},
            {"appid": 578080, "name": "PUBG: BATTLEGROUNDS", "hours": 31},
            {"appid": 431960, "name": "Wallpaper Engine", "hours": 28},
        ],
        "rarest_achievement": {
            "achievement": "POST_VIDEO_WALLPAPER",
            "game": "Wallpaper Engine",
            "percent": 2.0,
        },
    }
    paths = generate_card(fake_profile, fake_stats)
    for p in paths:
        print(p)

