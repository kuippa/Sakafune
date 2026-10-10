"""YAMLのモデル定義から、3D斜め見下ろし（アイソメトリック）の模式図をSVGで描く。

使い方:
    python tools/render_iso.py design/models/level1_counter.yaml --pulses 5 -o images/out.svg

- 図の寸法・しきい値・つながりは、すべてYAMLから読む（図はYAMLの写し）。
- --pulses N で、N回注いだ後の水の状態を簡易シミュレーションして描く。
- YAMLの expected（期待されるふるまい）を、同じシミュレーションで照合して結果を表示する。
"""

import argparse
import math
import sys
from pathlib import Path

import yaml

COS30 = math.cos(math.radians(30))
FONT = "'Yu Gothic','Meiryo','Hiragino Sans','Noto Sans CJK JP',sans-serif"

COL = {
    "bg": "#f7f2e7",
    "ink": "#3a3226",
    "sub": "#6a5e4c",
    "wall": "#c98b5a",      # 土器
    "wall_edge": "#7a4a26",
    "tube": "#6b8f2a",      # 竹
    "water": "#3d8fd6",
    "water_top": "#8fc3ec",
    "flow": "#2f7fc8",
    "panel": "#fffdf7",
    "panel_edge": "#c9bfa8",
}


# ------------------------------------------------------------------
# モデルの読み込みと簡易シミュレーション
# ------------------------------------------------------------------
def load_model(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def area_cm2(part):
    r = part["inner_diameter_cm"] / 2
    return math.pi * r * r


def height_cm(part, volume_ml):
    return volume_ml / area_cm2(part)  # 1 mL = 1 cm^3


def simulate(model, pulses):
    """N回注いだ後の各部品の水量（mL）を返す。"""
    parts = {p["id"]: p for p in model["parts"]}
    u = model["units"]["u_mL"]
    vol = {pid: 0.0 for pid in parts}
    pour = next(c for c in model["connections"] if c["kind"] == "pour")
    for _ in range(pulses):
        vol[pour["to"]] += pour["amount_u"] * u
        changed = True
        while changed:  # サイフォンの連鎖が落ち着くまで
            changed = False
            for p in model["parts"]:
                if p["type"] == "siphon_cup" and vol[p["id"]] >= p["threshold_mL"]:
                    vol[p["siphon_to"]] += vol[p["id"]]
                    vol[p["id"]] = 0.0
                    changed = True
    return vol


def bits_of(model, vol):
    cups = sorted((p for p in model["parts"] if p["type"] == "siphon_cup"), key=lambda p: p["bit"])
    return "".join("1" if vol[p["id"]] > 0 else "0" for p in reversed(cups))


def check_expected(model):
    results = []
    for e in model.get("expected", []):
        got = bits_of(model, simulate(model, e["pulses"]))
        results.append((e["pulses"], e["bits"], got, got == e["bits"]))
    return results


# ------------------------------------------------------------------
# アイソメトリック投影
# ------------------------------------------------------------------
class Iso:
    def __init__(self, scale, ox, oy):
        self.s, self.ox, self.oy = scale, ox, oy

    def p(self, x, y, z):
        return (self.ox + (x - y) * COS30 * self.s,
                self.oy + ((x + y) * 0.5 - z) * self.s)

    def ellipse_axes(self, r):
        # 水平な円は、横 1.2247r・縦 0.7071r の楕円に写る
        return r * self.s * math.sqrt(1.5), r * self.s * math.sqrt(0.5)


def raw_point(x, y, z):
    return ((x - y) * COS30, (x + y) * 0.5 - z)


def part_height(part):
    if part["type"] in ("siphon_cup", "basin"):
        return height_cm(part, part["capacity_mL"])
    if part["type"] == "metering_cup":
        return height_cm(part, part["volume_mL"]) * 1.15
    return 5


def fit(model, box):
    """全部品が box=(x0,y0,x1,y1) に収まる縮尺と原点を求める。"""
    xs, ys = [], []
    for p in model["parts"]:
        x, y, z = p["position"]
        r = p["inner_diameter_cm"] / 2
        h = part_height(p)
        for zz in (z - 6, z + h + 4):
            for dx, dy in ((r, -r), (-r, r), (r, r), (-r, -r)):
                X, Y = raw_point(x + dx, y + dy, zz)
                xs.append(X)
                ys.append(Y)
    x0, y0, x1, y1 = box
    s = min((x1 - x0) / (max(xs) - min(xs)), (y1 - y0) / (max(ys) - min(ys)))
    ox = x0 - min(xs) * s + ((x1 - x0) - (max(xs) - min(xs)) * s) / 2
    oy = y0 - min(ys) * s
    return Iso(s, ox, oy)


# ------------------------------------------------------------------
# SVG部品
# ------------------------------------------------------------------
def esc(t):
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def text(x, y, t, size=14, weight="normal", fill=None, anchor="start"):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{weight}" '
            f'fill="{fill or COL["ink"]}" text-anchor="{anchor}">{esc(t)}</text>')


