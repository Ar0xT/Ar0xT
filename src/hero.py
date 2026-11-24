"""Hero banner. A slow fluid flows left to right, then an invisible obstacle appears and every
streamline bends around it. The obstacle is the greeting, so the text shows up as the place
the fluid refuses to go.

The flow is real potential flow. We solve the Laplace equation for the stream function on a
grid with the letters as solid bodies, pick body constants so no body carries circulation,
and the contour lines of the result are the streamlines.
"""
import json
import math
import os
import sys

import numpy as np
from scipy import ndimage
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import splu
from skimage.draw import polygon as draw_polygon
from skimage.measure import find_contours

from svgkit import (ACCENT, ACCENT2, BG, DIM, FAINT, INK, HOT, Font, abs_poly_d, fmt, hold_then, rdp, rel_poly_d,
                    resample, svg_doc, write)

W, H = 1200, 400
FLOW_H = 400          # streamlines live in the whole banner
PAD = 260             # extra fluid left and right so the far field is really uniform
CELL = 2.0            # grid step in px
GAP = 7.0             # clearance between a letter and the closest streamline
SPACING = 7.0         # distance between streamlines far upstream

TEXT = "hi, i’m ariunbat"
TEXT_SIZE = 112
BASELINE = 232

REVEAL_AT = 0.7       # when the obstacle starts to appear
REVEAL_DUR = 3.0      # how long the streamlines take to bend around it
LOOP = 16.0


def letter_mask(font, gx0, gy0, nx, ny, scale=1.0):
    """Rasterize the greeting on the solver grid. Nonzero winding, since these outlines come
    from a variable font and overlap each other. With scale below one every letter shrinks
    around its own centre, which gives the in between states of the reveal."""
    wind = np.zeros((ny, nx), dtype=np.int32)
    for contours in font.glyph_polygons(TEXT, TEXT_SIZE, x=W / 2, y=BASELINE, anchor="middle", step=1.5):
        allp = np.concatenate([np.asarray(c) for c in contours])
        ctr = (allp.min(0) + allp.max(0)) / 2
        for poly in contours:
            p = ctr + (np.asarray(poly) - ctr) * scale
            area = 0.5 * np.sum(p[:-1, 0] * p[1:, 1] - p[1:, 0] * p[:-1, 1])
            rr, cc = draw_polygon((p[:, 1] - gy0) / CELL, (p[:, 0] - gx0) / CELL, shape=wind.shape)
            wind[rr, cc] += 1 if area > 0 else -1
    return wind != 0


def solve_flow(body):
    """Stream function on the grid. Top and bottom rows are walls, left and right columns far field."""
    ny, nx = body.shape
    ys = (np.arange(ny) * CELL)[:, None] * np.ones((1, nx))
    fixed = body.copy()
    fixed[0, :] = fixed[-1, :] = True
    fixed[:, 0] = fixed[:, -1] = True
    labels, nb = ndimage.label(body)

    idx = -np.ones((ny, nx), dtype=np.int64)
    free = ~fixed
    idx[free] = np.arange(free.sum())
    n = int(free.sum())

    rows, cols, vals = [], [], []
    fi, fj = np.nonzero(free)
    me = idx[fi, fj]
    rows.append(me); cols.append(me); vals.append(np.full(n, 4.0))
    nbrs = []
    for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        ni, nj = fi + di, fj + dj
        other = idx[ni, nj]
        ok = other >= 0
        rows.append(me[ok]); cols.append(other[ok]); vals.append(-np.ones(ok.sum()))
        nbrs.append((ni, nj, ok))
    A = coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)).tocsc()
    lu = splu(A)

    def solve(boundary):
        b = np.zeros(n)
        for ni, nj, ok in nbrs:
            ext = ~ok
            np.add.at(b, me[ext], boundary[ni[ext], nj[ext]])
        out = boundary.copy()
        out[free] = lu.solve(b)
        return out

    # uniform part, bodies held at zero
    bU = np.where(body, 0.0, ys)
    psi_u = solve(bU)
    basis = []
    for k in range(1, nb + 1):
        bk = np.where(labels == k, 1.0, 0.0)
        basis.append(solve(bk))

    def circulation(field):
        # sum of (fluid minus body) across every fluid face of each body
        g = np.zeros(nb + 1)
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            sh_lab = np.roll(np.roll(labels, -di, 0), -dj, 1)
            sh_val = np.roll(np.roll(field, -di, 0), -dj, 1)
            face = (labels == 0) & (sh_lab > 0) & free
            np.add.at(g, sh_lab[face], (field - sh_val)[face])
        return g[1:]

    G = np.stack([circulation(f) for f in basis], axis=1)
    rhs = -circulation(psi_u)
    c = np.linalg.solve(G, rhs)
    psi = psi_u + sum(ck * f for ck, f in zip(c, basis))
    return psi, labels, c


