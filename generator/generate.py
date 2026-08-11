"""
aiMahdiX animated GitHub profile banner generator.

Produces dark.svg and light.svg (1180x610) with:
  - Dense portrait dot layer (~17,000 dots) via Floyd-Steinberg dithering
  - Traveller swarm layer (~900 dots) morphing between three technical identities
  - SMIL intro animation (~3.2s, 60 interleaved random groups)

Source of truth: this script + photo.jpg + config.py
The generated SVG is NOT the source of truth.
"""
import os
import sys
import math
import random
import html
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

sys.path.insert(0, os.path.dirname(__file__))
import config as C

# ── Deterministic RNGs ────────────────────────────────────────────────────
RNG = random.Random(42)       # general
GROUP_RNG = random.Random(7)  # animation grouping (kept separate for determinism)

# ── Paths ─────────────────────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PHOTO = os.path.join(ROOT, "photo.jpg")
ASSETS = os.path.join(ROOT, "assets")
DATA = os.path.join(ROOT, "generator", "data")
os.makedirs(ASSETS, exist_ok=True)
os.makedirs(DATA, exist_ok=True)


# ═════════════════════════════════════════════════════════════════════════
# 1. PORTRAIT PIPELINE
# ═════════════════════════════════════════════════════════════════════════

def load_and_crop():
    """Load photo, crop head-and-shoulders, return RGB array."""
    img = Image.open(PHOTO).convert("RGB")
    w, h = img.size
    # Head-and-shoulders crop: central region, face upper-middle.
    crop_box = (int(w * 0.10), int(h * 0.06), int(w * 0.90), int(h * 0.92))
    img = img.crop(crop_box)
    return np.array(img)


def segment_background(rgb):
    """
    Remove photographic background for dark mode.
    Uses colour-distance threshold + binary closing + hole filling +
    largest-component selection + hard clearing of diffusion bleed.
    Returns boolean mask (True = subject).
    """
    hsv = np.array(Image.fromarray(rgb).convert("HSV"), dtype=np.float32)
    s, v = hsv[..., 1], hsv[..., 2]

    # Background tends to be low saturation and mid-to-high value.
    bg_score = (255.0 - s) * (v / 255.0)

    # Threshold: background where score is high.
    thresh = np.percentile(bg_score, 55)
    bg_mask = bg_score > thresh

    # Binary closing to fill small gaps.
    bg_mask = ndimage.binary_closing(bg_mask, structure=np.ones((7, 7)))

    # Hole filling.
    bg_mask = ndimage.binary_fill_holes(bg_mask)

    # Largest background component (the surrounding area).
    labels, n = ndimage.label(bg_mask)
    if n > 0:
        sizes = ndimage.sum(bg_mask, labels, range(1, n + 1))
        largest = np.argmax(sizes) + 1
        bg_mask = labels == largest

    # Subject = not background.
    subject = ~bg_mask

    # Largest subject component (remove stray blobs).
    labels, n = ndimage.label(subject)
    if n > 0:
        sizes = ndimage.sum(subject, labels, range(1, n + 1))
        largest = np.argmax(sizes) + 1
        subject = labels == largest

    # Hard clearing of diffusion bleed near the mask boundary:
    # erode the subject mask slightly to remove soft edges.
    subject = ndimage.binary_erosion(subject, structure=np.ones((3, 3)))

    return subject


def monochrome_tonal(rgb, mask=None):
    """Convert to monochrome tonal representation (0-255, 0=black)."""
    gray = np.array(Image.fromarray(rgb).convert("L"), dtype=np.float32)
    if mask is not None:
        gray[~mask] = 0.0  # background -> black (dark mode)
    return gray


def autocontrast_cutoff(gray, cutoff=1):
    """Autocontrast with percentile cutoff (like PIL autocontrast cutoff)."""
    lo = np.percentile(gray, cutoff)
    hi = np.percentile(gray, 100 - cutoff)
    if hi <= lo:
        return gray
    out = (gray - lo) * (255.0 / (hi - lo))
    return np.clip(out, 0, 255)