def cylinder_shape(iso, x, y, z0, z1, r):
    """円筒の外形（側面＋手前の底の弧）と上面の楕円。"""
    rx, ry = iso.ellipse_axes(r)
    cx, top = iso.p(x, y, z1)
    _, bot = iso.p(x, y, z0)
    body = (f"M{cx - rx:.1f},{top:.1f} L{cx - rx:.1f},{bot:.1f} "
            f"A{rx:.1f},{ry:.1f} 0 0 0 {cx + rx:.1f},{bot:.1f} "
            f"L{cx + rx:.1f},{top:.1f} "
            f"A{rx:.1f},{ry:.1f} 0 0 1 {cx - rx:.1f},{top:.1f} Z")
    return body, (cx, top, rx, ry), (cx, bot, rx, ry)


def draw_vessel(iso, part, water_ml, show_tube):
    x, y, z = part["position"]
    r = part["inner_diameter_cm"] / 2
    h = part_height(part)
    out = []
    body, (cx, top, rx, ry), (_, bot, _, _) = cylinder_shape(iso, x, y, z, z + h, r)
    # 奥の内壁
    out.append(f'<path d="{body}" fill="{COL["wall"]}" fill-opacity="0.18" stroke="none"/>')
    out.append(f'<ellipse cx="{cx:.1f}" cy="{top:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" '
               f'fill="{COL["wall"]}" fill-opacity="0.25" stroke="none"/>')
    # 水
    if water_ml > 0:
        wh = height_cm(part, water_ml)
        wbody, (wcx, wtop, wrx, wry), _ = cylinder_shape(iso, x, y, z, z + wh, r * 0.97)
        out.append(f'<path d="{wbody}" fill="{COL["water"]}" fill-opacity="0.75"/>')
        out.append(f'<ellipse cx="{wcx:.1f}" cy="{wtop:.1f}" rx="{wrx:.1f}" ry="{wry:.1f}" '
                   f'fill="{COL["water_top"]}"/>')
    # 内側の管（しきい値の高さまで）
    if show_tube:
        th = height_cm(part, part["threshold_mL"])
        tx, ty0 = iso.p(x, y, z)
        _, ty1 = iso.p(x, y, z + th)
        w = max(2.5, part["siphon_tube_inner_diameter_mm"] * 0.12 * iso.s)
        out.append(f'<rect x="{tx - w:.1f}" y="{ty1 - w:.1f}" width="{2 * w:.1f}" '
                   f'height="{ty0 - ty1 + w:.1f}" rx="{w:.1f}" fill="{COL["tube"]}" '
                   f'fill-opacity="0.85" stroke="#3f5a12" stroke-width="1"/>')
        # しきい値の線（器の奥の壁に引いた目盛り）
        _, lt = iso.p(x, y, z + th)
        out.append(f'<ellipse cx="{cx:.1f}" cy="{lt:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" fill="none" '
                   f'stroke="#c0392b" stroke-width="1.4" stroke-dasharray="5 4"/>')
    # 手前の壁と縁
    out.append(f'<path d="{body}" fill="{COL["wall"]}" fill-opacity="0.22" '
               f'stroke="{COL["wall_edge"]}" stroke-width="2"/>')
    out.append(f'<ellipse cx="{cx:.1f}" cy="{top:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" fill="none" '
               f'stroke="{COL["wall_edge"]}" stroke-width="2"/>')
    return out, (cx, top, rx, ry, bot)