def streamlines(psi, gx0, gy0, levels):
    """Contour of psi at each level that runs all the way across. Keyed by level."""
    lines = {}
    for lev in levels:
        pieces = find_contours(psi, lev)
        best = None
        for p in pieces:
            xs = p[:, 1] * CELL + gx0
            span = xs.max() - xs.min()
            if best is None or span > best[0]:
                best = (span, p)
        if best is None or best[0] < (W + PAD):
            continue
        p = best[1]
        pts = np.stack([p[:, 1] * CELL + gx0, p[:, 0] * CELL + gy0], axis=1)
        if pts[0, 0] > pts[-1, 0]:
            pts = pts[::-1]
        keep = (pts[:, 0] > -60) & (pts[:, 0] < W + 60)
        pts = pts[keep]
        # light smoothing to kill grid wobble
        k = np.array([1, 2, 3, 2, 1], float)
        k /= k.sum()
        if len(pts) > 10:
            pts = np.stack([np.convolve(np.pad(pts[:, i], 2, mode="edge"), k, mode="valid") for i in range(2)], axis=1)
        lines[round(float(lev), 3)] = pts
    return lines


SCALES = [0.4, 0.72, 1.0]


def build():
    font = Font("unbounded-latin-800-normal.woff2")
    mono = Font("geist-mono-latin-400-normal.woff2")

    gx0, gy0 = -PAD, 0.0
    nx = int((W + 2 * PAD) / CELL) + 1
    ny = int(FLOW_H / CELL) + 1

    # final state first, its body constants decide which levels to nudge
    fields = {}
    consts = None
    for sc in sorted(SCALES, reverse=True):
        glyphs = letter_mask(font, gx0, gy0, nx, ny, sc)
        body = ndimage.binary_dilation(glyphs, iterations=int(GAP / CELL))
        body = ndimage.binary_fill_holes(body)
        psi, labels, c = solve_flow(body)
        fields[sc] = psi
        if consts is None:
            consts = c
    levels = np.arange(SPACING / 2, FLOW_H - 2, SPACING)
    # nothing hugging the top and bottom edge, so no line ever pokes past the rounded corners
    levels = levels[(levels > 10) & (levels < FLOW_H - 10)]
    for c in consts:
        levels = np.where(np.abs(levels - c) < 0.6, levels + 1.2, levels)
    per_state = {sc: streamlines(psi, gx0, gy0, levels) for sc, psi in fields.items()}
    lines = []
    for lev in levels:
        key = round(float(lev), 3)
        if all(key in per_state[sc] for sc in SCALES):
            lines.append((float(lev), [per_state[sc][key] for sc in SCALES]))
    print(f"lines {len(lines)} of {len(levels)}", file=sys.stderr)
    return font, mono, lines


def kt(*secs):
    return ";".join(fmt(s / LOOP, 4) for s in secs)


MATH_FONT = "/usr/share/texmf/fonts/opentype/public/lm-math/latinmodern-math.otf"


