"""
Share card generator — creates 1200x630 PNG result cards for social media.
"""
import os
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

FONTS_DIR = os.path.join(os.path.dirname(__file__), 'fonts')
CARD_W, CARD_H = 1200, 630


def _font(bold=False, size=24):
    name = 'Inter-Bold.ttf' if bold else 'Inter-Regular.ttf'
    return ImageFont.truetype(os.path.join(FONTS_DIR, name), size)


def generate_result_card(election_name, geo_name, party_results,
                         pct_reporting, status='ongoing'):
    """
    Generate a shareable PNG result card.

    Args:
        election_name: e.g. "FCT Area Council Election 2026"
        geo_name: e.g. "National", "Federal Capital Territory", "Abaji"
        party_results: list of dicts with abbreviation, color, total_votes
        pct_reporting: int/float percentage
        status: 'ongoing' | 'completed'

    Returns:
        BytesIO containing the PNG image data.
    """
    img = Image.new('RGB', (CARD_W, CARD_H), '#0a0e1a')
    draw = ImageDraw.Draw(img)

    # Dark gradient background
    for y in range(CARD_H):
        r = int(10 + (y / CARD_H) * 8)
        g = int(14 + (y / CARD_H) * 20)
        b = int(26 + (y / CARD_H) * 10)
        draw.line([(0, y), (CARD_W, y)], fill=(r, g, b))

    # Green accent bar at top (6px)
    draw.rectangle([0, 0, CARD_W, 6], fill='#009401')

    # Nigerian flag element (top-left area)
    flag_x, flag_y = 48, 36
    flag_w, flag_h = 8, 28
    draw.rectangle([flag_x, flag_y, flag_x + flag_w, flag_y + flag_h], fill='#009401')
    draw.rectangle([flag_x + flag_w + 2, flag_y, flag_x + 2 * flag_w + 2, flag_y + flag_h], fill='#ffffff')
    draw.rectangle([flag_x + 2 * (flag_w + 1), flag_y, flag_x + 3 * flag_w + 2, flag_y + flag_h], fill='#009401')

    # "Nigeria Elections" branding next to flag
    brand_font = _font(bold=True, size=18)
    draw.text((flag_x + 3 * flag_w + 14, flag_y + 4), 'Nigeria Elections',
              fill=(200, 200, 210), font=brand_font)

    # Status badge
    status_text = 'LIVE' if status == 'ongoing' else 'COMPLETED'
    status_color = (0, 230, 118) if status == 'ongoing' else (0, 148, 1)
    sf = _font(bold=True, size=14)
    sw = draw.textlength(status_text, font=sf)
    sx = CARD_W - 48 - int(sw) - 20
    # Dim version of status color for background
    bg_color = (status_color[0] // 6, status_color[1] // 6, status_color[2] // 6)
    draw.rounded_rectangle([sx, flag_y, sx + int(sw) + 20, flag_y + 28],
                           radius=14, fill=bg_color)
    draw.text((sx + 10, flag_y + 5), status_text, fill=status_color, font=sf)

    # Election name (large)
    title_font = _font(bold=True, size=36)
    # Truncate if too long
    title = election_name
    if draw.textlength(title, font=title_font) > CARD_W - 96:
        while draw.textlength(title + '...', font=title_font) > CARD_W - 96 and len(title) > 10:
            title = title[:-1]
        title += '...'
    draw.text((48, 80), title, fill='white', font=title_font)

    # Geo name (secondary)
    geo_font = _font(bold=False, size=22)
    draw.text((48, 126), geo_name, fill=(142, 149, 169), font=geo_font)

    # Reporting percentage bar
    bar_y = 168
    bar_w = CARD_W - 96
    bar_h = 8
    draw.rounded_rectangle([48, bar_y, 48 + bar_w, bar_y + bar_h],
                           radius=4, fill=(34, 40, 64))
    fill_w = int(bar_w * min(pct_reporting, 100) / 100)
    if fill_w > 0:
        draw.rounded_rectangle([48, bar_y, 48 + fill_w, bar_y + bar_h],
                               radius=4, fill=(0, 200, 83))
    pct_font = _font(bold=True, size=14)
    pct_text = f'{pct_reporting}%'
    pct_tw = draw.textlength(pct_text, font=pct_font)
    draw.text((48 + bar_w - int(pct_tw), bar_y - 20), pct_text,
              fill=(0, 200, 83), font=pct_font)

    # Top 5 party vote bars
    top = party_results[:5]
    total_votes = sum(p['total_votes'] for p in party_results) if party_results else 0
    max_votes = top[0]['total_votes'] if top else 1

    party_start_y = 200
    row_h = 72

    for i, p in enumerate(top):
        y = party_start_y + i * row_h
        abbr = p['abbreviation']
        votes = p['total_votes']
        color = p['color'] or '#666666'
        pct = round(votes / total_votes * 100, 1) if total_votes > 0 else 0
        bar_pct = votes / max_votes if max_votes > 0 else 0

        # Parse color
        try:
            if color.startswith('#'):
                r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
            else:
                r, g, b = 102, 102, 102
        except (ValueError, IndexError):
            r, g, b = 102, 102, 102

        # Party abbreviation
        abbr_font = _font(bold=True, size=20)
        draw.text((48, y + 4), abbr, fill=(r, g, b), font=abbr_font)

        # Vote bar
        bar_x = 140
        bar_max_w = CARD_W - 96 - bar_x + 48 - 140
        fill_w = max(int(bar_max_w * bar_pct), 4)

        draw.rounded_rectangle([bar_x, y + 2, bar_x + bar_max_w, y + 34],
                               radius=6, fill=(34, 40, 64))
        draw.rounded_rectangle([bar_x, y + 2, bar_x + fill_w, y + 34],
                               radius=6, fill=(r, g, b))

        # Votes count inside bar (if wide enough)
        count_font = _font(bold=True, size=14)
        count_text = f'{votes:,}'
        ct_w = draw.textlength(count_text, font=count_font)
        if fill_w > ct_w + 16:
            draw.text((bar_x + fill_w - int(ct_w) - 8, y + 9), count_text,
                      fill='white', font=count_font)

        # Percentage and vote count to the right
        meta_font = _font(bold=False, size=14)
        draw.text((bar_x, y + 40), f'{count_text} votes ({pct}%)',
                  fill=(142, 149, 169), font=meta_font)

    # Total votes count (bottom-left)
    bottom_y = CARD_H - 60
    total_font = _font(bold=True, size=16)
    draw.text((48, bottom_y), f'{total_votes:,} total votes',
              fill=(142, 149, 169), font=total_font)

    # "Designed by Place of Ideation" branding (bottom-right)
    brand_small = _font(bold=False, size=14)
    brand_text = 'Designed by Place of Ideation'
    bt_w = draw.textlength(brand_text, font=brand_small)
    draw.text((CARD_W - 48 - int(bt_w), bottom_y + 2), brand_text,
              fill=(90, 97, 120), font=brand_small)

    # Output
    buf = BytesIO()
    img.save(buf, format='PNG', optimize=True)
    buf.seek(0)
    return buf
