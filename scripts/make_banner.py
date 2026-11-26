"""Generate the waveform profile banner (light and dark) with text converted to outlines.

Run: uv run --with fonttools --with uharfbuzz scripts/make_banner.py
Fonts (Inter 400/700) are downloaded once into .cache/fonts.
"""

import math
import re
import urllib.request
from pathlib import Path

import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".cache" / "fonts"
OUT = ROOT / "assets"

W, H = 840, 230
NAME_1, NAME_2 = "Tanmay", "Nargas"
TAGLINE = "MSc AI @ NTU · agents, native apps, ML · open to work"
TITLE = "Tanmay Nargas. MSc AI at NTU Singapore. Agents, native apps and ML. Open to work."

THEMES = {
    "light": {"bg": "#f6f8fa", "fg": "#1f2328", "muted": "#59636e", "bar": "#30a14e", "bar_hi": "#216e39"},
    "dark": {"bg": "#151b23", "fg": "#f0f6fc", "muted": "#9198a1", "bar": "#26a641", "bar_hi": "#39d353"},
}


def fetch_fonts():
    CACHE.mkdir(parents=True, exist_ok=True)
    paths = {w: CACHE / f"Inter-{w}.ttf" for w in (400, 700)}
    if all(p.exists() for p in paths.values()):
        return paths
    req = urllib.request.Request(
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;700",
        headers={"User-Agent": "Mozilla/4.0"},  # legacy UA makes the API return TTF
    )
    css = urllib.request.urlopen(req).read().decode()
    for weight, url in re.findall(r"font-weight:\s*(\d+);.*?src:\s*url\((\S+?\.ttf)\)", css, re.S):
        dest = paths.get(int(weight))
        if dest:
            dest.write_bytes(urllib.request.urlopen(url).read())
    missing = [str(p) for p in paths.values() if not p.exists()]
    if missing:
        raise SystemExit(f"font download failed: {missing}")
    return paths


def fmt(v):
    s = f"{v:.1f}"
    return s[:-2] if s.endswith(".0") else s


def text_path(fontfile, text, size, x, baseline, tracking=0.0):
    """Shape text with HarfBuzz (kerning on) and return (svg path d, advance width in px)."""
    hb_font = hb.Font(hb.Face(hb.Blob.from_file_path(str(fontfile))))
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(hb_font, buf, {"kern": True, "liga": True})

    tt = TTFont(fontfile)
    glyphs = tt.getGlyphSet()
    order = tt.getGlyphOrder()
    scale = size / tt["head"].unitsPerEm
    pen = SVGPathPen(glyphs, ntos=fmt)
    cursor = 0.0
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        dx = x + (cursor + pos.x_offset) * scale
        dy = baseline - pos.y_offset * scale
        glyphs[order[info.codepoint]].draw(TransformPen(pen, (scale, 0, 0, -scale, dx, dy)))
        cursor += pos.x_advance + tracking / scale
    return pen.getCommands(), cursor * scale


def bars(theme):
    out = []
    for i in range(38):
        h = 18 + round(70 * abs(math.sin(i * 0.55) * math.cos(i * 0.17)))
        x = 470 + i * 9
        fill = theme["bar_hi"] if i % 5 == 0 else theme["bar"]
        out.append(
            f'<rect class="b" x="{x}" y="{fmt(115 - h / 2)}" width="5" height="{h}" rx="2.5" '
            f'fill="{fill}" style="animation-delay:{i * 0.07:.2f}s"/>'
        )
    return "\n".join(out)


def build(theme, fonts):
    name1, _ = text_path(fonts[700], NAME_1, 50, 40, 104, tracking=-1)
    name2, _ = text_path(fonts[700], NAME_2, 50, 40, 156, tracking=-1)
    tag, _ = text_path(fonts[400], TAGLINE, 15, 42, 192)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="title">
<title id="title">{TITLE}</title>
<style>
@keyframes wave {{ 0%, 100% {{ transform: scaleY(.35) }} 50% {{ transform: scaleY(1) }} }}
.b {{ transform-box: fill-box; transform-origin: center; animation: wave 1.4s ease-in-out infinite }}
@media (prefers-reduced-motion: reduce) {{ .b {{ animation: none }} }}
</style>
<rect width="{W}" height="{H}" rx="10" fill="{theme['bg']}"/>
<path d="{name1}" fill="{theme['fg']}"/>
<path d="{name2}" fill="{theme['fg']}"/>
<path d="{tag}" fill="{theme['muted']}"/>
{bars(theme)}
</svg>
"""


def main():
    fonts = fetch_fonts()
    for key, theme in THEMES.items():
        path = OUT / f"banner-{key}.svg"
        path.write_text(build(theme, fonts))
        print(f"wrote {path.relative_to(ROOT)} ({path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
