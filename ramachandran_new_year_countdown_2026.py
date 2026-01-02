#!/usr/bin/env python
# coding: utf-8

# In[11]:


#!/usr/bin/env python3
"""
Ramachandran New Year Countdown → 2026 

- Square 1:1 aspect ratio (1080x1080) for Instagram/FB/WhatsApp
- PDB watermarks from RCSB 

Outputs:
  - rama_2026_social.gif
  - rama_2026_social.mp4 (requires ffmpeg)

Deps:
  pip install numpy matplotlib scipy pillow
System:
  ffmpeg (for mp4)
"""

import os
import shutil
import tempfile
import subprocess
import urllib.request
from dataclasses import dataclass
from typing import Optional, List, Tuple, Dict

import numpy as np

# Headless-friendly backend (safe for scripts)
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from scipy.ndimage import binary_dilation
from PIL import Image

# ---------------------------- OPTIMIZED SETTINGS ----------------------------
OUT_GIF = "rama_2026_social.gif"
OUT_MP4 = "rama_2026_social.mp4"

SEED = 7
rng = np.random.default_rng(SEED)

# SOCIAL MEDIA OPTIMIZATIONS
FIGURE_SIZE = (1080, 1080)  # Square format
DPI = 108                   # 1080x1080 px
FRAMES_FILL = 60
FRAMES_MORPH = 35
FRAME_MS = 50               # GIF frame duration (ms)
FPS = 20.0                  # MP4 framerate
HOLD_SECONDS = 3.0
HOLD_FRAMES = int((HOLD_SECONDS * 1000) / FRAME_MS)

