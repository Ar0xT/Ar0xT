"""Small helpers shared by all the generators. Fonts, text outlines, masks and path tools."""
import base64
import io
import math
import os

import numpy as np
import uharfbuzz as hb
from fontTools.pens.basePen import BasePen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.subset import Options, Subsetter
from fontTools.ttLib import TTFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "fonts")
ASSETS = os.path.join(os.path.dirname(HERE), "assets")

# palette used across every panel
BG = "#0d1117"          # same as github dark, so panels melt into the page
INK = "#e6edf3"         # main text
DIM = "#7d8590"         # secondary text
FAINT = "#30363d"       # hairlines
ACCENT = "#7cf0ff"      # cold cyan
ACCENT2 = "#b48cff"     # violet
HOT = "#ff6a3d"         # signal orange, used rarely


def font_path(name):
    return os.path.join(FONTS, name)


class Font:
    """A font we can shape text with and pull outlines from."""

    def __init__(self, filename):
        self.path = filename if os.path.isabs(filename) else font_path(filename)
        self.tt = TTFont(self.path)
        self.upem = self.tt["head"].unitsPerEm
        # static cuts of variable fonts keep overlapping contours, which show up as
        # stray lines the moment you stroke an outline. merge them.
        if "glyf" in self.tt:
            try:
                from fontTools.ttLib.removeOverlaps import removeOverlaps
                removeOverlaps(self.tt)
            except Exception:
                pass
        self.glyphset = self.tt.getGlyphSet()
        # harfbuzz wants plain sfnt bytes, so dump the ttfont back out
        buf = io.BytesIO()
        tt2 = TTFont(self.path)
        tt2.flavor = None
        tt2.save(buf)
        self.hb_face = hb.Face(buf.getvalue())
        self.hb_font = hb.Font(self.hb_face)
        self.order = self.tt.getGlyphOrder()
        os2 = self.tt["OS/2"]
        self.cap = getattr(os2, "sCapHeight", 0) or self.upem * 0.7
        self.xh = getattr(os2, "sxHeight", 0) or self.upem * 0.5
        self.asc = self.tt["hhea"].ascent
        self.desc = self.tt["hhea"].descent

    def shape(self, text, tracking=0.0):
        """Returns list of (glyph name, x offset, y offset) in font units, and total advance."""
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(self.hb_font, buf, {"kern": True, "liga": False})
        out = []
        x = 0.0
        for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
            name = self.order[info.codepoint]
            out.append((name, x + pos.x_offset, pos.y_offset))
            x += pos.x_advance + tracking * self.upem
        return out, x - tracking * self.upem

    def width(self, text, size, tracking=0.0):
        _, adv = self.shape(text, tracking)
        return adv * size / self.upem

    def path_d(self, text, size, x=0.0, y=0.0, tracking=0.0, anchor="start", precision=2):
        """SVG path data for a line of text, baseline at y."""
        glyphs, adv = self.shape(text, tracking)
        s = size / self.upem
        if anchor == "middle":
            x -= adv * s / 2
        elif anchor == "end":
            x -= adv * s
        pen = SVGPathPen(self.glyphset, ntos=lambda v: fmt(v, precision))
        for name, gx, gy in glyphs:
            tp = TransformPen(pen, (s, 0, 0, -s, x + gx * s, y - gy * s))
            self.glyphset[name].draw(tp)
        return pen.getCommands()

    def glyph_paths(self, text, size, x=0.0, y=0.0, tracking=0.0, anchor="start", precision=2):
        """One path per glyph, handy when each letter animates on its own."""
        glyphs, adv = self.shape(text, tracking)
        s = size / self.upem
        if anchor == "middle":
            x -= adv * s / 2
        elif anchor == "end":
            x -= adv * s
        res = []
        for name, gx, gy in glyphs:
            pen = SVGPathPen(self.glyphset, ntos=lambda v: fmt(v, precision))
            tp = TransformPen(pen, (s, 0, 0, -s, x + gx * s, y - gy * s))
            self.glyphset[name].draw(tp)
            res.append((name, pen.getCommands(), x + gx * s))
        return res

    def polygons(self, text, size, x=0.0, y=0.0, tracking=0.0, anchor="start", step=1.0):
        """Flattened outlines as lists of (x, y) points, for rasterizing masks."""
        glyphs, adv = self.shape(text, tracking)
        s = size / self.upem
        if anchor == "middle":
            x -= adv * s / 2
        elif anchor == "end":
            x -= adv * s
        pen = _FlattenPen(self.glyphset, step)
        for name, gx, gy in glyphs:
            tp = TransformPen(pen, (s, 0, 0, -s, x + gx * s, y - gy * s))
            self.glyphset[name].draw(tp)
        return pen.contours

    def glyph_polygons(self, text, size, x=0.0, y=0.0, tracking=0.0, anchor="start", step=1.0):
        """Like polygons, but grouped per glyph so each letter can be scaled on its own."""
        glyphs, adv = self.shape(text, tracking)
        s = size / self.upem
        if anchor == "middle":
            x -= adv * s / 2
        elif anchor == "end":
            x -= adv * s
        res = []
        for name, gx, gy in glyphs:
            pen = _FlattenPen(self.glyphset, step)
            tp = TransformPen(pen, (s, 0, 0, -s, x + gx * s, y - gy * s))
            self.glyphset[name].draw(tp)
            if pen.contours:
                res.append(pen.contours)
        return res

    def data_uri(self, text_used):
        """Subset the font down to the characters we use and return a woff2 data uri."""
        opts = Options()
        opts.flavor = "woff2"
        opts.layout_features = ["kern"]
        opts.name_IDs = []
        opts.notdef_outline = True
        tt = TTFont(self.path)
        sub = Subsetter(opts)
        sub.populate(text="".join(sorted(set(text_used))) + " ")
        sub.subset(tt)
        tt.flavor = "woff2"
        buf = io.BytesIO()
        tt.save(buf)
        return "data:font/woff2;base64," + base64.b64encode(buf.getvalue()).decode()


