"""Seed the stats SVG assets with known profile data (repos, stars).

Follows the GitHub-native Phase 2 spec:
  - Only metrics that can be reliably obtained are shown.
  - Known: 12 public repos, 37 stars (from the profile task data).
  - Unknown (followers, following, commits): shown as "—" — these will be
    populated with real values by the GitHub Action (scripts/generate_stats.py)
    on its first run using the official GitHub API.

This seeds valid, non-empty SVGs so the README works before the first
Action run. The Action overwrites them with live data.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate_stats as G

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
os.makedirs(ASSETS, exist_ok=True)

# Only reliably-known values from the task. Unknown => omitted ("—").
data = {
    "public_repos": 12,
    "total_stars": 37,
    "followers": "—",
    "following": "—",
    "total_commits": "—",
}

# Languages: we know the 6 pinned projects are Python, but full language
# distribution across 12 repos is not reliably known. Use the pinned set
# (all Python) as a minimal honest seed; Action will compute real counts.
langs = {"Python": 6}

streak = {"current_streak": "—", "longest_streak": "—", "total_days": "—"}

variants = {
    "stats": G.render_stats_card(data, True),
    "stats-light": G.render_stats_card(data, False),
    "top-languages": G.render_languages_card(langs, True),
    "top-languages-light": G.render_languages_card(langs, False),
    "streak": G.render_streak_card(streak, True),
    "streak-light": G.render_streak_card(streak, False),
}

for name, svg in variants.items():
    path = os.path.join(ASSETS, f"{name}.svg")
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"wrote {path} ({os.path.getsize(path)} bytes)")

print("Seed complete.")