def autocontrast_cutoff_masked(gray, mask, cutoff=1):
    """Autocontrast using percentiles from masked (subject) pixels only."""
    vals = gray[mask]
    if vals.size == 0:
        return gray
    lo = np.percentile(vals, cutoff)
    hi = np.percentile(vals, 100 - cutoff)
    if hi <= lo:
        return gray
    out = (gray - lo) * (255.0 / (hi - lo))
    return np.clip(out, 0, 255)


def scale_to_dot_target(gray, target):
    """
    Scale grayscale brightness so that Floyd-Steinberg dithering yields
    approximately `target` dots. Dot count ~= sum(gray)/255.
    """
    total = float(gray.sum())
    if total <= 0:
        return gray
    scale = (target * 255.0) / total
    return np.clip(gray * scale, 0, 255)


def unsharp_mask(gray, radius=3, percent=140):
    """Unsharp mask via PIL."""
    img = Image.fromarray(gray.astype(np.uint8))
    img = img.filter(ImageFilter.UnsharpMask(radius=radius, percent=percent))
    return np.array(img, dtype=np.float32)


def contrast_boost(gray, factor=1.3):
    """Contrast multiply around mid-gray."""
    return np.clip((gray - 128.0) * factor + 128.0, 0, 255)


def floyd_steinberg(gray, threshold=128.0, serpentine=True):
    """
    1-bit Floyd-Steinberg dithering with serpentine processing.
    Returns boolean array (True = dot). Pixel >= threshold becomes a dot.
    """
    h, w = gray.shape
    img = gray.copy()
    out = np.zeros((h, w), dtype=bool)

    for y in range(h):
        if serpentine and y % 2 == 1:
            x_range = range(w - 1, -1, -1)
        else:
            x_range = range(w)

        for x in x_range:
            old = img[y, x]
            new = 255.0 if old >= threshold else 0.0
            out[y, x] = new > 0
            err = old - new

            if serpentine and y % 2 == 1:
                # right-to-left
                if x > 0:
                    img[y, x - 1] += err * 7 / 16
                if y + 1 < h:
                    if x > 0:
                        img[y + 1, x - 1] += err * 3 / 16
                    img[y + 1, x] += err * 5 / 16
                    if x + 1 < w:
                        img[y + 1, x + 1] += err * 1 / 16
            else:
                # left-to-right
                if x + 1 < w:
                    img[y, x + 1] += err * 7 / 16
                if y + 1 < h:
                    if x > 0:
                        img[y + 1, x - 1] += err * 3 / 16
                    img[y + 1, x] += err * 5 / 16
                    if x + 1 < w:
                        img[y + 1, x + 1] += err * 1 / 16

    return out


def build_portrait_dots(mode):
    """
    Build the dense portrait dot layer (~17,000 dots).
    Returns list of (x, y) in portrait-local coordinates (0..300, 0..340).
    """
    rgb = load_and_crop()

    if mode == "dark":
        mask = segment_background(rgb)
        gray = monochrome_tonal(rgb, None)
        # Autocontrast using subject pixels only so subject tones span full range.
        gray = autocontrast_cutoff_masked(gray, mask, cutoff=1)
        gray = unsharp_mask(gray, radius=3, percent=140)
        gray = contrast_boost(gray, factor=1.3)
        # Mask background after processing; erode to clear diffusion bleed.
        eroded = ndimage.binary_erosion(mask, structure=np.ones((5, 5)))
        gray[~eroded] = 0.0
    else:  # light
        # Keep background; dark tonal areas become the dot structure.
        gray = monochrome_tonal(rgb, None)
        gray = 255.0 - gray  # dark -> high value -> dots
        gray = autocontrast_cutoff(gray, cutoff=1)
        gray = unsharp_mask(gray, radius=3, percent=140)
        gray = contrast_boost(gray, factor=1.3)

    # Resize to 300x340 (portrait target).
    img = Image.fromarray(gray.astype(np.uint8)).resize(
        (C.PORTRAIT_W, C.PORTRAIT_H), Image.LANCZOS
    )
    gray = np.array(img, dtype=np.float32)

    # Scale brightness to hit the target dot count.
    gray = scale_to_dot_target(gray, C.PORTRAIT_DOTS_TARGET)

    # Dither.
    dots = floyd_steinberg(gray, threshold=128.0, serpentine=True)

    ys, xs = np.nonzero(dots)
    coords = list(zip(xs.tolist(), ys.tolist()))

    # Save data (source of truth).
    np.save(os.path.join(DATA, f"portrait_{mode}.npy"), np.array(coords, dtype=np.int16))
    return coords