def arrow_defs():
    return f"""<defs>
  <marker id="ah" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
    <path d="M0,0 L10,5 L0,10 z" fill="{COL['flow']}"/></marker>
  <marker id="ahk" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
    <path d="M0,0 L10,5 L0,10 z" fill="{COL['sub']}"/></marker>
</defs>"""


def callout(px, py, bx, by, lines, width=250):
    """(px,py) を指す矢印つきの注釈の箱。lines=[(text, size, weight)]"""
    lh = [l[1] + 6 for l in lines]
    h = sum(lh) + 14
    out = [f'<line x1="{bx:.1f}" y1="{by + h / 2:.1f}" x2="{px:.1f}" y2="{py:.1f}" '
           f'stroke="{COL["sub"]}" stroke-width="1.3" marker-end="url(#ahk)"/>',
           f'<rect x="{bx:.1f}" y="{by:.1f}" width="{width}" height="{h:.1f}" rx="6" '
           f'fill="{COL["panel"]}" stroke="{COL["panel_edge"]}"/>']
    yy = by + 8
    for (t, size, weight), d in zip(lines, lh):
        yy += d
        out.append(text(bx + 10, yy - 4, t, size, weight))
    return out


def cross_section(x0, y0, cup, u):
    """教訓桝の断面図（説明用の小窓）。寸法は模式。"""
    w, h = 150, 150
    th_ratio = cup["threshold_mL"] / cup["capacity_mL"]
    lvl = y0 + 30 + h * (1 - th_ratio * 0.95)
    tube_top = y0 + 30 + h * (1 - th_ratio)
    cx = x0 + 30 + w / 2
    out = [f'<rect x="{x0}" y="{y0}" width="{w + 220}" height="{h + 110}" rx="8" '
           f'fill="{COL["panel"]}" stroke="{COL["panel_edge"]}"/>',
           text(x0 + 14, y0 + 22, "教訓桝の断面（模式）", 15, "bold")]
    # 器
    out.append(f'<path d="M{x0 + 30},{y0 + 30} L{x0 + 30},{y0 + 30 + h} L{x0 + 30 + w},{y0 + 30 + h} '
               f'L{x0 + 30 + w},{y0 + 30}" fill="none" stroke="{COL["wall_edge"]}" stroke-width="3"/>')
    # 水（しきい値の少し下）
    out.append(f'<rect x="{x0 + 32}" y="{lvl:.1f}" width="{w - 4}" height="{y0 + 30 + h - lvl - 2:.1f}" '
               f'fill="{COL["water"]}" fill-opacity="0.55"/>')
    # 内側の管と外側のかぶせ管（逆U字）
    out.append(f'<path d="M{cx - 6},{y0 + 30 + h + 30} L{cx - 6},{tube_top:.1f} '
               f'M{cx + 6},{y0 + 30 + h + 30} L{cx + 6},{tube_top:.1f}" '
               f'stroke="{COL["tube"]}" stroke-width="4" fill="none"/>')
    out.append(f'<path d="M{cx - 16},{y0 + 30 + h - 6} L{cx - 16},{tube_top - 10:.1f} '
               f'Q{cx},{tube_top - 24:.1f} {cx + 16},{tube_top - 10:.1f} L{cx + 16},{y0 + 30 + h - 6}" '
               f'stroke="{COL["tube"]}" stroke-width="3" fill="none" stroke-dasharray="1 0"/>')
    # しきい値の線
    out.append(f'<line x1="{x0 + 30}" y1="{tube_top:.1f}" x2="{x0 + 30 + w}" y2="{tube_top:.1f}" '
               f'stroke="#c0392b" stroke-width="1.5" stroke-dasharray="5 4"/>')
    out.append(f'<line x1="{cx}" y1="{y0 + 30 + h + 8}" x2="{cx}" y2="{y0 + 30 + h + 34}" '
               f'stroke="{COL["flow"]}" stroke-width="3" marker-end="url(#ah)"/>')
    tx = x0 + 30 + w + 16
    out += [text(tx, tube_top + 4, f"しきい値 θ（{cup['threshold_mL'] / u:g}u）", 13, "bold", "#c0392b"),
            text(tx, tube_top + 22, "ここを超えると", 12),
            text(tx, tube_top + 38, "サイフォンが起動し", 12),
            text(tx, tube_top + 54, "中身が全部抜ける", 12),
            text(tx, tube_top + 84, "竹の内管＋かぶせ管", 12, fill="#3f5a12"),
            text(tx, tube_top + 100, "（逆U字のサイフォン）", 12, fill="#3f5a12"),
            text(tx, y0 + 30 + h + 40, "↓ 下の桝へ（桁上り）", 12, fill=COL["flow"])]
    return out


