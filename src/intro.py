"""The few lines of actual text under the hero. Each line decrypts itself once, right as the
hero finishes, then the status dot keeps pulsing."""
import random

from svgkit import BG, DIM, INK, ACCENT, Font, fmt, hold_then, steps_from_zero, svg_doc, write

W, H = 1200, 236
SIZE = 23
ROWS = [
    ("studying", "software engineering at itmo university"),
    ("solving", "algorithm and data structure problems"),
    ("exploring", "how computers work, from the cpu to the backend"),
    ("status", "open to internships and new opportunities"),
]
GREEN = "#3fb950"
START = 2.3        # first line starts decrypting, timed to land just after the hero reveal
STAGGER = 0.38
CPS = 52           # characters resolved per second
HEAD = 6           # how many scrambled characters run ahead of the resolved text
FRAME = 0.034
CHARSET = "abcdefghijklmnopqrstuvwxyz0123456789#%&*+<>/=_-"


def build():
    rnd = random.Random(11)
    mono = Font("geist-mono-latin-400-normal.woff2")
    cw = mono.width("a", SIZE)
    key_w = max(len(k) for k, _ in ROWS) * cw
    gap = 2.4 * cw
    status_pad = 1.6 * cw          # room for the dot in front of the status text
    val_w = max(len(v) + (2 if k == "status" else 0) for k, v in ROWS) * cw
    x0 = (W - (key_w + gap + val_w)) / 2
    vx = x0 + key_w + gap
    y0, step = 58, 46

    defs = []
    used = set(CHARSET) | set("".join(v for _, v in ROWS))
    for ch in sorted(used - {" "}):
        d = mono.path_d(ch, SIZE, 0, 0, precision=1)
        if d:
            defs.append(f'<path id="m{ord(ch)}" d="{d}"/>')

    body = [f'<rect width="{W}" height="{H}" rx="18" fill="{BG}"/>']
    css = [f".k{{fill:{DIM}}}", f".v{{fill:{INK}}}", f".s{{fill:{ACCENT}}}"]

    for i, (key, val) in enumerate(ROWS):
        y = y0 + i * step
        t = START + i * STAGGER
        # key fades in a moment before its value starts resolving
        body.append(f'<path class="k" d="{mono.path_d(key, SIZE, x0, y, precision=1)}">'
                    f'{hold_then("opacity", 0, 1, t - 0.35, 0.5)}</path>')
        tx = vx + (status_pad if key == "status" else 0)
        n = len(val)
        dur = n / CPS
        widths = [k * cw for k in range(n + 1)]
        times = ";".join(fmt(k / n, 4) for k in range(n + 1))
        clip = f"c{i}"
        steps = [fmt(w + 2) for w in widths[1:]]
        defs.append(f'<clipPath id="{clip}"><rect x="{fmt(tx - 2)}" y="{y - SIZE}" height="{SIZE * 1.6}" width="{steps[-1]}">'
                    f'{steps_from_zero("width", "0", steps, t, dur)}</rect></clipPath>')
        uses = "".join(f'<use href="#m{ord(ch)}" x="{fmt(tx + c * cw)}" y="{y}"/>' for c, ch in enumerate(val) if ch != " ")
        body.append(f'<g class="v" clip-path="url(#{clip})">{uses}</g>')

        # scrambled head running ahead of the resolved part
        frames = int(dur / FRAME) + 1
        for f in range(frames):
            tf = t + f * FRAME
            r = min(n, int(round((tf - t) * CPS)))
            cells = []
            for c in range(r, min(n, r + HEAD)):
                if val[c] == " ":
                    continue
                ch = rnd.choice(CHARSET)
                cells.append(f'<use href="#m{ord(ch)}" x="{fmt(tx + c * cw)}" y="{y}"/>')
            if not cells:
                continue
            body.append(f'<g class="s" visibility="hidden"><set attributeName="visibility" to="visible" '
                        f'begin="{fmt(tf, 3)}s" dur="{fmt(FRAME, 3)}s"/>{"".join(cells)}</g>')

        if key == "status":
            cx, cy = vx + 0.55 * cw, y - SIZE * 0.36
            on = fmt(t - 0.2, 2)
            body.append(f'<g>{hold_then("opacity", 0, 1, t - 0.2, 0.4)}'
                        f'<circle cx="{fmt(cx)}" cy="{fmt(cy)}" r="5.5" fill="{GREEN}"/>'
                        f'<circle cx="{fmt(cx)}" cy="{fmt(cy)}" r="5.5" fill="none" stroke="{GREEN}" stroke-width="1.5">'
                        f'<animate attributeName="r" begin="{on}s" dur="2.4s" values="5.5;17" repeatCount="indefinite"/>'
                        f'<animate attributeName="stroke-opacity" begin="{on}s" dur="2.4s" values=".9;0" repeatCount="indefinite"/>'
                        f'</circle></g>')
            # block cursor that keeps blinking after the last line lands
            end_x = tx + n * cw + cw * 0.5
            cur_on = fmt(t + dur + 0.05, 2)
            body.append(f'<rect x="{fmt(end_x)}" y="{fmt(y - SIZE * 0.78)}" width="{fmt(cw * 0.62)}" height="{fmt(SIZE * 0.98)}" '
                        f'fill="{ACCENT}" opacity="0">'
                        f'<animate attributeName="opacity" begin="{cur_on}s" dur="1.1s" calcMode="discrete" '
                        f'values="1;0" keyTimes="0;.5" repeatCount="indefinite"/></rect>')

    svg = svg_doc(W, H, "".join(body), defs="".join(defs), style="".join(css),
                  title="about", desc="software engineering student at itmo university. solves algorithm and data "
                  "structure problems, curious how computers work. open to internships and new opportunities.")
    p, nbytes = write("intro.svg", svg)
    print(p, f"{nbytes / 1024:.0f} KB")


if __name__ == "__main__":
    build()