# ═════════════════════════════════════════════════════════════════════════
# 2. TRAVELLER SWARM / LOGO MORPH
# ═════════════════════════════════════════════════════════════════════════

def identity_neural():
    """Neural network motif: layered nodes with connecting edges (~900 pts)."""
    pts = []
    layers = [4, 6, 6, 4]
    spacing_x = 55
    spacing_y = 48
    start_x = 90
    start_y = 170
    nodes = []
    for li, count in enumerate(layers):
        col = []
        x = start_x + li * spacing_x
        for ni in range(count):
            y = start_y + (ni - (count - 1) / 2) * spacing_y
            col.append((x, y))
            pts.append((x, y))  # node
        nodes.append(col)
    # Edges between consecutive layers.
    for li in range(len(layers) - 1):
        for a in nodes[li]:
            for b in nodes[li + 1]:
                for t in np.linspace(0.12, 0.88, 10):
                    pts.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return pts


def identity_code():
    """Code / developer motif: angle brackets + slash (~900 pts)."""
    pts = []
    n = 180
    # Left angle bracket <
    for t in np.linspace(0, 1, n):
        pts.append((100 + t * 60, 170 - t * 60))
    for t in np.linspace(0, 1, n):
        pts.append((100 + t * 60, 170 + t * 60))
    # Right angle bracket >
    for t in np.linspace(0, 1, n):
        pts.append((220 + t * 60, 170 - t * 60))
    for t in np.linspace(0, 1, n):
        pts.append((220 + t * 60, 170 + t * 60))
    # Slash /
    for t in np.linspace(0, 1, n):
        pts.append((160 + t * 60, 110 + t * 120))
    return pts


def identity_vision():
    """Computer vision motif: eye / aperture (~900 pts)."""
    pts = []
    cx, cy = 180, 170
    rx, ry = 85, 55
    # Outer almond outline.
    for t in np.linspace(0, 2 * math.pi, 300, endpoint=False):
        pts.append((cx + rx * math.cos(t), cy + ry * math.sin(t)))
    # Iris circle.
    r = 30
    for t in np.linspace(0, 2 * math.pi, 200, endpoint=False):
        pts.append((cx + r * math.cos(t), cy + r * math.sin(t)))
    # Pupil.
    rp = 12
    for t in np.linspace(0, 2 * math.pi, 100, endpoint=False):
        pts.append((cx + rp * math.cos(t), cy + rp * math.sin(t)))
    # Radial lines from iris to outer.
    for i in range(12):
        ang = i * math.pi / 6
        for t in np.linspace(0.35, 1.0, 25):
            pts.append((cx + rx * t * math.cos(ang), cy + ry * t * math.sin(ang)))
    return pts


def normalize_points(pts, target):
    """Resample a point list to exactly `target` points."""
    if len(pts) > target:
        idx = np.linspace(0, len(pts) - 1, target).astype(int)
        return [pts[i] for i in idx]
    elif len(pts) < target:
        out = list(pts)
        while len(out) < target:
            p = RNG.choice(pts)
            out.append((p[0] + RNG.uniform(-1, 1), p[1] + RNG.uniform(-1, 1)))
        return out
    return pts


def optimal_transport(a, b):
    """
    Match points in set a to points in set b using optimal transport
    (minimum-cost assignment / Hungarian algorithm).
    Returns array where result[i] = index in b matched to a[i].
    """
    from scipy.optimize import linear_sum_assignment
    a_arr = np.array(a, dtype=np.float64)
    b_arr = np.array(b, dtype=np.float64)
    cost = ((a_arr[:, None, :] - b_arr[None, :, :]) ** 2).sum(axis=2)
    _, col = linear_sum_assignment(cost)
    return col


