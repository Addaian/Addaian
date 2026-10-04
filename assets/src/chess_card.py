"""Fetch Lichess + Chess.com ratings and draw them as an SVG card.

usage: python3 chess_card.py ../ratings.svg
Exits non-zero (leaving the old card alone) if either API can't be reached.
"""
import json
import sys
import urllib.request

LICHESS_USER = "Adrian4a1"
CHESSCOM_USER = "scrap2"
UA = "Addaian profile rating card (github.com/Addaian)"

W, ROW_H, TOP = 622, 34, 92
COL_LABEL, COL_LI, COL_CC = 36, 230, 430


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def lichess():
    perfs = get(f"https://lichess.org/api/user/{LICHESS_USER}")["perfs"]

    def cell(key):
        p = perfs.get(key)
        if not p or not p.get("games"):
            return None
        return (f"{p['rating']}{'?' if p.get('prov') else ''}", f"{p['games']:,} games")

    return {"bullet": cell("bullet"), "blitz": cell("blitz"), "rapid": cell("rapid"),
            "puzzles": cell("puzzle") and (str(perfs["puzzle"]["rating"]),
                                           f"{perfs['puzzle']['games']:,} solved")}


def chesscom():
    s = get(f"https://api.chess.com/pub/player/{CHESSCOM_USER}/stats")

    def cell(key):
        p = s.get(key)
        if not p or "last" not in p:
            return None
        rec = p.get("record", {})
        n = rec.get("win", 0) + rec.get("loss", 0) + rec.get("draw", 0)
        return (str(p["last"]["rating"]), f"{n:,} games")

    tac = s.get("tactics", {}).get("highest", {}).get("rating")
    return {"bullet": cell("chess_bullet"), "blitz": cell("chess_blitz"),
            "rapid": cell("chess_rapid"), "puzzles": tac and (str(tac), "peak")}


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def svg(li, cc):
    rows = ["bullet", "blitz", "rapid", "puzzles"]
    H = TOP + ROW_H * len(rows) + 22
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
        "<style>text{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace}"
        ".h{font-size:13px;fill:#3fb950}.dim{fill:#6e7681;font-size:11px}"
        ".lbl{font-size:13px;fill:#8b949e}.site{font-size:13px;font-weight:700}"
        ".r{font-size:20px;font-weight:700;fill:#f0f6fc}</style>",
        f'<rect width="{W}" height="{H}" rx="12" fill="#0d1117"/>',
        f'<text x="{COL_LABEL}" y="34" class="h">$ chess --ratings</text>',
        f'<text x="{COL_LI}" y="66" class="site" fill="#f0f6fc">lichess</text>',
        f'<text x="{COL_LI + 66}" y="66" class="dim">@{LICHESS_USER}</text>',
        f'<text x="{COL_CC}" y="66" class="site" fill="#81b64c">chess.com</text>',
        f'<text x="{COL_CC + 82}" y="66" class="dim">@{CHESSCOM_USER}</text>',
        f'<line x1="{COL_LABEL}" y1="{TOP - 12}" x2="{W - 36}" y2="{TOP - 12}" stroke="#30363d"/>',
    ]
    for i, key in enumerate(rows):
        y = TOP + 12 + i * ROW_H
        out.append(f'<text x="{COL_LABEL}" y="{y}" class="lbl">{key}</text>')
        for x, src in ((COL_LI, li), (COL_CC, cc)):
            c = src.get(key)
            if c is None:
                out.append(f'<text x="{x}" y="{y}" class="dim">—</text>')
                continue
            rating, sub = c
            out.append(f'<text x="{x}" y="{y + 2}" class="r">{esc(rating)}</text>')
            out.append(f'<text x="{x + 12 * len(rating) + 10}" y="{y}" class="dim">{esc(sub)}</text>')
    out.append("</svg>")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    try:
        li, cc = lichess(), chesscom()
    except Exception as e:  # keep the previous card rather than writing a broken one
        sys.exit(f"fetch failed: {e}")
    with open(sys.argv[1], "w") as f:
        f.write(svg(li, cc))
    print("lichess", li, "\nchess.com", cc)
