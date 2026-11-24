"""Figure 2. A maze with a few loops in it, searched from both ends at once. Two breadth first
frontiers grow toward each other, and the moment they touch, the shortest path lights up
from the meeting point outward. Then everything fades and it starts again."""
import random
from collections import deque

import numpy as np

from svgkit import BG, DIM, INK, Font, fmt, svg_doc, write

W, H = 1200, 408
NX, NY = 96, 27
P, C = 12, 8              # cell pitch and corridor width
OX, OY = (W - NX * P) // 2, 22
LOOP = 12.0
FLOOD_AT, FLOOD_DUR = 0.6, 5.2
PATH_DUR = 1.4
FADE_AT = 10.2
EXTRA_PASSAGES = 0.07     # share of leftover walls knocked down to create loops


def make_maze(seed=5):
    rnd = random.Random(seed)
    parent = list(range(NX * NY))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    walls = []
    for y in range(NY):
        for x in range(NX):
            if x + 1 < NX:
                walls.append(((x, y), (x + 1, y)))
            if y + 1 < NY:
                walls.append(((x, y), (x, y + 1)))
    rnd.shuffle(walls)
    open_ = set()
    left = []
    for a, b in walls:
        ra, rb = find(a[1] * NX + a[0]), find(b[1] * NX + b[0])
        if ra != rb:
            parent[ra] = rb
            open_.add((a, b))
        else:
            left.append((a, b))
    for w in rnd.sample(left, int(len(left) * EXTRA_PASSAGES)):
        open_.add(w)
    adj = {(x, y): [] for y in range(NY) for x in range(NX)}
    for a, b in open_:
        adj[a].append(b)
        adj[b].append(a)
    return adj, open_


def bfs(adj, src):
    dist = {src: 0}
    prev = {src: None}
    q = deque([src])
    while q:
        u = q.popleft()
        for v in adj[u]:
            if v not in dist:
                dist[v] = dist[u] + 1
                prev[v] = u
                q.append(v)
    return dist, prev


def lerp_hex(stops, t):
    t = min(1.0, max(0.0, t))
    for i in range(len(stops) - 1):
        a, b = stops[i], stops[i + 1]
        if t <= b[0]:
            u = (t - a[0]) / (b[0] - a[0])
            ca = np.array([int(a[1][j:j + 2], 16) for j in (1, 3, 5)], float)
            cb = np.array([int(b[1][j:j + 2], 16) for j in (1, 3, 5)], float)
            # mix in linear light so the middle of the ramp doesn't go muddy
            la, lb = (ca / 255) ** 2.2, (cb / 255) ** 2.2
            c = ((la + (lb - la) * u) ** (1 / 2.2)) * 255
            return "#" + "".join(f"{int(round(v)):02x}" for v in c)
    return stops[-1][1]


LEFT_RAMP = [(0, "#c8fbff"), (.35, "#7cf0ff"), (.7, "#4f8dff"), (1, "#6d5cff")]
RIGHT_RAMP = [(0, "#fff0c2"), (.35, "#ffb35c"), (.7, "#ff6a6a"), (1, "#ff4fa8")]


def cell_xy(c):
    return OX + c[0] * P + (P - C) / 2, OY + c[1] * P + (P - C) / 2


def square(c):
    x, y = cell_xy(c)
    return f"M{fmt(x)} {fmt(y)}h{C}v{C}h-{C}z"


def bridge(a, b):
    """Little rectangle filling the wall gap between two connected cells."""
    (ax, ay), (bx, by) = cell_xy(a), cell_xy(b)
    g = P - C
    if a[1] == b[1]:
        x = max(ax, bx) - g
        return f"M{fmt(x)} {fmt(ay)}h{g}v{C}h-{g}z"
    y = max(ay, by) - g
    return f"M{fmt(ax)} {fmt(y)}h{C}v{g}h-{C}z"


def rect_of_square(c):
    x, y = cell_xy(c)
    return (x, y, x + C, y + C)


def rect_of_bridge(a, b):
    (ax, ay), (bx, by) = cell_xy(a), cell_xy(b)
    g = P - C
    if a[1] == b[1]:
        x = max(ax, bx) - g
        return (x, ay, x + g, ay + C)
    y = max(ay, by) - g
    return (ax, y, ax + C, y + g)


def union_d(rects):
    """Merge a pile of touching rectangles into a few outlines. Fewer edges means less work
    for the renderer on every single frame."""
    from shapely.geometry import box
    from shapely.ops import unary_union
    shape = unary_union([box(*r) for r in rects])
    polys = getattr(shape, "geoms", [shape])
    out = []
    for poly in polys:
        for ring in [poly.exterior, *poly.interiors]:
            pts = [(int(round(x)), int(round(y))) for x, y in ring.coords][:-1]
            # drop points that sit in the middle of a straight edge
            clean = []
            n = len(pts)
            for i in range(n):
                p0, p1, p2 = pts[i - 1], pts[i], pts[(i + 1) % n]
                if (p0[0] == p1[0] == p2[0]) or (p0[1] == p1[1] == p2[1]):
                    continue
                clean.append(p1)
            if not clean:
                continue
            s = [f"M{clean[0][0]} {clean[0][1]}"]
            for (x0, y0), (x1, y1) in zip(clean, clean[1:]):
                s.append(f"h{x1 - x0}" if y0 == y1 else f"v{y1 - y0}")
            s.append("z")
            out.append("".join(s))
    return "".join(out)


def centre(c):
    x, y = cell_xy(c)
    return x + C / 2, y + C / 2


def kt(*secs):
    return ";".join(fmt(s / LOOP, 4) for s in secs)


def build(seed=5, label=None):
    mono = Font("geist-mono-latin-400-normal.woff2")
    adj, passages = make_maze(seed)
    A = (0, NY // 2)
    B = (NX - 1, NY // 2)
    dA, pA = bfs(adj, A)
    dB, pB = bfs(adj, B)
    L = dA[B]                         # length of the shortest path in steps
    K = (L + 1) // 2                  # both frontiers stop once they touch

    # who reaches each cell first, and when
    owner, depth = {}, {}
    for c in adj:
        a, b = dA.get(c, 10 ** 9), dB.get(c, 10 ** 9)
        if min(a, b) > K:
            continue
        if a <= b:
            owner[c], depth[c] = 0, a
        else:
            owner[c], depth[c] = 1, b
    # meeting point is the middle of the shortest path
    path = [B]
    while path[-1] != A:
        path.append(pA[path[-1]])
    path = path[::-1]
    mid = path[L // 2]

    def t_of(d):
        return FLOOD_AT + d / K * FLOOD_DUR

    # every cell joins the bucket of (side, depth), along with the bridges to the cells
    # of the same side it was reached from
    buckets = {}
    for c, s in owner.items():
        d = depth[c]
        rects = [rect_of_square(c)]
        for n in adj[c]:
            if owner.get(n) == s and depth[n] < d:
                rects.append(rect_of_bridge(c, n))
        buckets.setdefault((s, d), []).extend(rects)

    defs, body = [], [f'<rect width="{W}" height="{H}" rx="18" fill="{BG}"/>']
    # faint maze so you can see it before anything happens. every corridor merged into one
    # outline and filled, which is the cheapest thing to repaint on every frame
    all_rects = [rect_of_square(c) for c in adj] + [rect_of_bridge(a, b) for a, b in passages]
    body.append(f'<path d="{union_d(all_rects)}" fill="#c9d1d9" fill-opacity=".055" fill-rule="evenodd"/>')

    for (s, d), rects in sorted(buckets.items()):
        bid = f"b{s}_{d}"
        defs.append(f'<path id="{bid}" d="{union_d(rects)}"/>')
    flood, flash = [], []
    for (s, d) in sorted(buckets):
        bid = f"b{s}_{d}"
        t = t_of(d)
        col = lerp_hex(LEFT_RAMP if s == 0 else RIGHT_RAMP, d / K)
        # settle bright, dim a little once the path shows up so it reads on top
        t_path = t_of(K) + 0.25
        flood.append(f'<use href="#{bid}" fill="{col}" opacity=".42">'
                     f'<animate attributeName="opacity" dur="{LOOP}s" repeatCount="indefinite" '
                     f'keyTimes="{kt(0, t, t + .25, t_path, t_path + .6, FADE_AT, FADE_AT + .9, LOOP)}" '
                     f'values="0;0;.9;.9;.42;.42;0;0"/></use>')
        flash.append(f'<use href="#{bid}" fill="#ffffff" opacity="0">'
                     f'<animate attributeName="opacity" dur="{LOOP}s" repeatCount="indefinite" '
                     f'keyTimes="{kt(0, t, t + .05, t + .5, LOOP)}" values="0;0;.95;0;0"/></use>')
    body.append("<g>" + "".join(flood) + "</g>")
    body.append("<g>" + "".join(flash) + "</g>")

    # the moment they touch
    mx, my = centre(mid)
    t_meet = t_of(K)
    body.append(f'<circle cx="{fmt(mx)}" cy="{fmt(my)}" r="4" fill="none" stroke="#ffffff" stroke-width="2" opacity="0">'
                f'<animate attributeName="r" dur="{LOOP}s" repeatCount="indefinite" '
                f'keyTimes="{kt(0, t_meet, t_meet + .9, LOOP)}" values="4;4;46;46"/>'
                f'<animate attributeName="opacity" dur="{LOOP}s" repeatCount="indefinite" '
                f'keyTimes="{kt(0, t_meet, t_meet + .05, t_meet + .9, LOOP)}" values="0;0;1;0;0"/></circle>')

    # shortest path, drawn from the meeting point out to both ends
    i_mid = L // 2
    halves = [path[i_mid::-1], path[i_mid:]]
    t_draw = t_meet + 0.2
    for h in halves:
        pts = [centre(c) for c in h]
        d = "M" + " L".join(f"{fmt(x)} {fmt(y)}" for x, y in pts)
        for width, color, op in ((9, "#ffffff", .16), (2.6, "#ffffff", 1)):
            body.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linecap="round" '
                        f'stroke-linejoin="round" pathLength="1" stroke-dasharray="1 1" stroke-dashoffset="0" opacity="{op}">'
                        f'<animate attributeName="stroke-dashoffset" dur="{LOOP}s" repeatCount="indefinite" calcMode="spline" '
                        f'keyTimes="{kt(0, t_draw, t_draw + PATH_DUR, FADE_AT, LOOP)}" '
                        f'keySplines="0 0 1 1;.4 0 .2 1;0 0 1 1;0 0 1 1" values="1;1;0;0;1"/>'
                        f'<animate attributeName="opacity" dur="{LOOP}s" repeatCount="indefinite" '
                        f'keyTimes="{kt(0, FADE_AT, FADE_AT + .9, LOOP)}" values="{op};{op};0;0"/></path>')

    # a packet that keeps running along the finished path
    full = "M" + " L".join(f"{fmt(x)} {fmt(y)}" for x, y in (centre(c) for c in path))
    t_run = t_draw + PATH_DUR
    body.append(f'<path d="{full}" fill="none" stroke="#ffffff" stroke-width="5" stroke-linecap="round" '
                f'pathLength="100" stroke-dasharray="2.5 97.5" stroke-dashoffset="2.5" opacity="0">'
                f'<animate attributeName="stroke-dashoffset" dur="{LOOP}s" repeatCount="indefinite" '
                f'keyTimes="{kt(0, t_run, FADE_AT, LOOP)}" values="2.5;2.5;-97.5;-97.5"/>'
                f'<animate attributeName="opacity" dur="{LOOP}s" repeatCount="indefinite" '
                f'keyTimes="{kt(0, t_run, t_run + .1, FADE_AT - .2, FADE_AT, LOOP)}" values="0;0;1;1;0;0"/></path>')

    # the two ends
    for c, col in ((A, "#7cf0ff"), (B, "#ffb35c")):
        x, y = centre(c)
        body.append(f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="6.5" fill="none" stroke="{col}" stroke-width="2"/>'
                    f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="2.4" fill="{col}"/>')

    cap_y = H - 22
    body.append(f'<path fill="{DIM}" opacity=".9" d="{mono.path_d("fig. 2", 14.5, OX + 4, cap_y, tracking=0.04, precision=1)}"/>')
    tag = label or f"{NX * NY:,} cells"
    info = f"bidirectional bfs · {tag} · shortest path {L} steps"
    body.append(f'<path fill="{DIM}" opacity=".9" d="{mono.path_d(info, 14.5, W - OX - 4, cap_y, anchor="end", tracking=0.02, precision=1)}"/>')

    svg = svg_doc(W, H, "".join(body), defs="".join(defs),
                  title="bidirectional search", desc="two breadth first searches meet in a maze and trace the shortest path")
    p, n = write("maze.svg", svg)
    print(p, f"{n / 1024:.0f} KB", "L", L, "K", K, "buckets", len(buckets))


FIRST_DAY = (2026, 11, 23)


def daily():
    """Today's maze. The date is the seed, so every day is different but reproducible."""
    import datetime as dt
    today = dt.datetime.now(dt.timezone.utc).date()
    n = (today - dt.date(*FIRST_DAY)).days + 1
    build(seed=int(today.strftime("%Y%m%d")), label=f"daily maze #{n}")


if __name__ == "__main__":
    import argparse
    import datetime as dt

    ap = argparse.ArgumentParser(description="draw figure 2")
    ap.add_argument("--daily", action="store_true", help="new maze every day, seeded by the date")
    ap.add_argument("--seed", type=int, default=5)
    args = ap.parse_args()
    if args.daily:
        daily()
    else:
        build(seed=args.seed)
