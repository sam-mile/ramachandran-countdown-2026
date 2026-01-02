# Ramachandran New Year Countdown → 2026

Create a social-media–ready animation of a **Ramachandran plot (φ/ψ)** that:
1) fills the common allowed regions,  
2) morphs the points into **“2026”**, and  
3) finishes with **fireworks** (sparks can show **d‑block element symbols**) plus optional **PDB silhouette watermarks**.

**Outputs (written to the working directory):**
- `rama_2026_social.gif`
- `rama_2026_social.mp4` *(optional; requires `ffmpeg`)*

---

## Download & run (no git)

1. Click **Code → Download ZIP** on GitHub.
2. Unzip the folder.
3. Install dependencies (see below).
4. Run:
   ```bash
   python ramachandran_new_year_countdown_2026.py
   ```

---

## Requirements

- Python **3.9+** recommended
- Python packages:
  - `numpy`
  - `matplotlib`
  - `scipy`
  - `pillow`
- Optional system dependency (to write MP4):
  - `ffmpeg`

### Install (pip)

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Install ffmpeg (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install ffmpeg
```

---

## Run

```bash
python ramachandran_new_year_countdown_2026.py
```

If `ffmpeg` is not found, the script will still save the **GIF** and simply skip the MP4.

---

## Notes & customization

### 1) Science Lane logo (optional)
The script can place a logo inside the plot. Update this line in the script:

```python
BRAND_LOGO_PATH = "/path/to/science_lane_logo.jpg"
```

If the logo file is not found, the script falls back to a simple **[ SCIENCE LANE ]** text mark.

### 2) PDB watermarks (optional)
The script attempts to download PDB files from RCSB and render faint silhouette traces as watermarks:
- `4ACH`, `4J1R`, `3SAY`, `5F94`

If the download fails (no internet / timeout), it will continue **without** watermarks.

### 3) Social media settings
The defaults are tuned for square 1080×1080 (IG/FB/WhatsApp). You can change:
- `FIGURE_SIZE`, `DPI`
- `FRAMES_FILL`, `FRAMES_MORPH`, `HOLD_SECONDS`
- `NUM_BURSTS` (fireworks density)

---

## What the script does (high level)

- Samples points from three Gaussian “allowed regions” (α-helix / β-sheet-like clusters) to mimic a Ramachandran density.
- Uses a text mask to define where points should move to form the “2026” digits.
- Adds fireworks bursts near the top of the plot with per-burst colors and optional element symbols.
- Saves the animation as GIF and (optionally) MP4.

---

## License

MIT — see [`LICENSE`](LICENSE).
