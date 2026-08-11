#!/usr/bin/env python3
"""
aiMahdiX — GitHub-native static stats generator.

Generates SVG cards (stats, top-languages, streak) using only:
  - GitHub REST API (official)
  - GitHub Actions GITHUB_TOKEN
  - Python standard library

No external stats service. No Vercel. No github-readme-stats.

Data sources (GitHub REST API):
  - GET /users/{username}            -> public repos, followers, following
  - GET /users/{username}/repos      -> repo metadata + language
  - GET /users/{username}/events     -> recent activity (for streak estimate)
  - GET /repos/{owner}/{repo}/commits?author={username} -> commit counts

Streak calculation:
  GitHub's REST API does not expose the full contribution calendar
  (that requires the GraphQL contributionsCollection endpoint, which
  needs a token with `read:user` scope — the Actions GITHUB_TOKEN
  cannot access it for arbitrary users). Therefore:
    - current streak  : computed from recent public events (best-effort)
    - longest streak  : omitted (cannot be reliably computed)
    - total contributions: omitted (cannot be reliably computed)
  If a metric cannot be computed reliably, it is omitted rather than faked.
"""
import json
import os
import sys
import urllib.request
import urllib.error
import xml.sax.saxutils as sax
from datetime import datetime, timedelta, timezone

# ── Config ────────────────────────────────────────────────────────────────
USERNAME = "aiMahdiX"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
API = "https://api.github.com"

# Palette
BG_DARK = "#0A101F"
BG_LIGHT = "#F5F7FA"
UI_DARK = "#22D3EE"
UI_LIGHT = "#0891B2"
ACCENT = "#10B981"
PORTRAIT = "#A78BFA"
TEXT_DARK = "#E2E8F0"
TEXT_DIM_DARK = "#94A3B8"
TEXT_LIGHT = "#1E293B"
TEXT_DIM_LIGHT = "#64748B"

CARD_W = 400
CARD_H = 180
PAD = 20
ROW_H = 24


def api_get(path):
    """GET a GitHub API endpoint with auth. Returns parsed JSON."""
    url = API + path
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "aiMahdiX-profile-stats")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"ERROR: GitHub API {path} -> HTTP {e.code}: {e.reason}", file=sys.stderr)
        raise
    except urllib.error.URLError as e:
        print(f"ERROR: GitHub API {path} -> {e.reason}", file=sys.stderr)
        raise


def esc(s):
    return sax.escape(str(s))


def card_header(title, dark):
    """Common card header."""
    bg = BG_DARK if dark else BG_LIGHT
    ui = UI_DARK if dark else UI_LIGHT
    text = TEXT_DARK if dark else TEXT_LIGHT
    dim = TEXT_DIM_DARK if dark else TEXT_DIM_LIGHT
    return bg, ui, text, dim


def render_stats_card(data, dark):
    """SYSTEM.STATS card."""
    bg, ui, text, dim = card_header("SYSTEM.STATS", dark)
    rows = [
        ("Repositories", data["public_repos"]),
        ("Stars", data["total_stars"]),
        ("Followers", data["followers"]),
        ("Following", data["following"]),
        ("Commits", data["total_commits"]),
    ]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{CARD_W}" height="{CARD_H}" viewBox="0 0 {CARD_W} {CARD_H}">',
        f'<rect width="{CARD_W}" height="{CARD_H}" rx="12" fill="{bg}" stroke="{ui}" stroke-width="1.5" />',
        f'<text x="{PAD}" y="34" font-family="monospace" font-size="14" fill="{ACCENT}" font-weight="bold">SYSTEM.STATS</text>',
        f'<line x1="{PAD}" y1="44" x2="{CARD_W - PAD}" y2="44" stroke="{ui}" stroke-width="1" opacity="0.3" />',
    ]
    y = 70
    for label, value in rows:
        parts.append(
            f'<text x="{PAD}" y="{y}" font-family="monospace" font-size="12.5" fill="{dim}">{esc(label)}</text>'
        )
        parts.append(
            f'<text x="{CARD_W - PAD}" y="{y}" text-anchor="end" font-family="monospace" font-size="12.5" fill="{text}" font-weight="bold">{esc(value)}</text>'
        )
        y += ROW_H
    parts.append("</svg>")
    return "".join(parts)


def render_languages_card(langs, dark):
    """TOP.LANGUAGES card with proportional bars."""
    bg, ui, text, dim = card_header("TOP.LANGUAGES", dark)
    total = sum(langs.values())
    if total <= 0:
        langs = [("No data", 0)]
        total = 1
    # Sort by share descending, take top 6
    items = sorted(langs.items(), key=lambda kv: kv[1], reverse=True)[:6]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{CARD_W}" height="{CARD_H}" viewBox="0 0 {CARD_W} {CARD_H}">',
        f'<rect width="{CARD_W}" height="{CARD_H}" rx="12" fill="{bg}" stroke="{ui}" stroke-width="1.5" />',
        f'<text x="{PAD}" y="34" font-family="monospace" font-size="14" fill="{ACCENT}" font-weight="bold">TOP.LANGUAGES</text>',
        f'<line x1="{PAD}" y1="44" x2="{CARD_W - PAD}" y2="44" stroke="{ui}" stroke-width="1" opacity="0.3" />',
    ]
    y = 66
    bar_w = CARD_W - 2 * PAD
    for name, count in items:
        pct = count / total * 100
        parts.append(
            f'<text x="{PAD}" y="{y}" font-family="monospace" font-size="11.5" fill="{text}">{esc(name)}</text>'
        )
        parts.append(
            f'<text x="{CARD_W - PAD}" y="{y}" text-anchor="end" font-family="monospace" font-size="11.5" fill="{dim}">{pct:.1f}%</text>'
        )
        # Bar background
        parts.append(
            f'<rect x="{PAD}" y="{y + 4}" width="{bar_w}" height="6" rx="3" fill="{ui}" opacity="0.15" />'
        )
        # Bar fill
        fill_w = bar_w * pct / 100
        parts.append(
            f'<rect x="{PAD}" y="{y + 4}" width="{fill_w:.1f}" height="6" rx="3" fill="{PORTRAIT}" />'
        )
        y += 26
    parts.append("</svg>")
    return "".join(parts)