def cluster_travellers(travellers, group_size=5):
    """
    Group travellers into spatially-coherent clusters (by A position)
    using greedy nearest-neighbour clustering. Avoids grid alignment.
    """
    from scipy.spatial import cKDTree
    pts = np.array([t["A"] for t in travellers], dtype=np.float64)
    tree = cKDTree(pts)
    assigned = np.zeros(len(travellers), dtype=bool)
    groups = []
    order = list(range(len(travellers)))
    RNG.shuffle(order)
    for i in order:
        if assigned[i]:
            continue
        dist, idx = tree.query(pts[i], k=group_size)
        idx = np.atleast_1d(idx)
        chosen = [j for j in idx if not assigned[j]][:group_size]
        if not chosen:
            chosen = [i]
        groups.append([travellers[j] for j in chosen])
        for j in chosen:
            assigned[j] = True
    return groups


def build_travellers():
    """
    Build the traveller swarm: ~900 dots morphing between three identities.
    Each traveller has 3 keyframe positions (A, B, C) matched by optimal
    transport. Returns a list of clusters (each cluster = list of travellers).
    """
    identities = [identity_neural(), identity_code(), identity_vision()]
    normalized = [normalize_points(p, C.TRAVELLER_COUNT) for p in identities]

    # Optimal transport matching between consecutive identities.
    idx_ab = optimal_transport(normalized[0], normalized[1])
    idx_bc = optimal_transport(normalized[1], normalized[2])

    # Build 900 travellers, each with A, B, C keyframes + per-dot noise.
    travellers = []
    for i in range(C.TRAVELLER_COUNT):
        a = normalized[0][i]
        b = normalized[1][idx_ab[i]]
        c = normalized[2][idx_bc[idx_ab[i]]]
        nx = RNG.gauss(0, C.TRAVELLER_NOISE_SIGMA)
        ny = RNG.gauss(0, C.TRAVELLER_NOISE_SIGMA)
        travellers.append({
            "A": (a[0] + nx, a[1] + ny),
            "B": (b[0] + nx, b[1] + ny),
            "C": (c[0] + nx, c[1] + ny),
        })

    # Cluster into groups of ~5 for compact rendering.
    groups = cluster_travellers(travellers, group_size=5)

    # Save data (source of truth).
    flat = np.array(
        [[t["A"][0], t["A"][1], t["B"][0], t["B"][1], t["C"][0], t["C"][1]]
         for t in travellers],
        dtype=np.float32,
    )
    np.save(os.path.join(DATA, "travellers.npy"), flat)

    return groups


# ═════════════════════════════════════════════════════════════════════════
# 3. SVG RENDERING
# ═════════════════════════════════════════════════════════════════════════

def svg_escape(s):
    return html.escape(s, quote=False)


def dots_to_path(coords, scale=1.0, ox=0.0, oy=0.0):
    """Render dots as SVG <path> runs. shape-rendering=crispEdges on element."""
    parts = []
    for (x, y) in coords:
        sx = ox + x * scale
        sy = oy + y * scale
        parts.append(f"M{sx:.1f} {sy:.1f}h1v1h-1z")
    return " ".join(parts)


def split_into_groups(coords, n_groups):
    """Split dots into n_groups interleaved groups distributed across portrait."""
    groups = [[] for _ in range(n_groups)]
    for i, c in enumerate(coords):
        groups[i % n_groups].append(c)
    GROUP_RNG.shuffle(groups)
    return groups


