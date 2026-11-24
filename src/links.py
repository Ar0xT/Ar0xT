"""Contact buttons and the footer line. Each button is its own image so it can be its own link.
A thin light runs around each border, a little later on each button, so they shimmer in order."""
from svgkit import ACCENT, BG, DIM, INK, Font, fmt, svg_doc, write

BUTTONS = [
    ("email", "mail"),
    ("telegram", "send"),
]
BW, BH = 236, 60


def icon(kind, x, y, col):
    """Tiny generic icons drawn from lines, centered on x y."""
    s = f'fill="none" stroke="{col}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"'
    if kind == "mail":
        return (f'<rect x="{x - 9}" y="{y - 6.5}" width="18" height="13" rx="2.5" {s}/>'
                f'<path d="M{x - 8} {y - 5}l8 6 8 -6" {s}/>')
    if kind == "send":
        return f'<path d="M{x - 8} {y - 1}L{x + 9} {y - 8}L{x + 3} {y + 9}L{x} {y + 2}z M{x} {y + 2}L{x + 9} {y - 8}" {s}/>'
    if kind == "bars":
        return (f'<path d="M{x - 7} {y + 7}v-6 M{x} {y + 7}v-13 M{x + 7} {y + 7}v-9" {s.replace("1.6", "2.6")}/>')
    if kind == "braces":
        return (f'<path d="M{x - 3} {y - 8}q-4 0 -4 4v1.5q0 2.5 -2.5 2.5q2.5 0 2.5 2.5v1.5q0 4 4 4 '
                f'M{x + 3} {y - 8}q4 0 4 4v1.5q0 2.5 2.5 2.5q-2.5 0 -2.5 2.5v1.5q0 4 -4 4" {s}/>')
    return ""


def button(mono, label, kind, delay):
    w, h = BW, BH
    r = h / 2
    defs = (f'<linearGradient id="sw" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="90" y2="0">'
            f'<stop offset="0" stop-color="{ACCENT}" stop-opacity="0"/>'
            f'<stop offset=".5" stop-color="{ACCENT}" stop-opacity=".95"/>'
            f'<stop offset="1" stop-color="{ACCENT}" stop-opacity="0"/>'
            f'<animateTransform attributeName="gradientTransform" type="translate" begin="{fmt(delay, 2)}s" dur="5s" '
            f'repeatCount="indefinite" values="-120 0;{w + 40} 0;{w + 40} 0" keyTimes="0;.42;1"/></linearGradient>')
    body = [f'<rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="{r - 1}" fill="{BG}" stroke="#30363d" stroke-width="1.2"/>',
            f'<rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="{r - 1}" fill="none" stroke="url(#sw)" stroke-width="1.6"/>']
    body.append(icon(kind, 34, h / 2, ACCENT))
    tw = mono.width(label, 18)
    body.append(f'<path fill="{INK}" d="{mono.path_d(label, 18, 56, h / 2 + 6.2, precision=1)}"/>')
    ax = 56 + tw + 14
    ay = h / 2
    body.append(f'<path d="M{fmt(ax)} {fmt(ay + 5)}l9 -9 M{fmt(ax + 2)} {fmt(ay - 4)}h7v7" fill="none" stroke="{DIM}" '
                f'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>')
    return svg_doc(w, h, "".join(body), defs=defs, title=label)


def footer(mono):
    W, H = 1200, 96
    text = "every figure above is plain svg, drawn by the python scripts in src/"
    defs = ('<linearGradient id="fl" gradientUnits="userSpaceOnUse" x1="0" x2="160" y1="0" y2="0">'
            f'<stop offset="0" stop-color="{ACCENT}" stop-opacity="0"/><stop offset=".5" stop-color="{ACCENT}"/>'
            f'<stop offset="1" stop-color="{ACCENT}" stop-opacity="0"/>'
            f'<animateTransform attributeName="gradientTransform" type="translate" dur="6s" repeatCount="indefinite" '
            f'values="-200 0;1400 0"/></linearGradient>')
    body = [f'<rect width="{W}" height="{H}" rx="18" fill="{BG}"/>',
            f'<path d="M60 30H1140" stroke="#30363d" stroke-width="1"/>',
            f'<path d="M60 30H1140" stroke="url(#fl)" stroke-width="1.6"/>',
            f'<path fill="{DIM}" d="{mono.path_d(text, 16, W / 2, 70, anchor="middle", tracking=.02, precision=1)}"/>']
    return svg_doc(W, H, "".join(body), defs=defs, title="footer", desc=text)


def build():
    mono = Font("geist-mono-latin-400-normal.woff2")
    for i, (label, kind) in enumerate(BUTTONS):
        p, n = write(f"btn-{label}.svg", button(mono, label, kind, 0.8 + i * 0.55))
        print(p, n)
    p, n = write("footer.svg", footer(mono))
    print(p, n)


if __name__ == "__main__":
    build()