def render_streak_card(streak, dark):
    """STREAK card."""
    bg, ui, text, dim = card_header("STREAK", dark)
    rows = [
        ("Current Streak", streak["current_streak"]),
        ("Longest Streak", streak["longest_streak"]),
        ("Total Contribution Days", streak["total_days"]),
    ]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{CARD_W}" height="{CARD_H}" viewBox="0 0 {CARD_W} {CARD_H}">',
        f'<rect width="{CARD_W}" height="{CARD_H}" rx="12" fill="{bg}" stroke="{ui}" stroke-width="1.5" />',
        f'<text x="{PAD}" y="34" font-family="monospace" font-size="14" fill="{ACCENT}" font-weight="bold">STREAK</text>',
        f'<line x1="{PAD}" y1="44" x2="{CARD_W - PAD}" y2="44" stroke="{ui}" stroke-width="1" opacity="0.3" />',
    ]
    y = 70
    for label, value in rows:
        parts.append(
            f'<text x="{PAD}" y="{y}" font-family="monospace" font-size="12.5" fill="{dim}">{esc(label)}</text>'
        )
        parts.append(
            f'<text x="{CARD_W - PAD}" y="{y}" text-anchor="end" font-family="monospace" font-size="12.5" fill="{text}" font-weight="bold">{esc(value)}</text>'
        )
        y += ROW_H
    # Note about data source
    parts.append(
        f'<text x="{PAD}" y="{CARD_H - 14}" font-family="monospace" font-size="9" fill="{dim}" opacity="0.7">'
        f'based on public events via GitHub REST API</text>'
    )
    parts.append("</svg>")
    return "".join(parts)


def compute_streak(events):
    """
    Compute current streak from public events.
    GitHub REST API does not expose the full contribution calendar;
    we approximate using public event dates. Longest streak and total
    contribution days cannot be reliably computed -> omitted (shown as "—").
    """
    dates = set()
    for ev in events:
        created = ev.get("created_at")
        if created:
            try:
                dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                dates.add(dt.date())
            except (ValueError, TypeError):
                continue
    if not dates:
        return {"current_streak": "—", "longest_streak": "—", "total_days": "—"}

    today = datetime.now(timezone.utc).date()
    # Current streak: count consecutive days ending today or yesterday.
    streak = 0
    d = today
    if d not in dates:
        d = today - timedelta(days=1)
    while d in dates:
        streak += 1
        d -= timedelta(days=1)

    return {
        "current_streak": f"{streak}d",
        "longest_streak": "—",
        "total_days": "—",
    }


def main():
    print(f"Fetching GitHub data for @{USERNAME}...")

    # 1. User profile
    user = api_get(f"/users/{USERNAME}")
    public_repos = user.get("public_repos", 0)
    followers = user.get("followers", 0)
    following = user.get("following", 0)

    # 2. Repos (paginated, 100 per page)
    repos = []
    page = 1
    while True:
        batch = api_get(f"/users/{USERNAME}/repos?per_page=100&page={page}")
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1

    total_stars = sum(r.get("stargazers_count", 0) for r in repos)

    # 3. Language stats (repository-weighted: count repos per language)
    lang_counts = {}
    for r in repos:
        lang = r.get("language")
        if lang:
            lang_counts[lang] = lang_counts.get(lang, 0) + 1

    # 4. Commit count (best-effort: count commits authored by user per repo)
    total_commits = 0
    for r in repos[:10]:  # limit to avoid excessive API calls
        name = r.get("name", "")
        try:
            commits = api_get(
                f"/repos/{USERNAME}/{name}/commits?author={USERNAME}&per_page=1"
            )
            if isinstance(commits, list):
                total_commits += len(commits)
        except Exception:
            pass  # skip repos where commit listing fails

    # 5. Events for streak
    events = []
    try:
        events = api_get(f"/users/{USERNAME}/events?per_page=100")
    except Exception:
        pass

    streak = compute_streak(events)

    data = {
        "public_repos": public_repos,
        "total_stars": total_stars,
        "followers": followers,
        "following": following,
        "total_commits": total_commits,
    }

    print(f"  repos={public_repos} stars={total_stars} followers={followers} "
          f"following={following} commits={total_commits}")
    print(f"  languages={lang_counts}")
    print(f"  streak={streak}")

    # 6. Render SVGs (dark + light)
    assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
    os.makedirs(assets_dir, exist_ok=True)

    variants = {
        "stats": render_stats_card(data, dark=True),
        "stats-light": render_stats_card(data, dark=False),
        "top-languages": render_languages_card(lang_counts, dark=True),
        "top-languages-light": render_languages_card(lang_counts, dark=False),
        "streak": render_streak_card(streak, dark=True),
        "streak-light": render_streak_card(streak, dark=False),
    }

    for name, svg in variants.items():
        path = os.path.join(assets_dir, f"{name}.svg")
        with open(path, "w", encoding="utf-8") as f:
            f.write(svg)
        print(f"  wrote {path} ({os.path.getsize(path)} bytes)")

    print("Done.")


if __name__ == "__main__":
    main()