# ------------------------------------------------------------------
# 図の組み立て
# ------------------------------------------------------------------
def render(model, pulses, W=1500, H=860):
    parts = {p["id"]: p for p in model["parts"]}
    u = model["units"]["u_mL"]
    vol = simulate(model, pulses)
    bits = bits_of(model, vol)
    iso = fit(model, (300, 170, 1060, H - 80))

    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
           f'font-family="{FONT}">', arrow_defs(),
           f'<rect width="{W}" height="{H}" fill="{COL["bg"]}"/>']

    m = model["meta"]
    svg += [text(36, 52, f"{m['title']} ― 3D斜め見下ろし模式図", 30, "bold"),
            text(36, 84, f"モデル定義：design/models/{m['id']}.yaml から自動生成。"
                         f"作成：{m['author']}（{m['created']}）。状態：{m['status']}", 15, fill=COL["sub"]),
            text(36, 108, "土器の器（教訓桝）を階段状に積む。上から1uずつ注ぐと、"
                          "各桝に残る水が2進数の各ビットになる。", 15, fill=COL["sub"])]

    # 器（奥から手前の順＝x の小さい順）
    geo = {}
    for p in sorted(model["parts"], key=lambda q: q["position"][0]):
        water = vol.get(p["id"], 0.0)
        if p["type"] == "metering_cup":
            water = p["volume_mL"]
        shapes, g = draw_vessel(iso, p, water, p["type"] == "siphon_cup")
        geo[p["id"]] = g
        svg += shapes

    # 流れ（つながり）
    for c in model["connections"]:
        a, b = parts[c["from"]], parts[c["to"]]
        ax, ay, az = a["position"]
        bx, by, bz = b["position"]
        _, _, _, _, abot = geo[a["id"]]
        _, btop, _, _, _ = geo[b["id"]]
        if c["kind"] == "pour":
            sx, sy = iso.p(ax + 2, ay, az + part_height(a))
            ex, ey = iso.p(bx, by, bz + part_height(b) + 2)
            svg.append(f'<path d="M{sx:.1f},{sy:.1f} Q{(sx + ex) / 2 + 30:.1f},{sy - 30:.1f} '
                       f'{ex:.1f},{ey:.1f}" fill="none" stroke="{COL["flow"]}" stroke-width="4" '
                       f'marker-end="url(#ah)"/>')
        else:
            # サイフォン出口：底から下へ出て、次の器の上へ（竹の管）
            sx, sy = iso.p(ax, ay, az)
            dx, dy = iso.p(ax, ay, az - 6)
            ex, ey = iso.p(bx, by, bz + part_height(b) + 3)
            d = f"M{sx:.1f},{sy:.1f} L{dx:.1f},{dy:.1f} Q{dx:.1f},{ey - 10:.1f} {ex:.1f},{ey:.1f}"
            svg.append(f'<path d="{d}" fill="none" stroke="{COL["tube"]}" stroke-width="7" '
                       f'stroke-linecap="round" stroke-opacity="0.8"/>')
            svg.append(f'<path d="{d}" fill="none" stroke="{COL["flow"]}" stroke-width="2" '
                       f'stroke-dasharray="6 5" marker-end="url(#ah)"/>')
            mx, my = (dx + ex) / 2, (dy + ey) / 2
            svg.append(text(mx + 4, my - 12, f"{c['amount_u']}u 落ちる", 13, "bold", COL["flow"]))

    # 注釈
    L = parts["L"]
    lcx, ltop, lrx, _, _ = geo["L"]
    svg += callout(lcx - lrx, ltop, 36, 140,
                   [(f"入力：{L['name']}", 14, "bold"),
                    ("溢れ口までちょうど1uを量り、", 12, "normal"),
                    ("S0 に一気に注ぐ（人の操作）", 12, "normal")], 230)

    for p in model["parts"]:
        if p["type"] != "siphon_cup":
            continue
        cx, top, rx, ry, bot = geo[p["id"]]
        has = vol[p["id"]] > 0
        svg += callout(cx - rx * 0.7, bot, cx - rx - 290, bot + 6,
                       [(f"{p['id']}：{p['name']}（bit{p['bit']}＝{p['weight_u']}u）", 14, "bold"),
                        (f"しきい値 θ = {p['threshold_mL'] / u:g}u（{p['threshold_mL']}mL）", 12, "normal"),
                        (f"容量 {p['capacity_mL']}mL／内径 {p['inner_diameter_cm']}cm", 12, "normal"),
                        (f"いま：{'水あり → 1' if has else '空 → 0'}", 12, "bold")], 255)

    o = parts["OUT"]
    ocx, otop, orx, _, _ = geo["OUT"]
    _, _, _, _, obot = geo["OUT"]
    svg += callout(ocx - orx * 0.7, obot, ocx - orx - 270, obot - 10,
                   [(f"{o['name']}", 14, "bold"),
                    ("16回目で S3 から16uが落ちる", 12, "normal"),
                    ("（4ビットを超えた桁上り）", 12, "normal")], 230)

    # 状態パネル
    px, py = 1100, 140
    svg += [f'<rect x="{px}" y="{py}" width="364" height="150" rx="8" fill="{COL["panel"]}" '
            f'stroke="{COL["panel_edge"]}"/>',
            text(px + 16, py + 30, f"図の状態：{pulses}回注いだ後", 17, "bold"),
            text(px + 16, py + 76, f"S3 S2 S1 S0 = {' '.join(bits)}", 26, "bold", COL["flow"]),
            text(px + 16, py + 108, f"＝ 2進数 {bits} ＝ {int(bits, 2)}", 16),
            text(px + 16, py + 134, "水が残っている桝＝1、空の桝＝0", 13, fill=COL["sub"])]

    # 凡例
    lx, ly = 1100, 310
    svg += [f'<rect x="{lx}" y="{ly}" width="364" height="140" rx="8" fill="{COL["panel"]}" '
            f'stroke="{COL["panel_edge"]}"/>',
            text(lx + 16, ly + 26, "凡例", 15, "bold"),
            f'<rect x="{lx + 16}" y="{ly + 38}" width="26" height="14" fill="{COL["wall"]}" '
            f'fill-opacity="0.4" stroke="{COL["wall_edge"]}"/>',
            text(lx + 52, ly + 50, "土器の器（教訓桝）", 13),
            f'<rect x="{lx + 16}" y="{ly + 62}" width="26" height="8" fill="{COL["tube"]}"/>',
            text(lx + 52, ly + 71, "竹の管（サイフォン）", 13),
            f'<line x1="{lx + 16}" y1="{ly + 90}" x2="{lx + 42}" y2="{ly + 90}" stroke="#c0392b" '
            f'stroke-width="2" stroke-dasharray="5 4"/>',
            text(lx + 52, ly + 95, "しきい値の高さ", 13),
            f'<line x1="{lx + 16}" y1="{ly + 116}" x2="{lx + 42}" y2="{ly + 116}" stroke="{COL["flow"]}" '
            f'stroke-width="3" marker-end="url(#ah)"/>',
            text(lx + 52, ly + 121, "水の流れ", 13)]

    svg += cross_section(1100, 470, parts["S0"], u)

    svg.append(text(W - 20, H - 18, "寸法は設計値（未試作）。❓の前提は YAML の assumptions を参照", 12,
                    fill=COL["sub"], anchor="end"))
    svg.append("</svg>")
    return "\n".join(svg)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("--pulses", type=int, default=5)
    ap.add_argument("-o", "--out", required=True)
    args = ap.parse_args()

    model = load_model(args.model)
    ok = True
    for n, want, got, good in check_expected(model):
        print(f"expected pulses={n:2d}: want {want} got {got} {'OK' if good else 'NG'}")
        ok &= good
    Path(args.out).write_text(render(model, args.pulses), encoding="utf-8")
    print(f"wrote {args.out}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