def render_intro_animation(coords, scale, ox, oy, color):
    """
    Portrait intro animation: ~3.2s, 60 interleaved random groups.
    Base layer (stable final portrait) appears at the end of the intro;
    animated layer shimmers in staggered across the whole portrait.
    """
    groups = split_into_groups(coords, C.INTRO_GROUPS)

    # Base layer: stable final portrait, appears at end of intro.
    base_d = dots_to_path(coords, scale, ox, oy)
    base = (
        f'<path d="{base_d}" fill="{color}" shape-rendering="crispEdges" stroke="none" opacity="0">'
        f'<animate attributeName="opacity" values="0;1" begin="{C.INTRO_DURATION}s" '
        f'dur="0.01s" fill="freeze" />'
        f'</path>'
    )

    # Animated layer: 60 groups shimmer in staggered.
    anim_parts = []
    for gi, group in enumerate(groups):
        if not group:
            continue
        d = dots_to_path(group, scale, ox, oy)
        begin = gi * (C.INTRO_DURATION / C.INTRO_GROUPS)
        anim_parts.append(
            f'<path d="{d}" fill="{color}" shape-rendering="crispEdges" stroke="none" opacity="0">'
            f'<animate attributeName="opacity" values="0;1" begin="{begin:.3f}s" '
            f'dur="0.35s" fill="freeze" />'
            f'</path>'
        )

    return base + "".join(anim_parts)


def render_traveller_layer(groups, color, scale, ox, oy):
    """
    Render the traveller swarm as animated clusters.
    Each cluster translates through A -> B -> C -> A via animateTransform.
    """
    elems = []
    dur = 9.0
    for g in groups:
        meanA = np.mean([t["A"] for t in g], axis=0)
        meanB = np.mean([t["B"] for t in g], axis=0)
        meanC = np.mean([t["C"] for t in g], axis=0)
        # Circles at absolute A positions; group translates by delta from A.
        inner = "".join(
            f'<circle cx="{ox + t["A"][0] * scale:.1f}" cy="{oy + t["A"][1] * scale:.1f}" '
            f'r="1.6" fill="{color}" />'
            for t in g
        )
        vals = [
            "0,0",
            f"{(meanB[0] - meanA[0]) * scale:.1f},{(meanB[1] - meanA[1]) * scale:.1f}",
            f"{(meanC[0] - meanA[0]) * scale:.1f},{(meanC[1] - meanA[1]) * scale:.1f}",
            "0,0",
        ]
        elems.append(
            f'<g>'
            f'<animateTransform attributeName="transform" type="translate" '
            f'values="{";".join(vals)}" keyTimes="0;0.33;0.66;1" '
            f'dur="{dur}s" repeatCount="indefinite" />'
            f'{inner}'
            f'</g>'
        )
    return "".join(elems)


def render_terminal(mode):
    """Render the terminal window chrome."""
    dark = mode == "dark"
    bg = C.BG_DARK if dark else C.BG_LIGHT
    border = C.UI_CYAN_DEEP if dark else C.UI_CYAN
    title_color = C.TEXT_DIM_DARK if dark else C.TEXT_DIM_LIGHT

    parts = [
        f'<rect x="{C.TERM_X}" y="{C.TERM_Y}" width="{C.TERM_W}" height="{C.TERM_H}" '
        f'rx="{C.TERM_RADIUS}" fill="{bg}" stroke="{border}" stroke-width="1.5" />',
        f'<rect x="{C.TERM_X}" y="{C.TERM_Y}" width="{C.TERM_W}" height="34" '
        f'rx="{C.TERM_RADIUS}" fill="{border}" opacity="0.12" />',
        f'<circle cx="{C.TERM_X + 24}" cy="{C.TERM_Y + 17}" r="5" fill="#FF5F56" />',
        f'<circle cx="{C.TERM_X + 44}" cy="{C.TERM_Y + 17}" r="5" fill="#FFBD2E" />',
        f'<circle cx="{C.TERM_X + 64}" cy="{C.TERM_Y + 17}" r="5" fill="#27C93F" />',
        f'<text x="{C.TERM_X + C.TERM_W / 2}" y="{C.TERM_Y + 22}" '
        f'text-anchor="middle" font-family="monospace" font-size="13" '
        f'fill="{title_color}">{svg_escape(C.TERM_TITLE)}</text>',
        # LIVE indicator in title bar (right side)
        f'<circle cx="{C.TERM_X + C.TERM_W - 70}" cy="{C.TERM_Y + 17}" r="4" fill="{C.ACCENT_GREEN}">'
        f'<animate attributeName="opacity" values="1;0.2;1" dur="1.5s" repeatCount="indefinite" />'
        f'</circle>',
        f'<text x="{C.TERM_X + C.TERM_W - 58}" y="{C.TERM_Y + 21}" '
        f'font-family="monospace" font-size="12" fill="{C.ACCENT_GREEN}" '
        f'font-weight="bold">LIVE</text>',
    ]
    return "".join(parts)


