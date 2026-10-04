"""Pack rotating-chessboard ASCII frames into one animated SVG.

usage: build_svg.py out.svg            animated, all frames
       build_svg.py out.svg --still N  only frame N, no animation (for previews)
"""
import math
import sys

import chess3d as c  # run from this directory: python3 build_svg.py ../chessboard.svg

FRAMES = 60
FRAME_MS = 85
FONT = 8.0
CW, LH = FONT * 0.6, FONT * 1.2        # monospace cell; LH/CW == CHAR_ASPECT
PAD_X, PAD_TOP, PAD_BOT = 28, 26, 22

# layer name -> (classes in it, colour)
LAYERS = [
    ("d", {0, 2}, "#373e47"),   # dark squares + board sides
    ("l", {1}, "#8b949e"),      # light squares
    ("w", {3}, "#f0f6fc"),      # white pieces
    ("b", {4}, "#ff7b72"),      # black pieces
]


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def main():
    out_path = sys.argv[1]
    still = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[2] == "--still" else None
    pts = c.build_scene()
    idxs = [still] if still is not None else range(FRAMES)
    frames = [c.render(pts, 2 * math.pi * i / FRAMES) for i in idxs]

    # Trim to the union bounding box across all frames so nothing jumps.
    used = [(r, k) for chars, _ in frames for r, row in enumerate(chars)
            for k, ch in enumerate(row) if ch != " "]
    r0, r1 = min(r for r, _ in used), max(r for r, _ in used)
    c0, c1 = min(k for _, k in used), max(k for _, k in used)
    nrows, ncols = r1 - r0 + 1, c1 - c0 + 1

    W = round(PAD_X * 2 + ncols * CW)
    H = round(PAD_TOP + PAD_BOT + nrows * LH)
    period = FRAMES * FRAME_MS / 1000

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" xml:space="preserve">',
        "<style>",
        "text{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace;"
        f"font-size:{FONT}px;white-space:pre}}",
        *[f".{n}{{fill:{col}}}" for n, _, col in LAYERS],
    ]
    if still is None:
        parts += [
            f".f{{visibility:hidden;animation:s {period:.3f}s linear infinite}}",
            f"@keyframes s{{0%{{visibility:visible}}{100 / FRAMES:.4f}%{{visibility:hidden}}"
            "100%{visibility:hidden}}",
        ]
    parts += [
        "</style>",
        f'<rect width="{W}" height="{H}" rx="12" fill="#0d1117"/>',
    ]

    for fi, (chars, cls) in enumerate(frames):
        if still is None:
            delay = -(period - fi * FRAME_MS / 1000) if fi else 0
            parts.append(f'<g class="f" style="animation-delay:{delay:.3f}s">')
        else:
            parts.append("<g>")
        for name, members, _ in LAYERS:
            for r in range(r0, r1 + 1):
                line = "".join(chars[r][k] if cls[r][k] in members and chars[r][k] != " "
                               else " " for k in range(c0, c1 + 1)).rstrip()
                if line.strip():
                    y = PAD_TOP + (r - r0 + 0.8) * LH
                    parts.append(f'<text x="{PAD_X}" y="{y:.1f}" class="{name}">{esc(line)}</text>')
        parts.append("</g>")
    parts.append("</svg>")

    with open(out_path, "w") as f:
        f.write("\n".join(parts))
    print(f"{out_path}: {W}x{H}, {len(frames)} frames, "
          f"{sum(len(p) + 1 for p in parts) / 1024:.0f} KB")


if __name__ == "__main__":
    main()