class _FlattenPen(BasePen):
    def __init__(self, glyphset, step):
        super().__init__(glyphset)
        self.step = step
        self.contours = []
        self.cur = []

    def _moveTo(self, p):
        self.cur = [p]

    def _lineTo(self, p):
        self.cur.append(p)

    def _curveToOne(self, p1, p2, p3):
        p0 = self.cur[-1]
        n = max(4, int(_dist(p0, p3) / self.step))
        for i in range(1, n + 1):
            t = i / n
            mt = 1 - t
            self.cur.append((
                mt ** 3 * p0[0] + 3 * mt * mt * t * p1[0] + 3 * mt * t * t * p2[0] + t ** 3 * p3[0],
                mt ** 3 * p0[1] + 3 * mt * mt * t * p1[1] + 3 * mt * t * t * p2[1] + t ** 3 * p3[1],
            ))

    def _qCurveToOne(self, p1, p2):
        p0 = self.cur[-1]
        n = max(4, int(_dist(p0, p2) / self.step))
        for i in range(1, n + 1):
            t = i / n
            mt = 1 - t
            self.cur.append((
                mt * mt * p0[0] + 2 * mt * t * p1[0] + t * t * p2[0],
                mt * mt * p0[1] + 2 * mt * t * p1[1] + t * t * p2[1],
            ))

    def _closePath(self):
        if len(self.cur) > 2:
            self.contours.append(self.cur)
        self.cur = []

    _endPath = _closePath


def _dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def fmt(v, precision=1):
    """Shortest decent number string, no trailing zeros, no leading zero."""
    if abs(v) < 10 ** -precision / 2:
        return "0"
    s = f"{v:.{precision}f}".rstrip("0").rstrip(".")
    if s.startswith("0."):
        s = s[1:]
    elif s.startswith("-0."):
        s = "-" + s[2:]
    return s


def poly_d(pts, precision=1, closed=False):
    """Compact path data for a polyline, using relative moves to save bytes."""
    if len(pts) == 0:
        return ""
    out = [f"M{fmt(pts[0][0], precision)} {fmt(pts[0][1], precision)}"]
    px, py = round(pts[0][0], precision), round(pts[0][1], precision)
    parts = []
    for x, y in pts[1:]:
        x, y = round(x, precision), round(y, precision)
        dx, dy = x - px, y - py
        a, b = fmt(dx, precision), fmt(dy, precision)
        sep = "" if b.startswith("-") else " "
        parts.append(f"{a}{sep}{b}")
        px, py = x, y
    if parts:
        out.append("l" + " ".join(_join_signs(parts)))
    if closed:
        out.append("z")
    return "".join(out)


def _join_signs(parts):
    return parts