def render_info_panel(mode):
    """Render the SYSTEM.INFO panel with dotted leaders."""
    dark = mode == "dark"
    text = C.TEXT_DARK if dark else C.TEXT_LIGHT
    dim = C.TEXT_DIM_DARK if dark else C.TEXT_DIM_LIGHT
    accent = C.ACCENT_GREEN

    parts = []
    parts.append(
        f'<text x="{C.RIGHT_X}" y="{C.RIGHT_Y + 20}" font-family="monospace" '
        f'font-size="14" fill="{accent}" font-weight="bold">SYSTEM.INFO</text>'
    )

    row_h = 26
    start_y = C.RIGHT_Y + 45
    for i, (label, value) in enumerate(C.INFO_ROWS):
        y = start_y + i * row_h
        parts.append(
            f'<text x="{C.RIGHT_X}" y="{y}" font-family="monospace" font-size="12.5" '
            f'fill="{dim}">{svg_escape(label)}</text>'
        )
        leader_x = C.RIGHT_X + 140
        leader_end = C.RIGHT_X + 300
        parts.append(
            f'<line x1="{leader_x}" y1="{y - 4}" x2="{leader_end}" y2="{y - 4}" '
            f'stroke="{dim}" stroke-width="1" stroke-dasharray="2,4" opacity="0.5" />'
        )
        parts.append(
            f'<text x="{leader_end + 12}" y="{y}" font-family="monospace" font-size="12.5" '
            f'fill="{text}" font-weight="bold">{svg_escape(value)}</text>'
        )

    return "".join(parts)


def render_morph_panel(mode, traveller_groups):
    """Render the IDENTITY.MORPH panel (traveller swarm) in the right panel."""
    dark = mode == "dark"
    accent = C.ACCENT_GREEN
    traveller_color = C.UI_CYAN if dark else C.UI_CYAN_DEEP

    # Morph viewport below the info rows.
    viewport_y = C.RIGHT_Y + 45 + len(C.INFO_ROWS) * 26 + 20  # ~399
    header_y = viewport_y + 14
    morph_y = viewport_y + 30
    morph_h = C.RIGHT_Y + C.RIGHT_H - morph_y - 10  # remaining space

    parts = []
    parts.append(
        f'<text x="{C.RIGHT_X}" y="{header_y}" font-family="monospace" '
        f'font-size="12" fill="{accent}" font-weight="bold">'
        f'IDENTITY.MORPH // NEURAL -> CODE -> VISION</text>'
    )

    # Compute form bounds to scale the swarm into the viewport.
    all_a = np.array([t["A"] for g in traveller_groups for t in g])
    minx, miny = all_a.min(axis=0)
    maxx, maxy = all_a.max(axis=0)
    form_w = maxx - minx
    form_h = maxy - miny
    avail_w = C.RIGHT_W - 40
    avail_h = morph_h
    scale = min(avail_w / form_w, avail_h / form_h)
    # Center the swarm in the viewport.
    ox = C.RIGHT_X + (C.RIGHT_W - form_w * scale) / 2 - minx * scale
    oy = morph_y + (avail_h - form_h * scale) / 2 - miny * scale

    parts.append(render_traveller_layer(traveller_groups, traveller_color, scale, ox, oy))
    return "".join(parts)


