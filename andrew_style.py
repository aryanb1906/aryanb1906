#!/usr/bin/env python3
"""
Build an Andrew6rant-style neofetch profile SVG:
- ASCII self-portrait on the left (fully visible, static)
- terminal info panel on the right that types itself in line by line
Generates dark_mode.svg and light_mode.svg (self-contained, SMIL).
"""
import os
import sys
import json
import urllib.request
from PIL import Image, ImageOps, ImageEnhance

# ---- 1. ASCII portrait ------------------------------------------------
# Higher resolution (56 wide) so the FACE reads clearly, rendered with a
# small font / tight line-height so it still fits Andrew's ~530px height.
ASCII_COLS = 56
ASCII_FS = 13 # portrait font-size (px)
ASCII_LH = 14 # portrait line-height (px)
ASCII_CW = 7.8 # portrait char advance (px) at that font size
RAMP = " .'`^\",:;Il!i~+_-?][}{1)(|/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"

def portrait_rows(path, cols=ASCII_COLS):
    """Backlit-face friendly: lift shadows (gamma), autocontrast, boost."""
    im = Image.open(path).convert("L")
    im = im.point(lambda v: int(((v / 255.0) ** 0.55) * 255)) # lift shadows
    im = ImageOps.autocontrast(im, cutoff=2)
    im = ImageEnhance.Contrast(im).enhance(1.25)
    w, h = im.size
    # keep aspect undistorted for a cell of ASCII_CW x ASCII_LH
    rows = max(1, int(cols * (h / w) * (ASCII_CW / ASCII_LH)))
    im = im.resize((cols, rows))
    px = im.load()
    n = len(RAMP) - 1
    out = []
    for y in range(rows):
        out.append("".join(RAMP[int((255 - px[x, y]) / 255 * n)]
                           for x in range(cols)).rstrip())
    return out

# ---- 2. Dynamic GitHub Stats Fetching ---------------------------------
def fetch_github_stats(username="aryanb1906"):
    stats = {
        "repos": 33,
        "stars": 8,
        "commits": "2,936",
        "followers": 27,
        "since": "January 2024",
        "location": "Jaipur, IN"
    }
    try:
        # Fetch user general info
        req = urllib.request.Request(
            f"https://api.github.com/users/{username}",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            stats["repos"] = data.get("public_repos", stats["repos"])
            stats["followers"] = data.get("followers", stats["followers"])
            loc = data.get("location")
            if loc:
                stats["location"] = f"{loc}, IN"
            created_at = data.get("created_at")
            if created_at:
                year = created_at[:4]
                month_num = created_at[5:7]
                months = ["January", "February", "March", "April", "May", "June", 
                          "July", "August", "September", "October", "November", "December"]
                stats["since"] = f"{months[int(month_num)-1]} {year}"
        
        # Fetch repos to sum stargazers
        req_repos = urllib.request.Request(
            f"https://api.github.com/users/{username}/repos?per_page=100",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req_repos, timeout=5) as response:
            repos = json.loads(response.read().decode())
            stars = sum(repo.get("stargazers_count", 0) for repo in repos)
            stats["stars"] = stars
    except Exception as e:
        print("API fetch failed, using fallback stats:", e)
    return stats

# ---- 3. Info Panel Configuration --------------------------------------
NAME = "aryanb1906@github"
github_stats = fetch_github_stats("aryanb1906")

INFO = [
    ("header", NAME),
    ("kv", (["OS"], "Windows 11 · Linux (Ubuntu)")),
    ("kv", (["Uptime"], "21 years")),
    ("kv", (["Host"], "KIIT Bhubaneswar")),
    ("kv", (["Kernel"], "B.Tech CSE (2023 - 2027)")),
    ("kv", (["IDE"], "VS Code · Cursor")),
    ("blank", None),
    ("kv", (["Languages", "Programming"], "C++ · Python · JavaScript · SQL")),
    ("kv", (["Languages", "Computer"], "HTML · CSS · JSON · YAML")),
    ("kv", (["Languages", "Real"], "English · Hindi")),
    ("blank", None),
    ("kv", (["Hobbies", "Software"], "CP · Web Dev · GenAI")),
    ("kv", (["Hobbies", "Building"], "Open Source · Hackathons")),
    ("blank", None),
    ("section", "Contact"),
    ("kv", (["Email", "Personal"], "aryanaakash2005@gmail.com")),
    ("kv", (["Portfolio"], "aryanb1906.github.io")),
    ("kv", (["LinkedIn"], "aryan-bhargava")),
    ("kv", (["LinkedIn", "Followers"], "21,500+")),
    ("kv", (["GitHub"], "aryanb1906")),
    ("blank", None),
    ("section", "GitHub Stats"),
    ("stats1", None),
    ("stats2", None),
    ("stats3", None),
]

VALUE_COL = 26 # column where value text begins (monospace chars)
THEMES = {
    "dark": dict(bg="#161b22", text="#c9d1d9", key="#ffa657",
                 value="#a5d6ff", cc="#616e7f", add="#3fb950", dele="#f85149"),
    "light": dict(bg="#ffffff", text="#24292f", key="#953800",
                  value="#0a3069", cc="#6e7781", add="#1a7f37", dele="#cf222e"),
}

def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))

