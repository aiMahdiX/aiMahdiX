"""Local test of the stats SVG renderers with mock data (no API calls)."""
import sys
import os
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate_stats as G

data = {"public_repos": 12, "total_stars": 37, "followers": 5, "following": 3, "total_commits": 120}
langs = {"Python": 6, "Jupyter Notebook": 3, "C++": 2, "JavaScript": 1}
streak = {"current_streak": "3d", "longest_streak": "—", "total_days": "—"}

variants = [
    ("stats", G.render_stats_card(data, True)),
    ("stats-light", G.render_stats_card(data, False)),
    ("top-languages", G.render_languages_card(langs, True)),
    ("top-languages-light", G.render_languages_card(langs, False)),
    ("streak", G.render_streak_card(streak, True)),
    ("streak-light", G.render_streak_card(streak, False)),
]

for name, svg in variants:
    ET.fromstring(svg)  # raises if not well-formed XML
    print(f"{name}: OK ({len(svg)} chars)")
print("All renderers valid.")