def formula(x, y, size, fill):
    """The Laplace equation in a real math face, as outlines. Latin Modern Math comes with TeX
    and isn't shipped here, so the outlines get cached in data/ the first time."""
    cache = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "formula.json")
    key = f"{x},{y},{size}"
    saved = json.load(open(cache)) if os.path.exists(cache) else {}
    if key not in saved:
        m = Font(MATH_FONT)
        parts = []
        parts.append(m.path_d("\u2207", size, x, y, precision=1))
        x += m.width("\u2207", size) + 1
        parts.append(m.path_d("2", size * 0.68, x, y - size * 0.42, precision=1))
        x += m.width("2", size * 0.68) + 1.5
        parts.append(m.path_d("\U0001D713", size, x, y, precision=1))
        x += m.width("\U0001D713", size) + size * 0.32
        parts.append(m.path_d("=", size, x, y, precision=1))
        x += m.width("=", size) + size * 0.32
        parts.append(m.path_d("0", size, x, y, precision=1))
        x += m.width("0", size)
        saved[key] = {"d": "".join(parts), "end": x}
        json.dump(saved, open(cache, "w"))
    return f'<path fill="{fill}" d="{saved[key]["d"]}"/>', saved[key]["end"]


def sample_states(lev, states, lead, eps=0.7):
    """Put every state of one streamline on the same set of points so they morph cleanly.
    Returns a list of point arrays, straight line first."""
    mono_ok = all(np.all(np.diff(p[:, 0]) > -0.3) for p in states)
    if mono_ok:
        xs = np.concatenate([rdp(p, eps)[:, 0] for p in states])
        xs = np.sort(xs)
        keep = np.concatenate([[True], np.diff(xs) > 0.8])
        xs = xs[keep]
        out = [np.stack([xs, np.full(len(xs), lev)], axis=1)]
        for p in states:
            px = np.maximum.accumulate(p[:, 0]) + np.arange(len(p)) * 1e-6
            out.append(np.stack([xs, np.interp(xs, px, p[:, 1])], axis=1))
    else:
        n = int(max(len(rdp(p, eps)) for p in states) * 1.3) + 2
        out = []
        for p in states:
            out.append(resample(p, n))
        x0, x1 = out[-1][0, 0], out[-1][-1, 0]
        out.insert(0, np.stack([np.linspace(x0, x1, n), np.full(n, lev)], axis=1))
    # lead in, so dash patterns on neighbouring lines never line up
    res = []
    for p in out:
        res.append(np.vstack([[p[0, 0] - lead, p[0, 1]], p]))
    return res, mono_ok


