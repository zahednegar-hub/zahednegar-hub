"""Regenerate the Fanoos logo SVGs in ``assets/``.

Usage::

    pip install uharfbuzz fonttools
    python tools/build_logo.py assets InterDisplay-SemiBold.otf Vazirmatn-SemiBold.ttf

The wordmarks are outlined to paths, so the SVGs need no fonts at runtime.
Fonts: Inter Display (OFL) and Vazirmatn (OFL); ``.woff`` files work too.
"""

from __future__ import annotations

import io
import re
import sys
from pathlib import Path

AMBER = "#D97706"
INK = "#1C1917"
PAPER = "#F5F5F4"

# The flame is a teardrop whose base is notched into an upward arrow (light / path).
FLAME = (
    "M32 26c4.6 4.9 8 9.6 8 14.2 0 2.1-.9 3.9-2.4 5.2L32 39.8l-5.6 5.6c-1.5-1.3-2.4-3.1-2.4-5.2 0-4.6 3.4-9.3 8-14.2z"
)
STEM = "M30 43.8l2-2 2 2V48a2 2 0 0 1-4 0z"


def mark(frame: str, flame: str, stroke_width: float = 4) -> str:
    """Return the lantern mark on a 64-unit grid (4-unit strokes = 1px at 16px)."""
    return (
        f'<g fill="none" stroke="{frame}" stroke-width="{stroke_width:g}" '
        'stroke-linecap="round" stroke-linejoin="round">\n'
        '    <path d="M26 11a6 6 0 0 1 12 0"/>\n'
        '    <path d="M22 15h20"/>\n'
        '    <rect x="15" y="19" width="34" height="34" rx="13"/>\n'
        '    <path d="M22 57h20"/>\n'
        "  </g>\n"
        f'  <path fill="{flame}" d="{FLAME}"/>\n'
        f'  <path fill="{flame}" d="{STEM}"/>'
    )


def svg(body: str, width: float, height: float, title: str) -> str:
    """Wrap ``body`` in an accessible SVG document."""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:g} {height:g}" '
        f'role="img" aria-labelledby="t">\n  <title id="t">{title}</title>\n  {body}\n</svg>\n'
    )


def text_path(font_file: str, text: str, size: float, x: float, baseline: float) -> tuple[str, float]:
    """Shape ``text`` with HarfBuzz (correct Persian joining) and return ``(path_data, advance)``."""
    import uharfbuzz as hb
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.transformPen import TransformPen
    from fontTools.ttLib import TTFont

    source = TTFont(font_file)
    source.flavor = None  # unwrap woff/woff2 so HarfBuzz can read it
    buffer = io.BytesIO()
    source.save(buffer)
    data = buffer.getvalue()

    font = TTFont(io.BytesIO(data))
    face = hb.Face(data)
    shaped = hb.Buffer()
    shaped.add_str(text)
    shaped.guess_segment_properties()
    hb.shape(hb.Font(face), shaped, {"kern": True, "liga": True})

    scale = size / face.upem
    glyphs = font.getGlyphSet()
    order = font.getGlyphOrder()
    pen = SVGPathPen(glyphs)
    cursor = 0
    for info, pos in zip(shaped.glyph_infos, shaped.glyph_positions, strict=True):
        origin_x = x + (cursor + pos.x_offset) * scale
        origin_y = baseline - pos.y_offset * scale
        glyphs[order[info.codepoint]].draw(TransformPen(pen, (scale, 0, 0, -scale, origin_x, origin_y)))
        cursor += pos.x_advance
    return _round(pen.getCommands()), cursor * scale


def _round(path: str) -> str:
    return re.sub(r"-?\d+\.\d+", lambda m: f"{float(m.group()):.2f}".rstrip("0").rstrip("."), path)


def main(out_dir: str, latin_font: str, persian_font: str) -> None:
    """Write every logo variant to ``out_dir``."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    (out / "logo.svg").write_text(svg(mark(AMBER, AMBER), 64, 64, "Fanoos"), encoding="utf-8")
    (out / "logo-light.svg").write_text(svg(mark(INK, AMBER), 64, 64, "Fanoos"), encoding="utf-8")
    (out / "logo-mono.svg").write_text(svg(mark("currentColor", "currentColor"), 64, 64, "Fanoos"), encoding="utf-8")

    favicon = (
        f"<style>.s{{stroke:{INK}}}.f{{fill:{AMBER}}}"
        f"@media (prefers-color-scheme:dark){{.s{{stroke:{PAPER}}}}}</style>\n  "
        + mark("FRAME", "FLAME", 5).replace('stroke="FRAME"', 'class="s"').replace('fill="FLAME"', 'class="f"')
    )
    (out / "favicon.svg").write_text(svg(favicon, 64, 64, "Fanoos"), encoding="utf-8")

    # Horizontal lockup: mark, "Fanoos", a hairline divider, "فانوس".
    gap = 14
    latin, latin_width = text_path(latin_font, "Fanoos", 34, 64, 45)
    divider_x = 64 + latin_width + gap
    persian_x = divider_x + 1.5 + gap
    persian, persian_width = text_path(persian_font, "فانوس", 30, persian_x, 45)
    width = round(persian_x + persian_width + 2)

    def lockup(frame: str, word: str, divider: str) -> str:
        return (
            mark(frame, AMBER)
            + f'\n  <path fill="{word}" d="{latin}"/>'
            + f'\n  <rect x="{divider_x:.2f}" y="22" width="1.5" height="26" rx=".75" fill="{divider}"/>'
            + f'\n  <path fill="{word}" d="{persian}"/>'
        )

    title = "Fanoos — فانوس"
    (out / "logo-full.svg").write_text(svg(lockup(AMBER, PAPER, "#57534E"), width, 64, title), encoding="utf-8")
    (out / "logo-full-light.svg").write_text(svg(lockup(INK, INK, "#D6D3D1"), width, 64, title), encoding="utf-8")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    main(*sys.argv[1:])
