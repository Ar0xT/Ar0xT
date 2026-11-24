"""Figure 3. A dotted earth turning in real 3D, St. Petersburg marked.

There is no 3D engine here. Every latitude ring of land dots is a flat circle, squashed into
an ellipse by the camera tilt and spun with a single rotate animation. Spinning a ring and
then squashing it is exactly what an orthographic camera does to a ring on a turning sphere.
The far side of each ring is cut off with a clip line, and that line happens to be straight,
which is the whole trick.
"""
import json
import math
import os

from svgkit import BG, DIM, INK, ACCENT, HOT, Font, fmt, svg_doc, write

W, H = 1200, 440
CX, CY, R = 600, 214, 170
TILT = math.radians(24)     # camera looks down on the north a little
PERIOD = 46.0               # seconds per full turn
FACE_AT = 4.5               # St. Petersburg crosses the middle at this time on load
SPB = (59.94, 30.31)
HERE = os.path.dirname(os.path.abspath(__file__))


def ring_geometry(lat):
    h = R * math.sin(math.radians(lat))
    rho = R * math.cos(math.radians(lat))
    cy = CY - h * math.cos(TILT)
    cut = -h * math.tan(TILT)          # in the ring's own flat coordinates, visible below this line
    return h, rho, cy, cut


def build():
    mono = Font("geist-mono-latin-400-normal.woff2")
    data = json.load(open(os.path.join(HERE, "data", "land_dots.json")))
    s = math.sin(TILT)
    lam0 = -SPB[1] - 360.0 * FACE_AT / PERIOD   # longitude offset so SPb faces us at FACE_AT

    defs, body = [], [f'<rect width="{W}" height="{H}" rx="18" fill="{BG}"/>']
    css = [".d{fill:none;stroke-linecap:round;vector-effect:non-scaling-stroke}"]

    # atmosphere and the dark body of the planet
    defs.append(f'<radialGradient id="atm" cx="{CX}" cy="{CY}" r="{R * 1.32}" gradientUnits="userSpaceOnUse">'
                f'<stop offset=".74" stop-color="{ACCENT}" stop-opacity="0"/>'
                f'<stop offset=".765" stop-color="{ACCENT}" stop-opacity=".2"/>'
                f'<stop offset=".84" stop-color="#6d7cff" stop-opacity=".07"/>'
                f'<stop offset="1" stop-color="#6d7cff" stop-opacity="0"/></radialGradient>')
    defs.append(f'<radialGradient id="sea" cx="{CX - R * .3}" cy="{CY - R * .35}" r="{R * 1.25}" gradientUnits="userSpaceOnUse">'
                f'<stop offset="0" stop-color="#16243a"/><stop offset=".7" stop-color="#0f1626"/>'
                f'<stop offset="1" stop-color="#0b1019"/></radialGradient>')
    defs.append(f'<radialGradient id="shade" cx="{CX}" cy="{CY}" r="{R}" gradientUnits="userSpaceOnUse">'
                f'<stop offset=".45" stop-color="{BG}" stop-opacity="0"/>'
                f'<stop offset=".86" stop-color="{BG}" stop-opacity=".45"/>'
                f'<stop offset="1" stop-color="{BG}" stop-opacity=".85"/></radialGradient>')
    defs.append(f'<radialGradient id="spec" cx="{CX - R * .38}" cy="{CY - R * .42}" r="{R * .9}" gradientUnits="userSpaceOnUse">'
                f'<stop offset="0" stop-color="#bfefff" stop-opacity=".10"/>'
                f'<stop offset="1" stop-color="#bfefff" stop-opacity="0"/></radialGradient>')

    body.append(stars())
    orbit_back, orbit_front = orbits()
    body.append(orbit_back)
    body.append(f'<circle cx="{CX}" cy="{CY}" r="{R * 1.32}" fill="url(#atm)"/>')
    body.append(f'<circle cx="{CX}" cy="{CY}" r="{R}" fill="url(#sea)"/>')

    # latitude rings, front halves only, spinning together
    spin = (f'<animateTransform attributeName="transform" type="rotate" from="0" to="-360" '
            f'dur="{PERIOD}s" repeatCount="indefinite"/>')
    rings_svg = []
    for k, (lat, n, lons) in enumerate(data["rings"]):
        h, rho, cy, cut = ring_geometry(lat)
        if cut > rho:
            continue                       # entirely on the far side
        pts = []
        for lon in lons:
            a = math.radians(lon + lam0)
            u, v = rho * math.sin(a), rho * math.cos(a)
            pts.append(f"M{fmt(u)} {fmt(v)}h.01")
        clip = ""
        if cut > -rho:
            cid = f"k{k}"
            defs.append(f'<clipPath id="{cid}"><rect x="{fmt(-rho - 4)}" y="{fmt(cut)}" width="{fmt(2 * rho + 8)}" '
                        f'height="{fmt(rho - cut + 4)}"/></clipPath>')
            clip = f' clip-path="url(#{cid})"'
        # brighter toward the equator side facing us, tiny bit of variety by latitude
        col = "#dff6ff" if abs(lat) < 66 else "#b8c7e0"
        rings_svg.append(f'<g transform="translate({CX} {fmt(cy)}) scale(1 {fmt(s, 4)})"{clip}>'
                         f'<g>{spin}<path class="d" stroke="{col}" stroke-width="2.3" d="{"".join(pts)}"/></g></g>')
    body.append("<g>" + "".join(rings_svg) + "</g>")

    # St. Petersburg, riding its own ring
    h, rho, cy, cut = ring_geometry(SPB[0])
    a = math.radians(SPB[1] + lam0)
    u, v = rho * math.sin(a), rho * math.cos(a)
    body.append(f'<g transform="translate({CX} {fmt(cy)}) scale(1 {fmt(s, 4)})" clip-path="url(#spbclip)">'
                f'<g>{spin}'
                f'<path class="d" stroke="{HOT}" stroke-width="7" d="M{fmt(u)} {fmt(v)}h.01"/>'
                f'<path class="d" stroke="#fff3e8" stroke-width="2.6" d="M{fmt(u)} {fmt(v)}h.01"/>'
                f'<circle cx="{fmt(u)}" cy="{fmt(v)}" r="6" fill="none" stroke="{HOT}" stroke-width="1.6" style="vector-effect:non-scaling-stroke">'
                f'<animate attributeName="r" dur="2s" values="5;26" repeatCount="indefinite"/>'
                f'<animate attributeName="stroke-opacity" dur="2s" values="1;0" repeatCount="indefinite"/></circle>'
                f'</g></g>')
    defs.append(f'<clipPath id="spbclip"><rect x="{fmt(-rho - 40)}" y="{fmt(cut)}" width="{fmt(2 * rho + 80)}" height="{fmt(rho - cut + 40)}"/></clipPath>')

    # depth shading and a soft highlight on top of the dots
    body.append(f'<circle cx="{CX}" cy="{CY}" r="{R + .5}" fill="url(#shade)"/>')
    body.append(f'<circle cx="{CX}" cy="{CY}" r="{R}" fill="url(#spec)"/>')
    body.append(f'<circle cx="{CX}" cy="{CY}" r="{R}" fill="none" stroke="{ACCENT}" stroke-opacity=".18" stroke-width="1"/>')
    body.append(orbit_front)

    # label that follows the marker while it is on our side
    body.append(spb_label(mono, rho, cy, lam0))

    cap_y = H - 22
    body.append(f'<path fill="{DIM}" opacity=".9" d="{mono.path_d("fig. 3", 14.5, 34, cap_y, tracking=0.04, precision=1)}"/>')
    info = "orthographic projection · 1,857 land points · one rotate per latitude"
    body.append(f'<path fill="{DIM}" opacity=".9" d="{mono.path_d(info, 14.5, W - 34, cap_y, anchor="end", tracking=0.02, precision=1)}"/>')

    svg = svg_doc(W, H, "".join(body), defs="".join(defs), style="".join(css),
                  title="st. petersburg on a turning globe", desc="dotted earth rotating, st. petersburg highlighted")
    p, n = write("globe.svg", svg)
    print(p, f"{n / 1024:.0f} KB")