def rel_poly_d(pts, precision=1):
    """Absolute first point, then one relative l per point. Every point always gets its own
    segment so two lines with the same point count morph cleanly into each other."""
    q = np.round(np.asarray(pts, dtype=float), precision)
    head = f"M{join_nums([fmt(q[0, 0], precision), fmt(q[0, 1], precision)])}"
    if len(q) < 2:
        return head
    nums = []
    for dx, dy in np.diff(q, axis=0):
        nums.append(fmt(dx, precision))
        nums.append(fmt(dy, precision))
    return head + "l" + join_nums(nums)


def join_nums(nums):
    """Join numbers with the fewest separators the svg path grammar allows."""
    out = []
    prev = None
    for s in nums:
        if prev is None or s.startswith("-") or (s.startswith(".") and "." in prev):
            out.append(s)
        else:
            out.append(" " + s)
        prev = s
    return "".join(out)


def abs_poly_d(pts, precision=1):
    """Absolute coordinates version. SMIL path morphing needs both ends to use the same commands."""
    return "M" + " L".join(f"{fmt(x, precision)} {fmt(y, precision)}" for x, y in pts)


def rdp(points, eps):
    """Ramer Douglas Peucker simplification, iterative so long lines don't blow the stack."""
    pts = np.asarray(points, dtype=float)
    n = len(pts)
    if n < 3:
        return pts
    keep = np.zeros(n, dtype=bool)
    keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        a, b = pts[i], pts[j]
        seg = b - a
        L = np.hypot(*seg)
        mid = pts[i + 1:j]
        if L == 0:
            d = np.hypot(*(mid - a).T)
        else:
            rel = mid - a
            d = np.abs(seg[0] * rel[:, 1] - seg[1] * rel[:, 0]) / L
        k = int(np.argmax(d))
        if d[k] > eps:
            m = i + 1 + k
            keep[m] = True
            stack.append((i, m))
            stack.append((m, j))
    return pts[keep]


def resample(points, n):
    """n points evenly spaced by arc length along a polyline."""
    pts = np.asarray(points, dtype=float)
    seg = np.hypot(*np.diff(pts, axis=0).T)
    s = np.concatenate([[0], np.cumsum(seg)])
    t = np.linspace(0, s[-1], n)
    return np.stack([np.interp(t, s, pts[:, 0]), np.interp(t, s, pts[:, 1])], axis=1)


def arclen(points):
    pts = np.asarray(points, dtype=float)
    return float(np.hypot(*np.diff(pts, axis=0).T).sum())


def svg_doc(w, h, body, defs="", style="", title=None, desc=None):
    t = f"<title>{title}</title>" if title else ""
    dsc = f"<desc>{desc}</desc>" if desc else ""
    st = f"<style>{style}</style>" if style else ""
    df = f"<defs>{defs}</defs>" if defs else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img">{t}{dsc}{st}{df}{body}</svg>')


def write(name, svg):
    # refuse to write anything a browser would choke on
    import xml.etree.ElementTree as ET
    ET.fromstring(svg)
    os.makedirs(ASSETS, exist_ok=True)
    p = os.path.join(ASSETS, name)
    with open(p, "w", encoding="utf-8") as f:
        f.write(svg)
    return p, len(svg.encode())


def hold_then(attr, hidden, shown, at, dur, spline=None):
    """Animate from hidden to shown, starting at time zero and holding hidden until 'at'.
    The element's own attribute should already be the shown value, so renderers without
    animation support still get the finished picture."""
    total = at + dur
    kt0 = fmt(at / total, 4)
    sp = f' calcMode="spline" keySplines="0 0 1 1;{spline}"' if spline else ""
    return (f'<animate attributeName="{attr}" begin="0s" dur="{fmt(total, 3)}s" fill="freeze"{sp} '
            f'keyTimes="0;{kt0};1" values="{hidden};{hidden};{shown}"/>')


def steps_from_zero(attr, first, values, at, dur):
    """Discrete steps through values over dur, starting at 'at'. Holds 'first' until then."""
    n = len(values)
    total = at + dur
    keys = ["0"] + [fmt((at + (i + 1) * dur / n) / total, 5) for i in range(n)]
    keys[-1] = "1"
    vals = [first] + list(values)
    return (f'<animate attributeName="{attr}" begin="0s" dur="{fmt(total, 3)}s" calcMode="discrete" fill="freeze" '
            f'keyTimes="{";".join(keys)}" values="{";".join(vals)}"/>')


def hidden_until(t):
    """Child for a group that should pop in at time t but stay visible when nothing animates."""
    return f'<set attributeName="visibility" to="hidden" begin="0s" dur="{fmt(t, 3)}s"/>'
