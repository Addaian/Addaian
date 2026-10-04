"""Render a rotating 3D chess board as ASCII frames, packed into an animated SVG."""
import math
import sys

COLS, ROWS = 170, 90
RAMP = ".,:;-=+*#%@"  # pieces
SQ_LIGHT, SQ_DARK, SIDE = "=", ".", "|"
CHAR_ASPECT = 2.0          # terminal cells are ~2x taller than wide
TILT = math.radians(34)    # camera elevation
CAM_DIST = 40.0
SCALE = 205.0

# Piece profiles: list of (height, radius) points, bottom to top.
PROFILES = {
    "p": [(0, .34), (.08, .34), (.12, .24), (.32, .14), (.36, .2), (.40, .12),
          (.46, .17), (.56, .18), (.64, .12), (.68, 0)],
    "r": [(0, .36), (.1, .36), (.14, .26), (.5, .24), (.54, .32), (.72, .32), (.72, 0)],
    "b": [(0, .34), (.1, .34), (.14, .22), (.5, .13), (.56, .2), (.6, .12),
          (.7, .17), (.82, .12), (.9, .05), (.96, 0)],
    "n": [(0, .36), (.1, .36), (.14, .24), (.4, .2), (.6, .28), (.74, .22), (.8, 0)],
    "q": [(0, .38), (.1, .38), (.14, .26), (.62, .14), (.68, .24), (.74, .16),
          (.9, .24), (.96, .14), (1.02, 0)],
    "k": [(0, .38), (.1, .38), (.14, .26), (.68, .15), (.74, .26), (.8, .16),
          (.98, .22), (1.0, .08), (1.06, .08), (1.12, .03), (1.16, 0)],
}

# A mid-game position: (file 0-7, rank 0-7, piece, is_white)
POSITION = [
    (4, 0, "k", True), (3, 0, "q", True), (0, 0, "r", True), (5, 2, "n", True),
    (2, 3, "b", True), (4, 3, "p", True), (3, 2, "p", True), (6, 1, "p", True),
    (4, 7, "k", False), (3, 6, "q", False), (7, 7, "r", False), (2, 5, "n", False),
    (4, 4, "p", False), (5, 6, "b", False), (1, 6, "p", False), (6, 6, "p", False),
]

LIGHT = (-0.45, 0.8, -0.4)
_l = math.sqrt(sum(c * c for c in LIGHT))
LIGHT = tuple(c / _l for c in LIGHT)

# Surface samples: (x, y, z, nx, ny, nz, albedo, cls) in world space, y up.
def build_scene():
    pts = []
    step = 0.04
    # Board top (y=0), squares from -4..4
    n = int(8 / step)
    for i in range(n):
        for j in range(n):
            x = -4 + (i + .5) * step
            z = -4 + (j + .5) * step
            fi, ri = int(x + 4), int(z + 4)
            light_sq = (fi + ri) % 2 == 1
            pts.append((x, 0, z, 0, 1, 0, 1.0, 1 if light_sq else 0))
    # Board sides (thickness .35)
    t = 0.2
    for k in range(n):
        s = -4 + (k + .5) * step
        for h in range(int(t / step)):
            y = -(h + .5) * step
            pts.append((s, y, -4, 0, 0, -1, .55, 2))
            pts.append((s, y, 4, 0, 0, 1, .55, 2))
            pts.append((-4, y, s, -1, 0, 0, .55, 2))
            pts.append((4, y, s, 1, 0, 0, .55, 2))
    # Pieces as surfaces of revolution, scaled up a bit
    for f, r, kind, white in POSITION:
        cx, cz = -4 + f + .5, -4 + r + .5
        prof = [(h * 1.9, rad * 1.25) for h, rad in PROFILES[kind]]
        alb = 1.0
        cls = 3 if white else 4
        for a in range(len(prof) - 1):
            (h0, r0), (h1, r1) = prof[a], prof[a + 1]
            seg = math.hypot(h1 - h0, r1 - r0)
            if seg == 0:
                continue
            # outward normal in (radial, vertical) plane
            nr, nh = (h1 - h0) / seg, -(r1 - r0) / seg
            steps = max(2, int(seg / 0.018))
            for s in range(steps):
                u = (s + .5) / steps
                h, rad = h0 + (h1 - h0) * u, r0 + (r1 - r0) * u
                m = max(8, int(2 * math.pi * max(rad, .02) / 0.018))
                for q in range(m):
                    th = 2 * math.pi * q / m
                    c, sn = math.cos(th), math.sin(th)
                    pts.append((cx + rad * c, h, cz + rad * sn,
                                nr * c, nh, nr * sn, alb, cls))
    return pts


def render(pts, angle):
    ca, sa = math.cos(angle), math.sin(angle)
    ct, st = math.cos(TILT), math.sin(TILT)
    zbuf = [[-1e9] * COLS for _ in range(ROWS)]
    out = [[" "] * COLS for _ in range(ROWS)]
    cls_out = [[0] * COLS for _ in range(ROWS)]
    for x, y, z, nx, ny, nz, alb, cls in pts:
        # spin around y
        x1, z1 = x * ca - z * sa, x * sa + z * ca
        # tilt around x (camera looking down)
        y2, z2 = y * ct - z1 * st, y * st + z1 * ct
        depth = CAM_DIST - z2           # larger z2 = closer to camera
        ooz = 1 / depth
        sx = int(COLS / 2 + SCALE * ooz * x1 * CHAR_ASPECT * 0.5 * 2)
        sy = int(ROWS / 2 - SCALE * ooz * (y2 - 0.6))
        if 0 <= sx < COLS and 0 <= sy < ROWS and ooz > zbuf[sy][sx]:
            # rotate normal the same way for view-facing check
            nx1, nz1 = nx * ca - nz * sa, nx * sa + nz * ca
            nz2 = ny * st + nz1 * ct
            if nz2 < -0.05 and cls >= 3:
                continue  # back face of a piece
            zbuf[sy][sx] = ooz
            if cls == 0:
                ch = SQ_DARK
            elif cls == 1:
                ch = SQ_LIGHT
            elif cls == 2:
                ch = SIDE
            else:
                lum = max(0.0, nx * LIGHT[0] + ny * LIGHT[1] + nz * LIGHT[2])
                b = alb * (0.3 + 0.7 * lum)
                ch = RAMP[min(len(RAMP) - 1, int(b * (len(RAMP) - 1) + .5))]
            out[sy][sx] = ch
            cls_out[sy][sx] = cls
    return out, cls_out


if __name__ == "__main__":
    pts = build_scene()
    ang = math.radians(float(sys.argv[1]) if len(sys.argv) > 1 else 20)
    out, _ = render(pts, ang)
    print("\n".join("".join(r).rstrip() for r in out))