N_MAX = 2400
ADD_PER_FRAME = max(10, N_MAX // FRAMES_FILL)

PHI_MIN, PHI_MAX = -180, 180
PSI_MIN, PSI_MAX = -180, 180

# TEXT (mobile-friendly)
TOP_TITLE_FILL = "Ramachandran Countdown \u2192 2026"
TOP_TITLE_FINAL = "\u03A6/\u03A8 wishes for 2026"
HAPPY_NEW_YEAR_TEXT = "Happy New Year 2026!"
FINAL_MESSAGE = "Peace, Joy & Discovery in 2026!"

# Message placement (square)
MSG_X, MSG_Y = 0.5, 0.06
MSG_FONT = 13
MSG_BOX_ALPHA = 0.65

HNY_X, HNY_Y = 0.5, 0.12
HNY_FONT = 24

# Fireworks
NUM_BURSTS = 30
SPARK_SIZE = 16
TEXT_SYMBOL_PROB = 0.60

# Watermark rendering
WM_ALPHA_LINE = 0.30
WM_ALPHA_DOTS = 0.22
WM_LINEWIDTH = 3.0
WM_DOTSIZE = 12
WM_WHITEN = 0.50
WM_DRAW_DURING_LAST_MORPH_FRAMES = 10

# ---------------------------- BRANDING (Science Lane) ----------------------------
BRAND_ENABLED = True
BRAND_LOGO_PATH = "/home/samith/notebooks1/science_lane_logo.jpg"

# logo inside plot (bottom-right), axes-fraction coords: [x0, y0, width, height]
BRAND_INSET = [0.85, 0.02, 0.12, 0.12]
BRAND_LOGO_ALPHA = 0.92

# Optional white backing for readability (good during fireworks)
BRAND_BACKING = True
BRAND_BACKING_ALPHA = 0.20

# Fallback (if logo missing): bracket-style text at bottom
BRAND_X = 0.50
BRAND_Y = 0.03
BRAND_FONT = 13
BRAND_LEFT_BRACKET_COLOR = "#5DADE2"
BRAND_RIGHT_BRACKET_COLOR = "#52BE80"
BRAND_TEXT_COLOR = "white"

# Fade-in timing:
# Your “2026” appears during the LAST 10 morph frames (k >= FRAMES_MORPH - 10).
# We fade the logo in over the SAME window.
LOGO_FADE_MORPH_FRAMES = 8
LOGO_FADE_START_GLOBAL = FRAMES_FILL + (FRAMES_MORPH - LOGO_FADE_MORPH_FRAMES)  # global frame index

# ---------------------------- Region definitions ----------------------------
regions = {
    "A": {"mu": np.array([-60, -45]), "sigma": np.array([18, 18]), "p": 0.50},
    "B": {"mu": np.array([-120, 120]), "sigma": np.array([22, 22]), "p": 0.35},
    "C": {"mu": np.array([60, 45]), "sigma": np.array([18, 18]), "p": 0.15},
}
region_keys = list(regions.keys())
region_probs = np.array([regions[k]["p"] for k in region_keys], dtype=float)
region_probs /= region_probs.sum()


def sample_region_points(n: int) -> np.ndarray:
    choices = rng.choice(region_keys, size=n, p=region_probs)
    pts = np.zeros((n, 2), dtype=float)
    for i, key in enumerate(choices):
        mu = regions[key]["mu"]
        sig = regions[key]["sigma"]
        pts[i] = mu + rng.normal(scale=sig, size=2)
    pts[:, 0] = np.clip(pts[:, 0], PHI_MIN, PHI_MAX)
    pts[:, 1] = np.clip(pts[:, 1], PSI_MIN, PSI_MAX)
    return pts


# ---------------------------- Matplotlib helpers ----------------------------
def fig_to_rgb_array(fig) -> np.ndarray:
    fig.canvas.draw()
    buf = np.asarray(fig.canvas.buffer_rgba())
    return buf[..., :3].copy()


# ---------------------------- Easing + Logo alpha ----------------------------
def ease_in_out(x: float) -> float:
    x = float(np.clip(x, 0.0, 1.0))
    return 0.5 - 0.5 * np.cos(np.pi * x)


def brand_alpha(global_frame: int) -> float:
    """
    Logo alpha schedule:
    - 0.0 until the last LOGO_FADE_MORPH_FRAMES of the morph
    - fades to 1.0 over LOGO_FADE_MORPH_FRAMES, parallel to '2026' reveal
    """
    if global_frame < LOGO_FADE_START_GLOBAL:
        return 0.0

    # Make sure it reaches 1.0 exactly at start + (frames-1)
    denom = max(1, (LOGO_FADE_MORPH_FRAMES - 1))
    t = (global_frame - LOGO_FADE_START_GLOBAL) / denom
    return ease_in_out(np.clip(t, 0.0, 1.0))


# ---------------------------- Text mask for "2026" ----------------------------
def text_to_mask(text: str, font_size=140, dpi=120) -> np.ndarray:
    fig = plt.figure(figsize=(8, 2), dpi=dpi)
    ax = fig.add_subplot(111)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(
        0.5, 0.5, text,
        fontsize=font_size, fontweight="bold",
        ha="center", va="center",
        family="DejaVu Sans",
    )
    fig.canvas.draw()
    img = np.asarray(fig.canvas.buffer_rgba())[..., :3].copy()
    plt.close(fig)
    gray = img.mean(axis=2)
    mask = gray < 128
    mask = binary_dilation(mask, iterations=2)
    return mask


def mask_to_points(mask: np.ndarray, n_samples=None) -> np.ndarray:
    y_coords, x_coords = np.where(mask)
    if len(y_coords) == 0:
        return np.array([[0.5, 0.5]], dtype=float)

    x_norm = x_coords / (mask.shape[1] - 1)
    y_norm = 1.0 - y_coords / (mask.shape[0] - 1)
    pts = np.column_stack([x_norm, y_norm]).astype(float)

    if n_samples is not None and len(pts) > n_samples:
        idx = rng.choice(len(pts), size=n_samples, replace=False)
        pts = pts[idx]
    return pts


mask = text_to_mask("2026", font_size=140, dpi=120)
mask_pts = mask_to_points(mask)

phi_center, psi_center = 0.0, 0.0
phi_span, psi_span = 240.0, 140.0
target_digits = np.column_stack(
    [
        phi_center + (mask_pts[:, 0] - 0.5) * phi_span,
        psi_center + (mask_pts[:, 1] - 0.5) * psi_span,
    ]
).astype(float)

# ---------------------------- Background clouds ----------------------------
bg_clouds = {}
rng_bg = np.random.default_rng(SEED + 123)
for cfg in regions.values():
    mu = cfg["mu"]
    sig = cfg["sigma"]
    bg = mu + rng_bg.normal(scale=sig * 1.2, size=(500, 2))
    bg[:, 0] = np.clip(bg[:, 0], PHI_MIN, PHI_MAX)
    bg[:, 1] = np.clip(bg[:, 1], PSI_MIN, PSI_MAX)
    bg_clouds[id(cfg)] = bg

# ---------------------------- d-block colors ----------------------------
D_BLOCK = [
    "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn",
    "Y", "Zr", "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd",
    "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg",
    "Rf", "Db", "Sg", "Bh", "Hs", "Mt", "Ds", "Rg", "Cn",
]
cmap = plt.get_cmap("turbo", len(D_BLOCK))
D_COLORS = np.array([cmap(i) for i in range(len(D_BLOCK))], dtype=float)


def fade_rgb(rgb: Tuple[float, float, float], whiten: float) -> Tuple[float, float, float]:
    rgb = np.array(rgb[:3], dtype=float)
    out = (1 - whiten) * rgb + whiten * np.ones(3)
    return tuple(out.tolist())


# ---------------------------- Fireworks ----------------------------
@dataclass
class FireworkBurst:
    start_frame: int
    center: np.ndarray
    color_rgba: np.ndarray
    symbol: Optional[str]
    n_sparks: int = 100
    life: int = 28
    speed: float = 8.0

    def __post_init__(self):
        angles = rng.uniform(0, 2 * np.pi, size=self.n_sparks)
        radii = rng.uniform(0.55, 1.0, size=self.n_sparks)
        self.dir = np.column_stack([np.cos(angles), np.sin(angles)]) * radii[:, None]
        self.jitter = rng.normal(scale=0.16, size=(self.n_sparks, 2))

    def sample(self, frame: int):
        age = frame - self.start_frame
        if age < 0 or age >= self.life:
            return None
        t = age / max(1, (self.life - 1))
        r = self.speed * (0.2 + 1.8 * t - 0.9 * (t**2))
        gravity = -18.0 * (t**2)
        pos = self.center + self.dir * r + self.jitter * (0.35 + 0.9 * t)
        pos[:, 1] += gravity
        a = (1.0 - t) ** 1.7
        rgba = np.tile(self.color_rgba, (self.n_sparks, 1))
        rgba[:, 3] = rgba[:, 3] * a
        pos[:, 0] = np.clip(pos[:, 0], PHI_MIN, PHI_MAX)
        pos[:, 1] = np.clip(pos[:, 1], PSI_MIN, PSI_MAX)
        return pos, rgba, t


def build_fireworks(num_bursts: int, start_at_frame: int, duration: int) -> List[FireworkBurst]:
    bursts = []
    latest_start = start_at_frame + max(1, duration - 15)
    start_frames = rng.integers(start_at_frame, latest_start, size=num_bursts)
    for i in range(num_bursts):
        sf = int(start_frames[i])
        phi = rng.uniform(-170, 170)
        psi = rng.uniform(-10, 178)
        idx = int(rng.integers(0, len(D_BLOCK)))
        symbol = D_BLOCK[idx] if rng.random() < TEXT_SYMBOL_PROB else None
        color = D_COLORS[idx].copy()
        n_sparks = int(rng.integers(85, 140))
        life = int(rng.integers(22, 32))
        speed = float(rng.uniform(6.5, 9.5))
        bursts.append(
            FireworkBurst(sf, np.array([phi, psi]), color, symbol,
                         n_sparks=n_sparks, life=life, speed=speed)
        )
    return bursts


# ---------------------------- PDB watermarks ----------------------------
PREFERRED_CHAIN: Dict[str, Optional[str]] = {
    "4ACH": "A", "4J1R": "A", "3SAY": "A", "5F94": "A",
}
PLACEMENTS = [
    ("4ACH", (-140, 135), (110, 80), -18),
    ("4J1R", (120, 140), (115, 80), 16),
    ("3SAY", (-120, 10), (125, 85), 10),
    ("5F94", (125, -25), (125, 85), -10),
]


def download_pdb_text(pdb_id: str) -> str:
    url = f"https://files.rcsb.org/download/{pdb_id.upper()}.pdb"
    with urllib.request.urlopen(url, timeout=25) as resp:
        data = resp.read()
    return data.decode("utf-8", errors="replace")


def parse_ca_trace(pdb_text: str, chain: Optional[str] = None) -> np.ndarray:
    ca = []
    fallback = []
    for line in pdb_text.splitlines():
        if not line.startswith("ATOM"):
            continue
        atom_name = line[12:16].strip()
        ch = line[21].strip()
        try:
            x = float(line[30:38]); y = float(line[38:46]); z = float(line[46:54])
        except ValueError:
            continue
        if chain is None or ch == chain:
            fallback.append((x, y, z))
            if atom_name == "CA":
                ca.append((x, y, z))
    return np.array(ca if len(ca) >= 25 else fallback, dtype=float)


def pca_project_2d(coords3: np.ndarray) -> np.ndarray:
    X = coords3 - coords3.mean(axis=0, keepdims=True)
    if len(X) < 3:
        return np.zeros((len(X), 2), dtype=float)
    _, _, Vt = np.linalg.svd(X, full_matrices=False)
    axes = Vt[:2].T
    return X @ axes


def rotate_2d(Y: np.ndarray, deg: float) -> np.ndarray:
    rad = np.deg2rad(deg)
    R = np.array([[np.cos(rad), -np.sin(rad)],
                  [np.sin(rad),  np.cos(rad)]], dtype=float)
    return Y @ R.T


def place_watermark(Y: np.ndarray, center: Tuple[float, float],
                    span: Tuple[float, float], rot_deg: float) -> np.ndarray:
    if len(Y) == 0:
        return Y
    Y0 = Y - Y.mean(axis=0, keepdims=True)
    scale = np.max(np.linalg.norm(Y0, axis=1))
    if scale < 1e-9:
        scale = 1.0
    Y0 = Y0 / scale
    Y0 = rotate_2d(Y0, rot_deg)
    cx, cy = center
    sx, sy = span
    out = np.empty_like(Y0)
    out[:, 0] = cx + Y0[:, 0] * (sx / 2.0)
    out[:, 1] = cy + Y0[:, 1] * (sy / 2.0)
    out[:, 0] = np.clip(out[:, 0], PHI_MIN, PHI_MAX)
    out[:, 1] = np.clip(out[:, 1], PSI_MIN, PSI_MAX)
    return out


def build_watermark_traces() -> List[Dict]:
    traces = []
    print("[INFO] Downloading PDB watermarks (optional; will skip if slow/fails)...")
    for i, (pid, center, span, rot) in enumerate(PLACEMENTS):
        try:
            txt = download_pdb_text(pid)
        except Exception as e:
            print(f"[WARN] Could not download {pid}: {e}")
            continue

        chain = PREFERRED_CHAIN.get(pid, None)
        coords3 = parse_ca_trace(txt, chain=chain)
        if len(coords3) < 10:
            print(f"[WARN] Too few atoms for {pid}; skipping.")
            continue

        Y = pca_project_2d(coords3)
        XY = place_watermark(Y, center=center, span=span, rot_deg=rot)
        col = fade_rgb(tuple(D_COLORS[(i * 7) % len(D_COLORS)][:3]), whiten=WM_WHITEN)
        traces.append({"pdb_id": pid, "chain": chain, "xy": XY, "color": col})
        print(f"[OK] Watermark ready: {pid} chain={chain} points={len(XY)}")
    return traces


try:
    WATERMARK_TRACES = build_watermark_traces()
except Exception as e:
    print(f"[WARN] Watermarks disabled due to error: {e}")
    WATERMARK_TRACES = []


def draw_watermarks(ax):
    for t in WATERMARK_TRACES:
        xy = t["xy"]
        c = t["color"]
        ax.plot(xy[:, 0], xy[:, 1], color=c, linewidth=WM_LINEWIDTH,
                alpha=WM_ALPHA_LINE, zorder=2)
        step = max(1, len(xy) // 90)
        ax.scatter(xy[::step, 0], xy[::step, 1],
                   s=WM_DOTSIZE, color=c, alpha=WM_ALPHA_DOTS,
                   edgecolors="none", zorder=2)


# ---------------------------- Plot helpers ----------------------------
def draw_background(ax, bg_alpha: float = 0.03):
    ax.set_xlim(PHI_MIN, PHI_MAX)
    ax.set_ylim(PSI_MIN, PSI_MAX)
    ax.set_xlabel("\u03A6 (phi) / degrees", fontsize=12, fontweight="bold")
    ax.set_ylabel("\u03A8 (psi) / degrees", fontsize=12, fontweight="bold")
    ax.set_xticks(np.arange(-180, 181, 60))
    ax.set_yticks(np.arange(-180, 181, 60))
    ax.set_axisbelow(True)
    ax.grid(True, alpha=0.25, linewidth=0.6)
    for bg in bg_clouds.values():
        ax.scatter(bg[:, 0], bg[:, 1], s=3.5, alpha=bg_alpha, c="gray",
                   edgecolors="none", zorder=1)


def draw_text_branding(ax, alpha: float = 1.0):
    ax.text(BRAND_X - 0.11, BRAND_Y, "[",
            transform=ax.transAxes, ha="center", va="center",
            fontsize=20, fontweight="bold",
            color=BRAND_LEFT_BRACKET_COLOR, alpha=alpha, zorder=30)
    ax.text(BRAND_X, BRAND_Y, "SCIENCE LANE",
            transform=ax.transAxes, ha="center", va="center",
            fontsize=BRAND_FONT, fontweight="bold",
            color=BRAND_TEXT_COLOR, alpha=alpha, zorder=30)
    ax.text(BRAND_X + 0.11, BRAND_Y, "]",
            transform=ax.transAxes, ha="center", va="center",
            fontsize=20, fontweight="bold",
            color=BRAND_RIGHT_BRACKET_COLOR, alpha=alpha, zorder=30)


def _logo_rgba_array_with_alpha(path: str, alpha: float) -> np.ndarray:
    """Load any image (jpg/png), convert to RGBA, apply opacity, return uint8 RGBA array."""
    im = Image.open(path).convert("RGBA")
    arr = np.array(im, dtype=np.uint8)
    a = float(np.clip(alpha, 0.0, 1.0))
    arr[..., 3] = (arr[..., 3].astype(np.float32) * a).clip(0, 255).astype(np.uint8)
    return arr


def draw_branding(ax, alpha: float = 1.0):
    """Science Lane logo INSIDE plot at bottom-right (alpha controlled externally)."""
    if not BRAND_ENABLED:
        return
    if alpha <= 0.001:
        return

    if BRAND_LOGO_PATH and os.path.exists(BRAND_LOGO_PATH):
        try:
            rgba = _logo_rgba_array_with_alpha(BRAND_LOGO_PATH, BRAND_LOGO_ALPHA * alpha)

            x0, y0, w, h = BRAND_INSET
            ax_logo = ax.inset_axes([x0, y0, w, h], transform=ax.transAxes, zorder=30)

            ax_logo.set_xticks([]); ax_logo.set_yticks([])
            ax_logo.set_frame_on(False)
            if BRAND_BACKING:
                ax_logo.patch.set_facecolor("white")
                ax_logo.patch.set_alpha(BRAND_BACKING_ALPHA * alpha)
            else:
                ax_logo.patch.set_alpha(0.0)

            ax_logo.imshow(rgba)
            ax_logo.set_aspect("equal")
            ax_logo.axis("off")
            return
        except Exception as e:
            print(f"[WARN] Could not load logo: {e} (falling back to text)")

    # fallback text branding also respects alpha
    draw_text_branding(ax, alpha)


# ---------------------------- MP4 writer ----------------------------
def save_mp4_ffmpeg(frames_rgb: List[np.ndarray], out_mp4: str, fps: float):
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        print("[WARN] ffmpeg not found. Skipping MP4. Install: sudo apt install ffmpeg")
        return

    tmpdir = tempfile.mkdtemp(prefix="rama_frames_")
    try:
        for i, fr in enumerate(frames_rgb):
            Image.fromarray(fr).save(os.path.join(tmpdir, f"frame_{i:05d}.png"))

        cmd = [
            ffmpeg, "-y",
            "-framerate", f"{fps:.3f}",
            "-i", os.path.join(tmpdir, "frame_%05d.png"),
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
            "-movflags", "+faststart",
            out_mp4,
        ]
        subprocess.run(cmd, check=True, capture_output=True)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ---------------------------- MAIN ----------------------------
def main():
    frames: List[np.ndarray] = []

    # Phase 1: Fill
    points = np.zeros((0, 2), dtype=float)
    print(f"[1/3] Generating fill phase ({FRAMES_FILL} frames)...")
    for f in range(FRAMES_FILL):
        points = np.vstack([points, sample_region_points(ADD_PER_FRAME)])
        if len(points) > N_MAX:
            points = points[:N_MAX]

        fig, ax = plt.subplots(figsize=(FIGURE_SIZE[0] / DPI, FIGURE_SIZE[1] / DPI), dpi=DPI)
        draw_background(ax, bg_alpha=0.03)

        ax.text(0.02, 0.98, TOP_TITLE_FILL,
                transform=ax.transAxes, va="top",
                fontsize=13, fontweight="bold")
        ax.scatter(points[:, 0], points[:, 1], s=7, alpha=0.86,
                   c="steelblue", edgecolors="none", zorder=3)

        # Logo hidden here automatically (brand_alpha = 0)
        global_frame = f
        draw_branding(ax, alpha=brand_alpha(global_frame))

        fig.tight_layout(pad=0.3)
        frames.append(fig_to_rgb_array(fig))
        plt.close(fig)

        if (f + 1) % 20 == 0:
            print(f"  → {f + 1}/{FRAMES_FILL} frames")

    # Phase 2: Morph
    print(f"[2/3] Generating morph phase ({FRAMES_MORPH} frames)...")
    N = len(points)
    assign = rng.integers(0, len(target_digits), size=N)
    tgt = target_digits[assign]
    start = points.copy()
    last_pos = None

    for k in range(FRAMES_MORPH):
        u = ease_in_out((k + 1) / FRAMES_MORPH)
        pos = (1 - u) * start + u * tgt
        last_pos = pos

        fig, ax = plt.subplots(figsize=(FIGURE_SIZE[0] / DPI, FIGURE_SIZE[1] / DPI), dpi=DPI)
        draw_background(ax, bg_alpha=0.03)

        ax.text(0.02, 0.98, TOP_TITLE_FINAL,
                transform=ax.transAxes, va="top",
                fontsize=13, fontweight="bold")

        if k >= FRAMES_MORPH - WM_DRAW_DURING_LAST_MORPH_FRAMES:
            draw_watermarks(ax)

        ax.scatter(pos[:, 0], pos[:, 1], s=8, alpha=0.90,
                   c="steelblue", edgecolors="none", zorder=4)

        # “2026” reveal (last 8 frames)
        if k >= FRAMES_MORPH - 8:
            ax.text(0.5, 0.09, "2026",
                    transform=ax.transAxes, ha="center",
                    fontsize=32, fontweight="bold", alpha=0.60)

        # Logo fades in parallel to "2026"
        global_frame = FRAMES_FILL + k
        draw_branding(ax, alpha=brand_alpha(global_frame))

        fig.tight_layout(pad=0.3)
        frames.append(fig_to_rgb_array(fig))
        plt.close(fig)

    # Phase 3: Hold + fireworks
    print(f"[3/3] Generating fireworks phase ({HOLD_FRAMES} frames)...")
    if last_pos is None:
        last_pos = points

    hold_start_global = FRAMES_FILL + FRAMES_MORPH
    bursts = build_fireworks(NUM_BURSTS, hold_start_global, HOLD_FRAMES)
    MSG_FADE_FRAMES = min(12, max(6, HOLD_FRAMES // 6))

    for h in range(HOLD_FRAMES):
        global_frame = hold_start_global + h

        fig, ax = plt.subplots(figsize=(FIGURE_SIZE[0] / DPI, FIGURE_SIZE[1] / DPI), dpi=DPI)
        draw_background(ax, bg_alpha=0.02)
        draw_watermarks(ax)

        ax.scatter(last_pos[:, 0], last_pos[:, 1], s=8, alpha=0.92,
                   c="steelblue", edgecolors="none", zorder=5)

        ax.text(HNY_X, HNY_Y, HAPPY_NEW_YEAR_TEXT,
                transform=ax.transAxes, ha="center",
                fontsize=HNY_FONT, fontweight="bold",
                alpha=0.75, zorder=9)

        spark_pos_list = []
        spark_rgba_list = []
        symbol_draws = []

        for b in bursts:
            out = b.sample(global_frame)
            if out is None:
                continue
            p, rgba, t = out
            spark_pos_list.append(p)
            spark_rgba_list.append(rgba)

            if b.symbol is not None and (0.10 <= t <= 0.55):
                a_sym = float((1.0 - t) ** 1.2)
                symbol_draws.append((b.center[0], b.center[1], b.symbol, b.color_rgba[:3], a_sym))

        if spark_pos_list:
            P = np.vstack(spark_pos_list)
            C = np.vstack(spark_rgba_list)
            ax.scatter(P[:, 0], P[:, 1], s=SPARK_SIZE, c=C,
                       edgecolors="none", zorder=10)

        for x, y, sym, col, a_sym in symbol_draws:
            ax.text(x, y, sym, ha="center", va="center", fontsize=15,
                    fontweight="bold", color=col, alpha=0.95 * a_sym, zorder=11)

        msg_alpha = 1.0 if h >= MSG_FADE_FRAMES else (h / MSG_FADE_FRAMES)
        ax.text(MSG_X, MSG_Y, FINAL_MESSAGE,
                transform=ax.transAxes, ha="center", va="bottom",
                fontsize=MSG_FONT, fontweight="bold",
                alpha=0.92 * msg_alpha,
                bbox=dict(facecolor="white", alpha=MSG_BOX_ALPHA * msg_alpha,
                          edgecolor="none", pad=4),
                zorder=12)

        # Logo continues at full alpha after fade completes
        draw_branding(ax, alpha=brand_alpha(global_frame))

        fig.tight_layout(pad=0.3)
        frames.append(fig_to_rgb_array(fig))
        plt.close(fig)

        if (h + 1) % 15 == 0:
            print(f"  → {h + 1}/{HOLD_FRAMES} frames")

    # Save GIF (optimized)
    print(f"\n[SAVE] Creating optimized GIF: {OUT_GIF} ...")
    imgs = [Image.fromarray(f) for f in frames]
    imgs[0].save(
        OUT_GIF,
        save_all=True,
        append_images=imgs[1:],
        duration=FRAME_MS,
        loop=0,
        optimize=True,
        disposal=2
    )
    size_mb = os.path.getsize(OUT_GIF) / (1024 * 1024)
    print(f"✓ Saved GIF: {OUT_GIF} ({len(frames)} frames, {size_mb:.2f} MB)")

    # Save MP4
    print(f"[SAVE] Creating MP4: {OUT_MP4} ...")
    save_mp4_ffmpeg(frames, OUT_MP4, FPS)
    if os.path.exists(OUT_MP4):
        size_mb = os.path.getsize(OUT_MP4) / (1024 * 1024)
        print(f"✓ Saved MP4: {OUT_MP4} (fps={FPS:.1f}, {size_mb:.2f} MB)")

    print("\n" + "=" * 60)
    print("OPTIMIZATION SUMMARY FOR SOCIAL MEDIA:")
    print("=" * 60)
    print("✓ Square format: 1080x1080px (IG/FB/WhatsApp friendly)")
    print(f"✓ Total frames: {len(frames)}")
    print(f"✓ Duration: ~{len(frames) * FRAME_MS / 1000:.1f}s")
    print("✓ Logo fades in parallel to '2026' (not visible at beginning)")
    print("=" * 60)


if __name__ == "__main__":
    main()


# In[ ]:




