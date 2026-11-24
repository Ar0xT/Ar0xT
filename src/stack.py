"""Figure 4. The stack, kept broad on purpose. On the right, requests travel through a Spring Boot
app the way they really do, filter chain, controller, service, repository, database, and the
responses ride back. A new request leaves every two seconds, so the boxes flash on a beat."""
from svgkit import ACCENT, BG, DIM, INK, Font, fmt, svg_doc, write

W, H = 1200, 360
WARM = "#ffb35c"
BEAT = 2.0           # a new request leaves this often
CYCLE = 6.0          # one request, there and back, plus idle time
LANE_REQ, LANE_RES = 180, 222
BOXES = [
    ("filter chain", "spring security"),
    ("@RestController", "spring web"),
    ("@Service", "your logic"),
    ("@Repository", "spring data jpa"),
]


def build():
    mono = Font("geist-mono-latin-400-normal.woff2")
    disp = Font("unbounded-latin-800-normal.woff2")
    cw = mono.width("a", 13)
    body = [f'<rect width="{W}" height="{H}" rx="18" fill="{BG}"/>']
    defs = []

    # left side, the broad statement
    lx = 60
    body.append(f'<path fill="{DIM}" d="{mono.path_d("stack", 14.5, lx, 128, tracking=.12, precision=1)}"/>')
    body.append(f'<path fill="{INK}" d="{disp.path_d("java", 92, lx - 4, 222, precision=1)}"/>')
    body.append(f'<path fill="{INK}" d="{mono.path_d("spring ecosystem", 16, lx, 262, precision=1)}"/>')
    body.append(f'<path fill="{DIM}" d="{mono.path_d("and a little bit of everything else", 14.5, lx, 288, precision=1)}"/>')

    # geometry of the pipeline
    bw, gap, pad = 134, 10, 16
    cx0 = 492
    box_x = [cx0 + pad + i * (bw + gap) for i in range(len(BOXES))]
    cont_w = pad * 2 + len(BOXES) * bw + (len(BOXES) - 1) * gap
    client_x, db_x = 438, cx0 + cont_w + 52
    top, bot = 140, 262

    # spring boot container
    body.append(f'<rect x="{cx0}" y="{top - 34}" width="{cont_w}" height="{bot - top + 62}" rx="14" fill="#c9d1d9" '
                f'fill-opacity=".02" stroke="{DIM}" stroke-opacity=".55" stroke-dasharray="5 6"/>')
    body.append(f'<path fill="{DIM}" d="{mono.path_d("spring boot", 13, cx0 + 16, top - 14, tracking=.04, precision=1)}"/>')

    # lanes with a slow drift so the direction reads even between packets
    css = (f".ln{{fill:none;stroke-width:1.2;stroke-dasharray:2 7}}"
           f".rq{{stroke:{ACCENT};stroke-opacity:.35;animation:rq 1.2s linear infinite}}"
           f".rs{{stroke:{WARM};stroke-opacity:.3;animation:rs 1.2s linear infinite}}"
           f"@keyframes rq{{to{{stroke-dashoffset:-9}}}}@keyframes rs{{to{{stroke-dashoffset:9}}}}"
           f".bx{{fill:#c9d1d9;fill-opacity:.03;stroke:#c9d1d9;stroke-opacity:.18}}")
    body.append(f'<path class="ln rq" d="M{client_x + 26} {LANE_REQ}H{db_x - 30}"/>')
    body.append(f'<path class="ln rs" d="M{client_x + 26} {LANE_RES}H{db_x - 30}"/>')

    # timing of one request. the request stops briefly at every box, the response only at the controller
    stops = [x + bw / 2 for x in box_x]
    t, req = 0.0, [(client_x + 26, 0.0)]
    hits_req = []
    for sx in stops:
        t += 0.42
        req.append((sx, t))
        hits_req.append(t)
        t += 0.22
        req.append((sx, t))
    t += 0.42
    req.append((db_x - 30, t))
    t_db = t
    t += 0.3
    res = [(db_x - 30, t)]
    hits_res = []
    for i, sx in reversed(list(enumerate(stops))):
        t += 0.26
        res.append((sx, t))
        hits_res.append((i, t))
        if i == 1:
            t += 0.18
            res.append((sx, t))
    t += 0.3
    res.append((client_x + 26, t))
    t_back = t

    def motion(points, lane, colour, t_start, t_end):
        x0 = points[0][0]
        keys = ";".join(fmt(tt / CYCLE, 4) for _, tt in points) + ";1"
        vals = ";".join(f"{fmt(x - x0)},0" for x, _ in points) + f";{fmt(points[-1][0] - x0)},0"
        vis = (f'<animate attributeName="opacity" dur="{CYCLE}s" repeatCount="indefinite" begin="{{b}}" calcMode="discrete" '
               f'keyTimes="0;{fmt(t_start / CYCLE, 4)};{fmt(t_end / CYCLE, 4)}" values="0;1;0"/>')
        return (f'<g transform="translate({fmt(x0)} {lane})" opacity="0">'
                f'<animateMotion dur="{CYCLE}s" repeatCount="indefinite" begin="{{b}}" calcMode="linear" keyTimes="0;{keys}" '
                f'values="0,0;{vals}"/>{vis}'
                f'<circle r="10" fill="{colour}" fill-opacity=".18"/><circle r="4" fill="{colour}"/><circle r="1.6" fill="#fff"/></g>')

    m_req = motion(req, LANE_REQ, ACCENT, 0.0, t_db)
    m_res = motion(res, LANE_RES, WARM, res[0][1], t_back)
    n_in_flight = int(CYCLE / BEAT)
    for k in range(n_in_flight):
        b = f"-{fmt(k * BEAT, 2)}s"
        body.append(m_req.replace("{b}", b))
        body.append(m_res.replace("{b}", b))

    def flash(times, colour, x, y, w, h, rx):
        # all requests share one beat, so every flash repeats every BEAT seconds
        ts = sorted((tt % BEAT) / BEAT for tt in times)
        keys, vals = ["0"], ["0"]
        for p in ts:
            a, b2 = max(0.0, p - 0.01), min(1.0, p + 0.16)
            keys += [fmt(a, 4), fmt(p, 4), fmt(b2, 4)]
            vals += ["0", "1", "0"]
        keys.append("1")
        vals.append("0")
        return (f'<rect x="{fmt(x)}" y="{fmt(y)}" width="{fmt(w)}" height="{fmt(h)}" rx="{rx}" fill="{colour}" fill-opacity=".1" '
                f'stroke="{colour}" stroke-opacity=".9" stroke-width="1.4" opacity="0">'
                f'<animate attributeName="opacity" dur="{BEAT}s" repeatCount="indefinite" keyTimes="{";".join(keys)}" '
                f'values="{";".join(vals)}"/></rect>')

    for i, (title, sub) in enumerate(BOXES):
        x = box_x[i]
        body.append(f'<rect class="bx" x="{x}" y="{top}" width="{bw}" height="{bot - top}" rx="10"/>')
        body.append(flash([hits_req[i]], ACCENT, x, top, bw, bot - top, 10))
        body.append(flash([tt for j, tt in hits_res if j == i], WARM, x, top, bw, bot - top, 10))
        body.append(f'<path fill="{INK}" d="{mono.path_d(title, 13, x + bw / 2, top + 24, anchor="middle", precision=1)}"/>')
        body.append(f'<path fill="{DIM}" d="{mono.path_d(sub, 11.5, x + bw / 2, bot - 14, anchor="middle", precision=1)}"/>')

    # client and database
    body.append(f'<circle cx="{client_x}" cy="{(LANE_REQ + LANE_RES) / 2}" r="26" fill="#c9d1d9" fill-opacity=".03" '
                f'stroke="#c9d1d9" stroke-opacity=".25"/>')
    body.append(flash([t_back], WARM, client_x - 26, (LANE_REQ + LANE_RES) / 2 - 26, 52, 52, 26))
    body.append(f'<path fill="{DIM}" d="{mono.path_d("client", 11.5, client_x, bot + 6, anchor="middle", precision=1)}"/>')
    ok_t = (t_back % BEAT) / BEAT
    body.append(f'<g opacity="0"><animate attributeName="opacity" dur="{BEAT}s" repeatCount="indefinite" '
                f'keyTimes="0;{fmt(ok_t, 4)};{fmt(min(1, ok_t + .02), 4)};{fmt(min(1, ok_t + .42), 4)};1" values="0;0;1;0;0"/>'
                f'<path fill="{WARM}" d="{mono.path_d("200 ok", 13, client_x, top - 6, anchor="middle", precision=1)}"/></g>')
    dy = (LANE_REQ + LANE_RES) / 2
    cyl = (f'M{db_x - 28} {dy - 30}v60a28 9 0 0 0 56 0v-60')
    body.append(f'<path d="{cyl}" fill="#c9d1d9" fill-opacity=".03" stroke="#c9d1d9" stroke-opacity=".25"/>'
                f'<ellipse cx="{db_x}" cy="{dy - 30}" rx="28" ry="9" fill="{BG}" stroke="#c9d1d9" stroke-opacity=".25"/>')
    body.append(flash([t_db], ACCENT, db_x - 30, dy - 41, 60, 82, 12))
    body.append(f'<path fill="{DIM}" d="{mono.path_d("database", 11.5, db_x, bot + 6, anchor="middle", precision=1)}"/>')

    cap_y = H - 22
    body.append(f'<path fill="{DIM}" opacity=".9" d="{mono.path_d("fig. 4", 14.5, 34, cap_y, tracking=0.04, precision=1)}"/>')
    body.append(f'<path fill="{DIM}" opacity=".9" d="{mono.path_d("one request after another through a spring boot app", 14.5, W - 34, cap_y, anchor="end", tracking=0.02, precision=1)}"/>')

    svg = svg_doc(W, H, "".join(body), style=css, title="stack",
                  desc="java and the spring ecosystem. requests flow through a spring boot app and back.")
    p, n = write("stack.svg", svg)
    print(p, f"{n / 1024:.0f} KB")


if __name__ == "__main__":
    build()