def render_visual_map(mode, portrait_coords):
    """Render the VISUAL.MAP panel: portrait."""
    dark = mode == "dark"
    accent = C.ACCENT_GREEN
    portrait_color = C.PORTRAIT_DARK if dark else "#7C3AED"

    parts = []
    parts.append(
        f'<text x="{C.LEFT_X}" y="{C.LEFT_Y + 20}" font-family="monospace" '
        f'font-size="14" fill="{accent}" font-weight="bold">VISUAL.MAP</text>'
    )

    parts.append(
        f'<rect x="{C.PORTRAIT_X - 10}" y="{C.PORTRAIT_Y - 10}" '
        f'width="{C.PORTRAIT_W + 20}" height="{C.PORTRAIT_H + 20}" '
        f'fill="{C.UI_CYAN_DEEP}" opacity="0.06" rx="8" />'
    )

    # Portrait layer (dense dots) with intro animation.
    scale = 1.0
    ox = C.PORTRAIT_X
    oy = C.PORTRAIT_Y
    parts.append(render_intro_animation(portrait_coords, scale, ox, oy, portrait_color))

    # aiMahdiX handle below the portrait.
    parts.append(
        f'<text x="{C.LEFT_X}" y="{C.PORTRAIT_Y + C.PORTRAIT_H + 24}" '
        f'font-family="monospace" font-size="16" fill="{portrait_color}" '
        f'font-weight="bold">aiMahdiX</text>'
    )

    return "".join(parts)


def generate_svg(mode, portrait_coords, traveller_groups):
    """Assemble the full SVG document."""
    dark = mode == "dark"
    bg = C.BG_DARK if dark else C.BG_LIGHT

    terminal = render_terminal(mode)
    info = render_info_panel(mode)
    morph = render_morph_panel(mode, traveller_groups)
    visual = render_visual_map(mode, portrait_coords)

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{C.CANVAS_W}" height="{C.CANVAS_H}" viewBox="0 0 {C.CANVAS_W} {C.CANVAS_H}">
  <rect width="{C.CANVAS_W}" height="{C.CANVAS_H}" fill="{bg}" />
  {terminal}
  {visual}
  {info}
  {morph}