def spb_label(mono, rho, cy, lam0):
    """Text that rides along with the marker. Its screen path is the projected ring, sampled
    finely so the motion keeps the same pace as the spin."""
    s = math.sin(TILT)
    h = R * math.sin(math.radians(SPB[0]))
    steps = 180
    pts, vis = [], []
    for i in range(steps + 1):
        t = i / steps * PERIOD
        a = math.radians(SPB[1] + lam0 + 360.0 * t / PERIOD)
        x = CX + rho * math.sin(a)
        y = cy + rho * s * math.cos(a)
        z = h * math.sin(TILT) + rho * math.cos(TILT) * math.cos(a)
        pts.append((x, y))
        vis.append(z / R)
    # fade the label in once the marker is well on our side
    keys, ops = [], []
    for i, z in enumerate(vis):
        keys.append(fmt(i / steps, 4))
        ops.append("1" if z > 0.45 else ("0" if z < 0.3 else fmt((z - 0.3) / 0.15, 2)))
    label1 = "st. petersburg"
    label2 = "59.94°n 30.31°e"
    lx, ly = 34, -30
    t1 = mono.path_d(label1, 18, lx + 8, ly, precision=1)
    t2 = mono.path_d(label2, 14, lx + 8, ly + 20, precision=1)
    w1 = mono.width(label1, 18)
    # motion is written relative to the first point, and the group already sits there, so
    # a renderer that ignores animation still puts the label in the right place
    x0, y0 = pts[0]
    vals = ";".join(f"{fmt(x - x0)},{fmt(y - y0)}" for x, y in pts)
    return (f'<g transform="translate({fmt(x0)} {fmt(y0)})"><animateMotion dur="{PERIOD}s" repeatCount="indefinite" calcMode="linear" values="{vals}"/>'
            f'<g><animate attributeName="opacity" dur="{PERIOD}s" repeatCount="indefinite" calcMode="linear" '
            f'keyTimes="{";".join(keys)}" values="{";".join(ops)}"/>'
            f'<rect x="{lx}" y="{ly - 20}" width="{fmt(w1 + 18)}" height="48" rx="7" fill="{BG}" fill-opacity=".74"/>'
            f'<path d="M5 -5L{lx} {ly + 6}h{fmt(w1 + 16)}" fill="none" stroke="{HOT}" stroke-opacity=".75" stroke-width="1"/>'
            f'<path fill="{INK}" d="{t1}"/><path fill="{DIM}" d="{t2}"/></g></g>')