def render():
    font, mono, lines = build()
    rng = np.random.default_rng(7)
    cy_mid = BASELINE - TEXT_SIZE * 0.3

    # sort lines into groups. timing band depends on how far the line is from the text,
    # so the bend spreads outward like a ripple. speed varies inside each band.
    NB, NS = 4, 3
    dists = np.array([abs(lev - cy_mid) for lev, _ in lines])
    edges = np.quantile(dists, np.linspace(0, 1, NB + 1)[1:-1])
    groups = {}
    nonmono = 0
    for i, (lev, states) in enumerate(lines):
        pts, ok = sample_states(lev, states, rng.uniform(0, 140))
        nonmono += not ok
        band = int(np.searchsorted(edges, dists[i]))
        spd = i % NS
        groups.setdefault((band, spd), []).append([rel_poly_d(p, 1) for p in pts])
    print(f"non monotonic lines {nonmono}", file=sys.stderr)

    defs = []
    keys = sorted(groups)
    for gi, key in enumerate(keys):
        band, spd = key
        g = groups[key]
        S, F1, F2, B = ("".join(line[j] for line in g) for j in range(4))
        a0 = REVEAL_AT + 0.16 * band
        total = a0 + REVEAL_DUR
        # resting value is the bent state, so anything that can't animate still shows the text
        # plays once on load and freezes, so after the intro nothing but the particles moves
        defs.append(
            f'<path id="g{gi}" d="{B}">'
            f'<animate attributeName="d" begin="0s" dur="{fmt(total, 3)}s" fill="freeze" calcMode="spline" '
            f'keyTimes="0;{fmt(a0 / total, 4)};{fmt((a0 + .34 * REVEAL_DUR) / total, 4)};{fmt((a0 + .64 * REVEAL_DUR) / total, 4)};1" '
            f'keySplines="0 0 1 1;.55 0 1 .6;0 0 1 1;0 .4 .35 1" '
            f'values="{S};{S};{F1};{F2};{B}"/></path>')

    cx, cy = W / 2, cy_mid

    def radial(id_, stops, r=600, sy=0.45):
        s = "".join(f'<stop offset="{o}" stop-color="{c}" stop-opacity="{a}"/>' for o, c, a in stops)
        return (f'<radialGradient id="{id_}" gradientUnits="userSpaceOnUse" cx="{fmt(cx)}" cy="{fmt(cy)}" r="{r}" '
                f'gradientTransform="translate({fmt(cx)} {fmt(cy)}) scale(1 {sy}) translate({fmt(-cx)} {fmt(-cy)})">{s}</radialGradient>')

    defs.append(radial("glow", [(0, "#7cf0ff", .17), (.6, "#7c9cff", .05), (1, "#7c9cff", 0)], 540, .38))
    # dark edges so the eye stays in the middle
    defs.append('<linearGradient id="vx" x1="0" x2="1"><stop offset="0" stop-color="#0d1117"/>'
                '<stop offset=".09" stop-color="#0d1117" stop-opacity="0"/><stop offset=".91" stop-color="#0d1117" stop-opacity="0"/>'
                '<stop offset="1" stop-color="#0d1117"/></linearGradient>')
    defs.append('<linearGradient id="vy" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#0d1117" stop-opacity=".85"/>'
                '<stop offset=".12" stop-color="#0d1117" stop-opacity="0"/><stop offset=".8" stop-color="#0d1117" stop-opacity="0"/>'
                '<stop offset="1" stop-color="#0d1117" stop-opacity=".95"/></linearGradient>')

    speeds = [58, 74, 66]
    tails = [(30, 90), (22, 70), (38, 110)]
    # solid colours per distance band. gradient strokes looked the same but cost a third
    # of the frame rate, since the whole image gets repainted every frame
    css = ["@media (prefers-reduced-motion:reduce){.t,.h{animation:none!important}}",
           ".b{fill:none;stroke-width:1}",
           ".t{fill:none;stroke-width:1.3;stroke-linecap:round}",
           ".h{fill:none;stroke-width:2.2;stroke-linecap:round}"]
    base_c = [("#cfe6ff", .36), ("#b4cdf6", .27), ("#9fb2e2", .19), ("#8a93c9", .13)]
    tail_c = [("#a6f3ff", .58), ("#8fe4ff", .44), ("#9cb6ff", .32), ("#ae9bff", .22)]
    head_c = [("#ffffff", 1), ("#f0fcff", .92), ("#dfe8ff", .78), ("#d2c6ff", .62)]
    for bnd in range(NB):
        css.append(f".B{bnd}{{stroke:{base_c[bnd][0]};stroke-opacity:{base_c[bnd][1]}}}"
                   f".T{bnd}{{stroke:{tail_c[bnd][0]};stroke-opacity:{tail_c[bnd][1]}}}"
                   f".H{bnd}{{stroke:{head_c[bnd][0]};stroke-opacity:{head_c[bnd][1]}}}")
    for s in range(NS):
        on, off = tails[s]
        per = on + off
        dur = per / speeds[s]
        head = on - 0.5
        css.append(f".t{s}{{stroke-dasharray:{on} {off};animation:t{s} {fmt(dur, 3)}s linear infinite}}"
                   f"@keyframes t{s}{{from{{stroke-dashoffset:0}}to{{stroke-dashoffset:-{per}}}}}"
                   f".h{s}{{stroke-dasharray:.5 {per - .5};animation:h{s} {fmt(dur, 3)}s linear infinite}}"
                   f"@keyframes h{s}{{from{{stroke-dashoffset:{-head}}}to{{stroke-dashoffset:{-head - per}}}}}")

    body = [f'<rect width="{W}" height="{H}" rx="18" fill="{BG}"/>']
    # soft light behind the text that comes up with it, then breathes
    gl_on = REVEAL_AT + 0.8
    body.append(f'<rect width="{W}" height="{H}" fill="url(#glow)">'
                f'{hold_then("opacity", 0, 1, gl_on, 2.2)}'
                f'<animate attributeName="opacity" begin="{gl_on + 2.2}s" dur="7s" values="1;.55;1" '
                f'calcMode="spline" keyTimes="0;.5;1" keySplines=".45 0 .55 1;.45 0 .55 1" repeatCount="indefinite"/></rect>')
    body.append('<g>')
    for gi, (band, spd) in enumerate(keys):
        body.append(f'<use href="#g{gi}" class="b B{band}"/>')
    for gi, (band, spd) in enumerate(keys):
        body.append(f'<use href="#g{gi}" class="t t{spd} T{band}"/>')
    for gi, (band, spd) in enumerate(keys):
        # bright heads on one speed group only. dashing a long path is the expensive part of
        # every frame, and a third of the heads reads just as alive
        if spd == 0:
            body.append(f'<use href="#g{gi}" class="h h{spd} H{band}"/>')
    body.append("</g>")
    body.append(f'<rect width="{W}" height="{H}" rx="18" fill="url(#vx)"/>')
    body.append(f'<rect width="{W}" height="{H}" rx="18" fill="url(#vy)"/>')

    # the letters, traced in as the flow makes room for them
    gl = font.glyph_paths(TEXT, TEXT_SIZE, x=W / 2, y=BASELINE, anchor="middle")
    letters = []
    vis = [(n, d) for n, d, _ in gl if d]
    for i, (name, d) in enumerate(vis):
        t0 = REVEAL_AT + 0.55 + 0.06 * i
        letters.append(
            f'<path d="{d}" pathLength="1" fill="url(#lf)" stroke="#e9f6ff" stroke-opacity=".85" '
            f'stroke-width="1.1" stroke-dasharray="1 1">'
            f'{hold_then("stroke-dashoffset", 1, 0, t0, 1.7, spline=".5 0 .2 1")}'
            f'{hold_then("fill-opacity", 0, 1, t0 + 0.9, 1.3)}'
            f'</path>')
    defs.append('<linearGradient id="lf" x1="0" y1="0" x2="0" y2="1">'
                '<stop offset="0" stop-color="#d6f3ff" stop-opacity=".2"/>'
                '<stop offset="1" stop-color="#d6f3ff" stop-opacity=".03"/></linearGradient>')
    body.append("<g>" + "".join(letters) + "</g>")

    # a slow glint that runs across the letters every few seconds
    all_d = font.path_d(TEXT, TEXT_SIZE, x=W / 2, y=BASELINE, anchor="middle")
    defs.append('<linearGradient id="shine" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="260" y2="120">'
                '<stop offset="0" stop-color="#fff" stop-opacity="0"/>'
                '<stop offset=".5" stop-color="#fff" stop-opacity=".34"/>'
                '<stop offset="1" stop-color="#fff" stop-opacity="0"/>'
                '<animateTransform attributeName="gradientTransform" type="translate" begin="4.6s" dur="8s" '
                'repeatCount="indefinite" values="-420 0;1300 0;1300 0" keyTimes="0;.3;1"/></linearGradient>')
    body.append(f'<path d="{all_d}" fill="url(#shine)" opacity="0">'
                f'<set attributeName="opacity" to="1" begin="4.5s"/></path>')

    # quiet caption, like a figure in a paper
    cap_y = H - 24
    fx, end = formula(32, cap_y, 18, DIM)
    body.append(f'<path fill="{DIM}" opacity=".9" d="{mono.path_d("fig. 1", 14.5, 32, cap_y - 30, tracking=0.04, precision=1)}"/>')
    body.append(fx)
    body.append(f'<path fill="{DIM}" opacity=".9" d="{mono.path_d("potential flow past a greeting", 14.5, W - 32, cap_y, anchor="end", tracking=0.02, precision=1)}"/>')

    svg = svg_doc(W, H, "".join(body), defs="".join(defs), style="".join(css),
                  title="hi, i'm ariunbat", desc="streamlines of a fluid bending around the greeting")
    p, n = write("hero.svg", svg)
    print(p, f"{n/1024:.0f} KB")


if __name__ == "__main__":
    render()