</svg>
'''
    return svg


# ═════════════════════════════════════════════════════════════════════════
# 4. VALIDATION METRICS
# ═════════════════════════════════════════════════════════════════════════

def grid_evenness(points, nx, ny, xmax, ymax):
    """std/mean of point counts across an nx*ny grid."""
    if len(points) == 0:
        return 1.0
    arr = np.array(points, dtype=np.float64)
    gx = np.clip((arr[:, 0] / (xmax / nx)).astype(int), 0, nx - 1)
    gy = np.clip((arr[:, 1] / (ymax / ny)).astype(int), 0, ny - 1)
    counts = np.zeros((ny, nx))
    for i in range(len(arr)):
        counts[gy[i], gx[i]] += 1
    mean = counts.mean()
    std = counts.std()
    return std / mean if mean > 0 else 1.0


def validate_portrait(coords, mode):
    """Numerical validation of portrait dot distribution."""
    n = len(coords)
    print(f"  [{mode}] portrait dots: {n}")

    density = n / (C.PORTRAIT_W * C.PORTRAIT_H) * 10000
    print(f"  [{mode}] density (dots/10000px): {density:.1f}")

    ink = n / (C.PORTRAIT_W * C.PORTRAIT_H)
    print(f"  [{mode}] ink coverage: {ink:.3%}")


def validate_animation(coords):
    """
    Validate the intro animation evenness: at the midpoint of the intro,
    half the groups have appeared. The appeared dots must be a uniform
    random subset of the final portrait (not a spatial wipe/reveal).

    We measure RELATIVE evenness: for each grid cell, the ratio of
    appeared/final dots should be constant across cells. This isolates
    the animation's spatial evenness from the portrait's natural density
    variation (e.g. face vs body).
    """
    groups = split_into_groups(coords, C.INTRO_GROUPS)
    half = C.INTRO_GROUPS // 2
    appeared = [c for g in groups[:half] for c in g]

    final_arr = np.array(coords, dtype=np.float64)
    app_arr = np.array(appeared, dtype=np.float64)
    if len(app_arr) == 0 or len(final_arr) == 0:
        print("  animation evenness (t=mid): 1.000  (no dots)")
        return

    xmax = max(final_arr[:, 0].max() - final_arr[:, 0].min(), 1.0)
    ymax = max(final_arr[:, 1].max() - final_arr[:, 1].min(), 1.0)
    nx = ny = 8

    def cell_counts(arr):
        gx = np.clip((arr[:, 0] / (xmax / nx)).astype(int), 0, nx - 1)
        gy = np.clip((arr[:, 1] / (ymax / ny)).astype(int), 0, ny - 1)
        counts = np.zeros((ny, nx))
        for i in range(len(arr)):
            counts[gy[i], gx[i]] += 1
        return counts

    final_counts = cell_counts(final_arr)
    app_counts = cell_counts(app_arr)

    # Relative evenness: ratio of appeared/final per cell, weighted by cells
    # that actually contain final dots.
    mask = final_counts > 0
    ratios = np.where(mask, app_counts / np.maximum(final_counts, 1), np.nan)
    valid = ratios[~np.isnan(ratios)]
    if len(valid) == 0:
        print("  animation evenness (t=mid): 1.000  (no populated cells)")
        return
    mean = valid.mean()
    std = valid.std()
    evenness = std / mean if mean > 0 else 1.0
    print(f"  animation evenness (t=mid): {evenness:.3f}  (0.05=good, 0.7=patchy)")


def validate_travellers(groups):
    """Validate traveller distribution and organic movement."""
    travellers = [t for g in groups for t in g]
    n = len(travellers)
    print(f"  travellers: {n}")

    # Distribution evenness of A positions.
    a_pts = [t["A"] for t in travellers]
    evenness = grid_evenness(a_pts, 6, 6, 360, 360)
    print(f"  traveller grid evenness: {evenness:.3f}")

    # Organic movement: straight-boundary metric on A->B movement.
    arr = np.array([[t["A"][0], t["A"][1], t["B"][0], t["B"][1]] for t in travellers])
    dx = arr[:, 2] - arr[:, 0]
    dy = arr[:, 3] - arr[:, 1]
    angles = np.abs(np.arctan2(dy, dx))
    grid_like = (
        (angles < 0.05) | (np.abs(angles - np.pi / 2) < 0.05) |
        (np.abs(angles - np.pi) < 0.05) | (np.abs(angles - 3 * np.pi / 2) < 0.05)
    )
    grid_frac = grid_like.mean()
    print(f"  grid-like movement fraction: {grid_frac:.3f}  (0.01=organic, 0.17=grid-like)")


# ═════════════════════════════════════════════════════════════════════════
# 5. MAIN
# ═════════════════════════════════════════════════════════════════════════

def main():
    print("Building portrait dots (dark)...")
    dark_coords = build_portrait_dots("dark")
    print("Building portrait dots (light)...")
    light_coords = build_portrait_dots("light")
    print("Building traveller swarm...")
    traveller_groups = build_travellers()

    print("\nValidation:")
    validate_portrait(dark_coords, "dark")
    validate_animation(dark_coords)
    validate_portrait(light_coords, "light")
    validate_animation(light_coords)
    validate_travellers(traveller_groups)

    print("\nGenerating SVGs...")
    dark_svg = generate_svg("dark", dark_coords, traveller_groups)
    light_svg = generate_svg("light", light_coords, traveller_groups)

    dark_path = os.path.join(ASSETS, "banner-dark.svg")
    light_path = os.path.join(ASSETS, "banner-light.svg")

    with open(dark_path, "w", encoding="utf-8") as f:
        f.write(dark_svg)
    with open(light_path, "w", encoding="utf-8") as f:
        f.write(light_svg)

    dark_size = os.path.getsize(dark_path) / 1024
    light_size = os.path.getsize(light_path) / 1024
    print(f"\nWrote {dark_path} ({dark_size:.0f} KB)")
    print(f"Wrote {light_path} ({light_size:.0f} KB)")


if __name__ == "__main__":
    main()