def stars(seed=3):
    """Sparse background stars, a few of them twinkling."""
    import random
    rnd = random.Random(seed)
    still, tw = [], []
    for i in range(110):
        x, y = rnd.uniform(16, W - 16), rnd.uniform(14, H - 44)
        if (x - CX) ** 2 + (y - CY) ** 2 < (R * 1.35) ** 2:
            continue
        r = rnd.choice([.6, .7, .8, 1.0, 1.3])
        if i % 9 == 0:
            d = rnd.uniform(2.5, 5.5)
            tw.append(f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="{r + .3}" fill="#dbe8ff">'
                      f'<animate attributeName="opacity" dur="{fmt(d, 2)}s" begin="-{fmt(rnd.uniform(0, d), 2)}s" '
                      f'values=".15;.9;.15" repeatCount="indefinite"/></circle>')
        else:
            still.append(f"M{fmt(x)} {fmt(y)}h.01")
    return (f'<path d="{"".join(still)}" stroke="#c9d6ee" stroke-opacity=".35" stroke-width="1.6" '
            f'stroke-linecap="round"/>' + "".join(tw))


def orbits():
    """Two satellites on wide tilted orbits. The half of each orbit behind the planet is drawn
    before it, the other half after, and each satellite switches layers as it goes round."""
    specs = [
        (R * 2.55, R * 0.30, -9.0, 15.0, 0.0, ACCENT),
        (R * 2.2, R * 0.42, 11.0, 23.0, 0.37, "#b48cff"),
    ]
    back, front = [], []
    for i, (rx, ry, rot, per, phase, col) in enumerate(specs):
        tf = f"translate({CX} {CY}) rotate({rot})"
        # back half is the top half of the ellipse, front half the bottom
        back.append(f'<path transform="{tf}" d="M{-rx} 0A{fmt(rx)} {fmt(ry)} 0 0 1 {fmt(rx)} 0" fill="none" '
                    f'stroke="{col}" stroke-opacity=".14" stroke-width="1" stroke-dasharray="2 5"/>')
        front.append(f'<path transform="{tf}" d="M{fmt(rx)} 0A{fmt(rx)} {fmt(ry)} 0 0 1 {fmt(-rx)} 0" fill="none" '
                     f'stroke="{col}" stroke-opacity=".3" stroke-width="1"/>')
        n = 120
        vals, opb, opf, keys = [], [], [], []
        for k in range(n + 1):
            ang = 2 * math.pi * (k / n + phase)
            x, y = rx * math.cos(ang), ry * math.sin(ang)
            if k == 0:
                x0, y0 = x, y
            vals.append(f"{fmt(x - x0)},{fmt(y - y0)}")
            keys.append(fmt(k / n, 4))
            on_front = y > 0
            opf.append("1" if on_front else "0")
            opb.append("0" if on_front else ".55")
        motion = f'<animateMotion dur="{per}s" repeatCount="indefinite" calcMode="linear" values="{";".join(vals)}"/>'
        for layer, ops in ((back, opb), (front, opf)):
            layer.append(f'<g transform="{tf}"><g transform="translate({fmt(x0)} {fmt(y0)})" opacity="{ops[0]}">{motion}'
                         f'<animate attributeName="opacity" dur="{per}s" repeatCount="indefinite" calcMode="discrete" '
                         f'keyTimes="{";".join(keys)}" values="{";".join(ops)}"/>'
                         f'<circle r="9" fill="{col}" fill-opacity=".14"/><circle r="2.6" fill="#ffffff"/></g></g>')
    return "".join(back), "".join(front)


if __name__ == "__main__":
    build()
