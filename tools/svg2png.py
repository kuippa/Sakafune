"""SVGを、同じ大きさのPNGに書き出す（ヘッドレスのChrome／Edgeを使う）。

使い方:
    python tools/svg2png.py images/a.svg [images/b.svg ...]

ブラウザは環境変数 BROWSER で指定できる。省略時は、よくある場所の Edge／Chrome を探す。
"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "google-chrome", "chromium", "chromium-browser", "microsoft-edge",
]


def find_browser():
    if os.environ.get("BROWSER"):
        return os.environ["BROWSER"]
    for c in CANDIDATES:
        if Path(c).exists() or shutil.which(c):
            return c
    sys.exit("ブラウザが見つかりません。環境変数 BROWSER にChrome／Edgeのパスを指定してください。")


def size_of(svg_path):
    head = Path(svg_path).read_text(encoding="utf-8")[:2000]
    m = re.search(r'<svg[^>]*\swidth="(\d+)"[^>]*\sheight="(\d+)"', head)
    if not m:
        sys.exit(f"{svg_path}: width/height が読めません")
    return int(m.group(1)), int(m.group(2))


def main():
    browser = find_browser()
    for svg in sys.argv[1:]:
        svg = Path(svg).resolve()
        png = svg.with_suffix(".png")
        w, h = size_of(svg)
        subprocess.run([browser, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        f"--window-size={w},{h}", f"--screenshot={png}", svg.as_uri()],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        print(f"{'wrote' if png.exists() else 'FAILED'} {png.name} ({w}x{h})")


if __name__ == "__main__":
    main()
