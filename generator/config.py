"""
Configuration for the aiMahdiX animated GitHub profile banner.
Source of truth for all visual parameters.
"""

# ── Canvas ────────────────────────────────────────────────────────────────
CANVAS_W = 1180
CANVAS_H = 610

# ── Palette ───────────────────────────────────────────────────────────────
BG_DARK = "#0A101F"
BG_LIGHT = "#F5F7FA"

PORTRAIT_DARK = "#A78BFA"
PORTRAIT_DARK_DEEP = "#7C3AED"
UI_CYAN = "#22D3EE"
UI_CYAN_DEEP = "#0891B2"
ACCENT_GREEN = "#10B981"

TEXT_DARK = "#E2E8F0"
TEXT_DIM_DARK = "#94A3B8"
TEXT_LIGHT = "#1E293B"
TEXT_DIM_LIGHT = "#64748B"

# ── Layout ────────────────────────────────────────────────────────────────
# Terminal window
TERM_X = 40
TERM_Y = 30
TERM_W = 1100
TERM_H = 550
TERM_RADIUS = 16
TERM_TITLE = "profile.sh --live"

# Left panel (VISUAL.MAP) ~38%
LEFT_X = 60
LEFT_Y = 100
LEFT_W = 400
LEFT_H = 440

# Right panel (SYSTEM.INFO) ~62%
RIGHT_X = 480
RIGHT_Y = 100
RIGHT_W = 640
RIGHT_H = 440

# ── Portrait ──────────────────────────────────────────────────────────────
PORTRAIT_W = 300
PORTRAIT_H = 340
PORTRAIT_X = LEFT_X + (LEFT_W - PORTRAIT_W) // 2
PORTRAIT_Y = LEFT_Y + 40

# Portrait dot density
PORTRAIT_DOTS_TARGET = 17000

# ── Traveller swarm ───────────────────────────────────────────────────────
TRAVELLER_COUNT = 900
TRAVELLER_NOISE_SIGMA = 4.0

# ── Animation ─────────────────────────────────────────────────────────────
INTRO_DURATION = 3.2  # seconds
INTRO_GROUPS = 60     # interleaved random groups

# ── Info rows ─────────────────────────────────────────────────────────────
INFO_ROWS = [
    ("Subject",       "Mehdi Ahmadi"),
    ("Role",          "AI Engineer"),
    ("Focus",         "Computer Vision"),
    ("Core.AI",       "LLMs / AI Systems"),
    ("Core.ML",       "Machine Learning"),
    ("Core.Data",     "Heavy Data Processing"),
    ("Core.Analysis", "Model Behavior"),
    ("Status",        "Building + Learning + Shipping"),
    ("GitHub",        "aiMahdiX"),
]

# ── Social links ──────────────────────────────────────────────────────────
SOCIAL_LINKS = {
    "Telegram": "https://t.me/aiMahdiX",
    "Reddit":   "https://www.reddit.com/u/aiMahdiX",
    "X":        "https://twitter.com/Mtech2500m",
    "GitHub":   "https://github.com/aiMahdiX",
}

# ── Profile description ───────────────────────────────────────────────────
PROFILE_DESC = (
    "Hi, I'm Mehdi 🚀 AI engineer crafting computer-vision systems "
    "and smart tools 🤖 I work on LLM tuning, model behavior analysis, "
    "and heavy data processing 🔍📊"
)