def leader(prefix_len):
    """Dots needed to reach the value column."""
    return max(1, VALUE_COL - prefix_len)

def kv_line(keys, value):
    """Return tspans for a '. Key.Sub: ....... value' line."""
    key_txt = ".".join(keys)
    prefix_len = 2 + len(key_txt) + 1
    dots = leader(prefix_len)
    key_spans = ('<tspan class="key">'
                 + '</tspan>.<tspan class="key">'.join(esc(k) for k in keys)
                 + '</tspan>')
    return (f'<tspan class="cc">. </tspan>{key_spans}'
            f'<tspan class="cc">:</tspan>'
            f'<tspan class="cc"> {"." * dots} </tspan>'
            f'<tspan class="value">{esc(value)}</tspan>')

CW = 10.0 # px per monospace char (info panel, wide-font safe)
INFO_X = 500 # info panel left edge (clears the ASCII portrait)
W, H = 1120, 540

# ---- 4. SVG Generation ------------------------------------------------
def build_svg(theme_name, ascii_rows):
    t = THEMES[theme_name]
    parts = []
    parts.append(
        f"<svg xmlns='http://www.w3.org/2000/svg' "
        f"font-family=\"Consolas,'DejaVu Sans Mono',monospace\" "
        f"width='{W}px' height='{H}px' font-size='16px'>")
    parts.append(
        "<style>"
        f".key{{fill:{t['key']};}} .value{{fill:{t['value']};}} "
        f".cc{{fill:{t['cc']};}} .add{{fill:{t['add']};}} "
        f".del{{fill:{t['dele']};}} "
        f"text,tspan{{white-space:pre;}} "
        f"</style>")
    parts.append(f"<rect width='{W}px' height='{H}px' fill='{t['bg']}' rx='15'/>")
    
    # ----- ASCII portrait: fully visible, static (small dense font) -----
    parts.append(f"<text x='15' y='24' fill='{t['text']}' "
                 f"font-size='{ASCII_FS}px'>")
    y = 24
    for row in ascii_rows:
        parts.append(f"<tspan x='15' y='{y}'>{esc(row)}</tspan>")
        y += ASCII_LH
    parts.append("</text>")
    
    # ----- Right info panel: fully visible -----
    px = INFO_X
    y = 30
    n_dash = int((W - px) / CW) - 16
    for i, (kind, payload) in enumerate(INFO):
        if kind == "header":
            dash = "—" * max(4, n_dash - len(payload))
            body = (f"<tspan x='{px}' y='{y}' fill='{t['text']}'>{esc(payload)}"
                    f"</tspan><tspan class='cc'> -{dash}-</tspan>")
        elif kind == "section":
            dash = "—" * max(4, n_dash - len(payload) - 2)
            body = (f"<tspan x='{px}' y='{y}' fill='{t['text']}'>- {esc(payload)}"
                    f"</tspan><tspan class='cc'> -{dash}-</tspan>")
        elif kind == "blank":
            body = f"<tspan x='{px}' y='{y}' class='cc'>. </tspan>"
        elif kind == "kv":
            keys, value = payload
            body = f"<tspan x='{px}' y='{y}'>{kv_line(keys, value)}</tspan>"
        elif kind == "stats1":
            body = (f"<tspan x='{px}' y='{y}'><tspan class='cc'>. </tspan>"
                    f"<tspan class='key'>Repos</tspan>"
                    f"<tspan class='cc'> ..... </tspan>"
                    f"<tspan class='value'>{github_stats['repos']}</tspan>"
                    f"<tspan class='cc'> | </tspan>"
                    f"<tspan class='key'>Stars</tspan>"
                    f"<tspan class='cc'> ..... </tspan>"
                    f"<tspan class='value'>{github_stats['stars']}</tspan></tspan>")
        elif kind == "stats2":
            body = (f"<tspan x='{px}' y='{y}'><tspan class='cc'>. </tspan>"
                    f"<tspan class='key'>Commits</tspan>"
                    f"<tspan class='cc'> ... </tspan>"
                    f"<tspan class='value'>{github_stats['commits']}</tspan>"
                    f"<tspan class='cc'> | </tspan>"
                    f"<tspan class='key'>Followers</tspan>"
                    f"<tspan class='cc'> . </tspan>"
                    f"<tspan class='value'>{github_stats['followers']}</tspan></tspan>")
        elif kind == "stats3":
            body = (f"<tspan x='{px}' y='{y}'><tspan class='cc'>. </tspan>"
                    f"<tspan class='key'>Member Since</tspan>"
                    f"<tspan class='cc'> ... </tspan>"
                    f"<tspan class='value'>{github_stats['since']}</tspan>"
                    f"<tspan class='cc'> | </tspan>"
                    f"<tspan class='key'>Location</tspan>"
                    f"<tspan class='cc'> . </tspan>"
                    f"<tspan class='value'>{github_stats['location']}</tspan></tspan>")
        parts.append(f"<text>{body}</text>")
        y += 20
        
    # ----- blinking terminal prompt + cursor (the "alive" animation) -----
    prompt_y = y + 8
    parts.append(
        f"<text x='{px}' y='{prompt_y}' fill='{t['add']}'>{NAME}</text>"
        f"<text x='{px + len(NAME) * CW}' y='{prompt_y}' fill='{t['text']}'>:~$</text>")
    cur_x = px + (len(NAME) + 4) * CW
    parts.append(
        f"<rect x='{cur_x}' y='{prompt_y - 13}' width='{int(CW)}' height='17' "
        f"fill='{t['add']}'>"
        f"<animate attributeName='opacity' values='1;1;0;0' dur='1.1s' "
        f"keyTimes='0;0.5;0.5;1' repeatCount='indefinite'/></rect>")
    parts.append("</svg>")
    return "\n".join(parts)

def main():
    portrait_path = "aryan_portrait.png"
    if not os.path.exists(portrait_path):
        print(f"! Portrait file not found at: {portrait_path}")
        sys.exit(1)
        
    print(f"→ Reading {portrait_path}")
    ascii_rows = portrait_rows(portrait_path)
    
    for name in ("dark", "light"):
        out = f"{name}_mode.svg"
        with open(out, "w", encoding="utf-8") as f:
            f.write(build_svg(name, ascii_rows))
        print("wrote", out)

if __name__ == "__main__":
    main()
