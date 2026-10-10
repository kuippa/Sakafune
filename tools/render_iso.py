"""YAMLのモデル定義から、3D斜め見下ろし（アイソメトリック）の模式図をSVGで描く。

使い方:
    python tools/render_iso.py design/models/level2_full_adder.yaml -o images/out.svg [--case a1b0c1]

- 図の寸法・しきい値・つながりは、すべてYAMLから読む（図はYAMLの写し）。書き方は design/models/SCHEMA.md。
- YAMLの cases（入力と期待される出力）を、すべて簡易シミュレーションで照合して結果を表示する。
  食い違いがあれば終了コード1で終わる。
- 図には --case（省略時は readout.default_case）を実行した後の水の状態を描く。
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
    "plug": "#8a5a2b",      # 木の栓・注ぎ口
    "water": "#3d8fd6",
    "water_top": "#8fc3ec",
    "flow": "#2f7fc8",
    "thr": "#c0392b",
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


class Sim:
    """部品の水量（mL）を持ち、操作ごとにサイフォン・溢れを落ち着くまで進める。"""

    def __init__(self, model):
        self.parts = {p["id"]: p for p in model["parts"]}
        self.vol = {pid: 0.0 for pid in self.parts}
        self.state = {pid: 0 for pid, p in self.parts.items() if p["type"] == "tipping_bucket"}

    def settle(self):
        changed = True
        while changed:
            changed = False
            for pid, p in self.parts.items():
                v = self.vol[pid]
                if p["type"] == "siphon_cup" and v >= p["threshold_mL"] - 1e-9:
                    self.vol[p["siphon_to"]] += v
                    self.vol[pid] = 0.0
                    changed = True
                elif p["type"] == "holed_cup" and v > p["hole_mL"] + 1e-9:
                    self.vol[p["hole_to"]] += v - p["hole_mL"]
                    self.vol[pid] = p["hole_mL"]
                    changed = True
                elif p["type"] == "tipping_bucket" and v >= p["compartment_mL"] - 1e-9:
                    # 上を向いている升が満ちると傾いて中身を出し、向きが入れ替わる
                    self.vol[pid] -= p["compartment_mL"]
                    self.vol[p["dump_to"][self.state[pid]]] += p["compartment_mL"]
                    self.state[pid] ^= 1
                    changed = True
                elif p["type"] == "vane" and v > 1e-9:
                    # 振り分け板：つながった両升の向きで行き先が決まる
                    self.vol[p["route_to"][self.state[p["bucket"]]]] += v
                    self.vol[pid] = 0.0
                    changed = True
                elif p["type"] == "splitter" and v > 1e-9:
                    for t in p["split_to"]:
                        self.vol[t] += v / len(p["split_to"])
                    self.vol[pid] = 0.0
                    changed = True
                elif p["type"] == "metering_cup" and v > p["volume_mL"] + 1e-9:
                    extra = v - p["volume_mL"]
                    self.vol[pid] = p["volume_mL"]
                    if p.get("overflow_to"):
                        self.vol[p["overflow_to"]] += extra
                    changed = True

    def do(self, step):
        if "fill" in step:
            p = self.parts[step["fill"]]
            self.vol[p["id"]] = p["volume_mL"]
        elif "release" in step:
            pid = step["release"]
            self.vol[self.parts[pid]["drain_to"]] += self.vol[pid]
            self.vol[pid] = 0.0
        self.settle()


def run_case(model, case):
    sim = Sim(model)
    for pid, on in (case.get("inputs") or {}).items():
        if on:
            sim.do({"fill": pid})
    for _ in range(case.get("repeat", 1)):
        for step in model["procedure"]:
            sim.do(step)
    return sim


def check_cases(model):
    results = []
    for case in model.get("cases", []):
        vol = run_case(model, case).vol
        got = {k: int(vol[k] > 1e-9) for k in case["expect"]}
        results.append((case["id"], case["expect"], got, got == case["expect"]))
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
    if part["type"] in ("siphon_cup", "basin", "holed_cup"):
        return height_cm(part, part["capacity_mL"])
    if part["type"] == "splitter":
        return 3
    if part["type"] in ("tipping_bucket", "vane"):
        return 8
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


def draw_tipping(iso, part, state, water_ml):
    """両升（左右に升がある転倒升）と振り分け板の模式。向き（state）で傾きを変える。"""
    x, y, z = part["position"]
    cx, base = iso.p(x, y, z)
    _, pivot = iso.p(x, y, z + 6)
    s = iso.s
    ang = -22 if state == 0 else 22   # 0：左の升が上（受ける側）
    out = [f'<line x1="{cx:.1f}" y1="{base:.1f}" x2="{cx:.1f}" y2="{pivot:.1f}" stroke="{COL["plug"]}" stroke-width="5"/>']
    if part["type"] == "tipping_bucket":
        w, h = 7 * s, 3.2 * s
        g = [f'<g transform="rotate({ang} {cx:.1f} {pivot:.1f})">',
             f'<path d="M{cx - w:.1f},{pivot - h:.1f} L{cx - w:.1f},{pivot:.1f} L{cx + w:.1f},{pivot:.1f} '
             f'L{cx + w:.1f},{pivot - h:.1f} M{cx:.1f},{pivot:.1f} L{cx:.1f},{pivot - h * 1.1:.1f}" '
             f'fill="{COL["wall"]}" fill-opacity="0.35" stroke="{COL["wall_edge"]}" stroke-width="2.5"/>']
        if water_ml > 1e-9:
            fr = min(1, water_ml / part["compartment_mL"])
            g.append(f'<rect x="{cx - w + 2:.1f}" y="{pivot - h * fr:.1f}" width="{w - 4:.1f}" '
                     f'height="{h * fr - 1:.1f}" fill="{COL["water"]}" fill-opacity="0.75"/>')
        g.append("</g>")
        out += g
        out.append(f'<circle cx="{cx:.1f}" cy="{pivot:.1f}" r="4" fill="#4a2e12"/>')
        out.append(text(cx, base + 18, f"向き {state}", 13, "bold", COL["thr"], anchor="middle"))
        geo = {"cx": cx, "top": pivot - h * 1.6, "rx": w, "ry": h * 0.5, "bot": base}
    else:  # vane
        L = 6 * s
        out.append(f'<line x1="{cx:.1f}" y1="{pivot:.1f}" x2="{cx:.1f}" y2="{pivot + L:.1f}" '
                   f'stroke="{COL["plug"]}" stroke-width="6" stroke-linecap="round" '
                   f'transform="rotate({ang} {cx:.1f} {pivot:.1f})"/>')
        out.append(f'<circle cx="{cx:.1f}" cy="{pivot:.1f}" r="4" fill="#4a2e12"/>')
        geo = {"cx": cx, "top": pivot - 6, "rx": 3 * s, "ry": 2 * s, "bot": pivot + L * 0.9}
    if part.get("tag"):
        out.append(text(cx, geo["bot"] + 36, part["tag"], 14, "bold", anchor="middle"))
    return out, geo


def draw_vessel(iso, part, water_ml):
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
    if water_ml > 1e-9:
        wh = min(height_cm(part, water_ml), h)
        wbody, (wcx, wtop, wrx, wry), _ = cylinder_shape(iso, x, y, z, z + wh, r * 0.97)
        out.append(f'<path d="{wbody}" fill="{COL["water"]}" fill-opacity="0.75"/>')
        out.append(f'<ellipse cx="{wcx:.1f}" cy="{wtop:.1f}" rx="{wrx:.1f}" ry="{wry:.1f}" '
                   f'fill="{COL["water_top"]}"/>')
    if part["type"] == "siphon_cup":
        # 内側の管（しきい値の高さまで）
        th = height_cm(part, part["threshold_mL"])
        tx, ty0 = iso.p(x, y, z)
        _, ty1 = iso.p(x, y, z + th)
        w = max(2.5, part.get("siphon_tube_inner_diameter_mm", 5) * 0.12 * iso.s)
        out.append(f'<rect x="{tx - w:.1f}" y="{ty1 - w:.1f}" width="{2 * w:.1f}" '
                   f'height="{ty0 - ty1 + w:.1f}" rx="{w:.1f}" fill="{COL["tube"]}" '
                   f'fill-opacity="0.85" stroke="#3f5a12" stroke-width="1"/>')
        # しきい値の線（器の壁に引いた目盛り）
        _, lt = iso.p(x, y, z + th)
        out.append(f'<ellipse cx="{cx:.1f}" cy="{lt:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" fill="none" '
                   f'stroke="{COL["thr"]}" stroke-width="1.4" stroke-dasharray="5 4"/>')
    if part["type"] == "holed_cup":
        hh = height_cm(part, part["hole_mL"])
        _, lt = iso.p(x, y, z + hh)
        out.append(f'<ellipse cx="{cx:.1f}" cy="{lt:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" fill="none" '
                   f'stroke="{COL["thr"]}" stroke-width="1.4" stroke-dasharray="5 4"/>')
    if part["type"] == "metering_cup" and part.get("overflow_to"):
        # 溢れ口（縁の切り欠き）
        out.append(f'<rect x="{cx + rx - 5:.1f}" y="{top - 2:.1f}" width="10" height="6" '
                   f'fill="{COL["bg"]}" stroke="{COL["wall_edge"]}" stroke-width="1.5"/>')
    # 手前の壁と縁
    out.append(f'<path d="{body}" fill="{COL["wall"]}" fill-opacity="0.22" '
               f'stroke="{COL["wall_edge"]}" stroke-width="2"/>')
    out.append(f'<ellipse cx="{cx:.1f}" cy="{top:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" fill="none" '
               f'stroke="{COL["wall_edge"]}" stroke-width="2"/>')
    if part["type"] == "holed_cup":
        # 側面の穴（右手前、穴の高さ）
        _, lt = iso.p(x, y, z + height_cm(part, part["hole_mL"]))
        out.append(f'<ellipse cx="{cx + rx * 0.8:.1f}" cy="{lt + ry * 0.6:.1f}" rx="4.5" ry="5.5" '
                   f'fill="#2b1a0c" stroke="{COL["thr"]}" stroke-width="1"/>')
    if part["type"] == "siphon_cup" and part.get("drain_to"):
        # 栓（手前の壁の下のほう）
        px, py = cx + rx * 0.55, bot + ry * 0.55
        out.append(f'<rect x="{px - 5:.1f}" y="{py - 9:.1f}" width="10" height="12" rx="2" '
                   f'fill="{COL["plug"]}" stroke="#4a2e12"/>')
    if part.get("tag"):
        out.append(text(cx, bot + ry + 18, part["tag"], 14, "bold", anchor="middle"))
    return out, {"cx": cx, "top": top, "rx": rx, "ry": ry, "bot": bot}


def arrow_defs():
    return f"""<defs>
  <marker id="ah" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
    <path d="M0,0 L10,5 L0,10 z" fill="{COL['flow']}"/></marker>
  <marker id="ahk" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
    <path d="M0,0 L10,5 L0,10 z" fill="{COL['sub']}"/></marker>
</defs>"""


def text_width(t, size):
    return sum(size * (0.55 if ord(c) < 128 else 1.0) for c in t)


def callout(px, py, bx, by, lines, width=None):
    """(px,py) を指す矢印つきの注釈の箱。lines=[(text, size, weight)]"""
    width = width or max(text_width(t, sz) for t, sz, _ in lines) + 22
    lh = [l[1] + 6 for l in lines]
    h = sum(lh) + 14
    # 箱の辺のうち、指す点に近い側から線を出す
    sx = bx + width if px > bx + width else (bx if px < bx else px)
    sy = by + h if py > by + h else (by if py < by else by + h / 2)
    out = [f'<line x1="{sx:.1f}" y1="{sy:.1f}" x2="{px:.1f}" y2="{py:.1f}" '
           f'stroke="{COL["sub"]}" stroke-width="1.3" marker-end="url(#ahk)"/>',
           f'<rect x="{bx:.1f}" y="{by:.1f}" width="{width:.0f}" height="{h:.1f}" rx="6" '
           f'fill="{COL["panel"]}" stroke="{COL["panel_edge"]}"/>']
    yy = by + 8
    for (t, size, weight), d in zip(lines, lh):
        yy += d
        out.append(text(bx + 10, yy - 4, t, size, weight))
    return out


def callout_lines(part, vol_ml, u, inputs):
    lines = [(f"{part['id']}：{part['name']}", 14, "bold")]
    if part["type"] == "siphon_cup":
        lines.append((f"しきい値 θ = {part['threshold_mL'] / u:g}u（{part['threshold_mL']}mL）"
                      f"／容量 {part['capacity_mL']}mL", 12, "normal"))
    if part["type"] == "holed_cup":
        lines.append((f"穴の高さ = {part['hole_mL'] / u:g}u（{part['hole_mL']}mL）"
                      f"／容量 {part['capacity_mL']}mL", 12, "normal"))
    for n in part.get("notes", []):
        lines.append((n, 12, "normal"))
    if part["type"] in ("splitter", "tipping_bucket", "vane"):
        return lines
    if part["id"] in inputs:
        v = int(bool(inputs[part["id"]]))
        lines.append((f"入力値：{v}（{'1u 満たして注いだ' if v else '空のまま'}）", 12, "bold"))
        return lines
    state = f"水あり（{vol_ml / u:g}u）→ 1" if vol_ml > 1e-9 else "空 → 0"
    lines.append((f"いま：{state}", 12, "bold"))
    return lines


def cross_section(x0, y0, cup, u):
    """教訓桝の断面図（説明用の小窓）。寸法は模式。"""
    w, h = 150, 150
    th_ratio = cup["threshold_mL"] / cup["capacity_mL"]
    lvl = y0 + 30 + h * (1 - th_ratio * 0.95)
    tube_top = y0 + 30 + h * (1 - th_ratio)
    cx = x0 + 30 + w / 2
    base = y0 + 30 + h
    out = [f'<rect x="{x0}" y="{y0}" width="{w + 220}" height="{h + 110}" rx="8" '
           f'fill="{COL["panel"]}" stroke="{COL["panel_edge"]}"/>',
           text(x0 + 14, y0 + 22, "教訓桝の断面（模式）", 15, "bold"),
           f'<path d="M{x0 + 30},{y0 + 30} L{x0 + 30},{base} L{x0 + 30 + w},{base} '
           f'L{x0 + 30 + w},{y0 + 30}" fill="none" stroke="{COL["wall_edge"]}" stroke-width="3"/>',
           f'<rect x="{x0 + 32}" y="{lvl:.1f}" width="{w - 4}" height="{base - lvl - 2:.1f}" '
           f'fill="{COL["water"]}" fill-opacity="0.55"/>',
           f'<path d="M{cx - 6},{base + 30} L{cx - 6},{tube_top:.1f} M{cx + 6},{base + 30} '
           f'L{cx + 6},{tube_top:.1f}" stroke="{COL["tube"]}" stroke-width="4" fill="none"/>',
           f'<path d="M{cx - 16},{base - 6} L{cx - 16},{tube_top - 10:.1f} Q{cx},{tube_top - 24:.1f} '
           f'{cx + 16},{tube_top - 10:.1f} L{cx + 16},{base - 6}" stroke="{COL["tube"]}" '
           f'stroke-width="3" fill="none"/>',
           f'<line x1="{x0 + 30}" y1="{tube_top:.1f}" x2="{x0 + 30 + w}" y2="{tube_top:.1f}" '
           f'stroke="{COL["thr"]}" stroke-width="1.5" stroke-dasharray="5 4"/>',
           f'<line x1="{cx}" y1="{base + 8}" x2="{cx}" y2="{base + 34}" '
           f'stroke="{COL["flow"]}" stroke-width="3" marker-end="url(#ah)"/>']
    tx = x0 + 30 + w + 16
    out += [text(tx, tube_top + 4, f"しきい値 θ（{cup['threshold_mL'] / u:g}u）", 13, "bold", COL["thr"]),
            text(tx, tube_top + 22, "ここを超えると", 12),
            text(tx, tube_top + 38, "サイフォンが起動し", 12),
            text(tx, tube_top + 54, "中身が全部抜ける", 12),
            text(tx, tube_top + 84, "竹の内管＋かぶせ管", 12, fill="#3f5a12"),
            text(tx, tube_top + 100, "（逆U字のサイフォン）", 12, fill="#3f5a12"),
            text(tx, base + 40, "↓ サイフォン出口", 12, fill=COL["flow"])]
    if cup.get("drain_to"):
        out += [f'<rect x="{x0 + 30 + w - 10}" y="{base - 22}" width="16" height="12" rx="2" '
                f'fill="{COL["plug"]}" stroke="#4a2e12"/>',
                text(x0 + 30, base + 62, "■ 栓（後の段階で抜く）", 12, fill=COL["plug"])]
    return out


def readout_panel(model, case, vol, x, y):
    ro = model["readout"]
    out = []
    if ro["kind"] == "binary":
        bits = "".join("1" if vol[i] > 1e-9 else "0" for i in ro["order"])
        title = f"図の状態：{case.get('repeat', 1)}回注いだ後"
        out += [text(x + 16, y + 76, f"{' '.join(ro['order'])} = {' '.join(bits)}", 24, "bold", COL["flow"]),
                text(x + 16, y + 108, f"＝ 2進数 {bits} ＝ {int(bits, 2)}", 16)]
    else:
        title = f"図の状態：case {case['id']} の後"
        ins = "　".join(f"{i['label']}={int(bool((case.get('inputs') or {}).get(i['id'])))}"
                       for i in ro.get("inputs", []))
        outs = "　".join(f"{i['label']}={int(vol[i['id']] > 1e-9)}" for i in ro["items"])
        out += [text(x + 16, y + 66, f"入力：{ins}", 16),
                text(x + 16, y + 100, f"出力：{outs}", 20, "bold", COL["flow"])]
    out = [f'<rect x="{x}" y="{y}" width="364" height="150" rx="8" fill="{COL["panel"]}" '
           f'stroke="{COL["panel_edge"]}"/>', text(x + 16, y + 30, title, 17, "bold")] + out
    out.append(text(x + 16, y + 134, "水が残っている器＝1、空の器＝0", 13, fill=COL["sub"]))
    return out


def procedure_panel(model, x, y):
    lines = []
    for s in model["procedure"]:
        act = f"{s['fill']} を満たす" if "fill" in s else f"{s['release']} の栓を抜く／注ぐ"
        lines.append(f"{s.get('phase', '')}：{act}")
    h = 40 + 20 * len(lines)
    out = [f'<rect x="{x}" y="{y}" width="364" height="{h}" rx="8" fill="{COL["panel"]}" '
           f'stroke="{COL["panel_edge"]}"/>', text(x + 16, y + 26, "人の操作（判断なし・この順に）", 15, "bold")]
    for i, l in enumerate(lines):
        out.append(text(x + 16, y + 50 + 20 * i, f"{i + 1}. {l}", 13))
    return out, h


def legend(x, y):
    return [f'<rect x="{x}" y="{y}" width="364" height="140" rx="8" fill="{COL["panel"]}" '
            f'stroke="{COL["panel_edge"]}"/>',
            text(x + 16, y + 26, "凡例", 15, "bold"),
            f'<rect x="{x + 16}" y="{y + 38}" width="26" height="14" fill="{COL["wall"]}" '
            f'fill-opacity="0.4" stroke="{COL["wall_edge"]}"/>',
            text(x + 52, y + 50, "土器の器", 13),
            f'<rect x="{x + 190}" y="{y + 38}" width="10" height="13" rx="2" fill="{COL["plug"]}"/>',
            text(x + 210, y + 50, "木の栓", 13),
            f'<rect x="{x + 16}" y="{y + 62}" width="26" height="8" fill="{COL["tube"]}"/>',
            text(x + 52, y + 71, "竹の管（サイフォン）", 13),
            f'<line x1="{x + 16}" y1="{y + 90}" x2="{x + 42}" y2="{y + 90}" stroke="{COL["thr"]}" '
            f'stroke-width="2" stroke-dasharray="5 4"/>',
            text(x + 52, y + 95, "しきい値・穴の高さ", 13),
            f'<line x1="{x + 16}" y1="{y + 116}" x2="{x + 42}" y2="{y + 116}" stroke="{COL["flow"]}" '
            f'stroke-width="3" marker-end="url(#ah)"/>',
            text(x + 52, y + 121, "水の流れ（緑の管＝サイフォン、茶の点線＝栓・注ぎ）", 12)]


# ------------------------------------------------------------------
# 図の組み立て
# ------------------------------------------------------------------
def connections(model):
    """parts の siphon_to / drain_to / overflow_to から、流れの一覧を作る。"""
    out = []
    for p in model["parts"]:
        for key in ("siphon_to", "drain_to", "overflow_to", "hole_to"):
            if p.get(key):
                out.append((p, key, p[key]))
        for t in p.get("split_to", []):
            out.append((p, "split_to", t))
        for i, t in enumerate(p.get("dump_to", [])):
            out.append((p, f"dump_to{i}", t))
        for i, t in enumerate(p.get("route_to", [])):
            out.append((p, f"route_to{i}", t))
    return out


def render(model, case, W=1500, H=None):
    parts = {p["id"]: p for p in model["parts"]}
    H = H or max(860, 475 + 40 + 20 * len(model["procedure"]) + 300)
    u = model["units"]["u_mL"]
    sim = run_case(model, case)
    vol = sim.vol
    box = model.get("layout", {}).get("fit_box", [300, 190, 1060, H - 80])
    iso = fit(model, tuple(box[:3]) + (box[3] if box[3] > 0 else H + box[3],))

    m = model["meta"]
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
           f'font-family="{FONT}">', arrow_defs(),
           f'<rect width="{W}" height="{H}" fill="{COL["bg"]}"/>',
           text(36, 52, f"{m['title']} ― 3D斜め見下ろし模式図", 30, "bold"),
           text(36, 84, f"モデル定義：design/models/{m['id']}.yaml から自動生成。"
                        f"作成：{m['author']}（{m['created']}）。状態：{m['status']}", 15, fill=COL["sub"]),
           text(36, 108, m.get("caption", ""), 15, fill=COL["sub"])]

    # 器（奥から手前の順に描く）
    geo = {}
    for p in sorted(model["parts"], key=lambda q: q["position"][0] + q["position"][1]):
        if p["type"] in ("tipping_bucket", "vane"):
            st = sim.state[p["id"] if p["type"] == "tipping_bucket" else p["bucket"]]
            shapes, g = draw_tipping(iso, p, st, vol.get(p["id"], 0.0))
        else:
            shapes, g = draw_vessel(iso, p, vol.get(p["id"], 0.0))
        geo[p["id"]] = g
        svg += shapes

    # 流れ
    for a, kind, to in connections(model):
        b = parts[to]
        ax, ay, az = a["position"]
        bx, by, bz = b["position"]
        ex, ey = iso.p(bx, by, bz + part_height(b) + 3)
        g = geo[a["id"]]
        if kind == "siphon_to":
            sx, sy = iso.p(ax, ay, az)
            dx, dy = iso.p(ax, ay, az - 6)
            d = f"M{sx:.1f},{sy:.1f} L{dx:.1f},{dy:.1f} Q{dx:.1f},{ey - 10:.1f} {ex:.1f},{ey:.1f}"
            svg.append(f'<path d="{d}" fill="none" stroke="{COL["tube"]}" stroke-width="7" '
                       f'stroke-linecap="round" stroke-opacity="0.8"/>')
            svg.append(f'<path d="{d}" fill="none" stroke="{COL["flow"]}" stroke-width="2" '
                       f'stroke-dasharray="6 5" marker-end="url(#ah)"/>')
        elif kind == "drain_to":
            if a["type"] == "metering_cup":   # 注ぐ（縁から）
                sx, sy = g["cx"] + g["rx"], g["top"]
                d = f"M{sx:.1f},{sy:.1f} Q{(sx + ex) / 2 + 20:.1f},{min(sy, ey) - 30:.1f} {ex:.1f},{ey:.1f}"
            else:                             # 栓から
                sx, sy = g["cx"] + g["rx"] * 0.55, g["bot"] + g["ry"] * 0.55
                d = f"M{sx:.1f},{sy:.1f} Q{sx + 10:.1f},{ey:.1f} {ex:.1f},{ey:.1f}"
            svg.append(f'<path d="{d}" fill="none" stroke="{COL["plug"]}" stroke-width="2.5" '
                       f'stroke-dasharray="7 5" marker-end="url(#ah)"/>')
        elif kind == "hole_to":
            _, ly = iso.p(ax, ay, az + height_cm(a, a["hole_mL"]))
            sx, sy = g["cx"] + g["rx"] * 0.8, ly + g["ry"] * 0.6
            d = f"M{sx:.1f},{sy:.1f} Q{sx + 25:.1f},{sy:.1f} {ex:.1f},{ey:.1f}"
            svg.append(f'<path d="{d}" fill="none" stroke="{COL["flow"]}" stroke-width="3" '
                       f'marker-end="url(#ah)"/>')
        elif kind.startswith(("dump_to", "route_to")):
            i = int(kind[-1])
            sx = g["cx"] + (-1 if i == 0 else 1) * g["rx"] * 0.9
            sy = g["bot"] - (g["bot"] - g["top"]) * 0.4
            dash = "7 5" if kind.startswith("dump") else "none"
            colr = COL["plug"] if kind.startswith("dump") else COL["flow"]
            d = f"M{sx:.1f},{sy:.1f} Q{sx:.1f},{ey - 10:.1f} {ex:.1f},{ey:.1f}"
            svg.append(f'<path d="{d}" fill="none" stroke="{colr}" stroke-width="2.5" '
                       f'stroke-dasharray="{dash}" marker-end="url(#ah)"/>')
            lab = ("向き0のとき" if i == 0 else "向き1のとき")
            if len(set(a.get("dump_to", a.get("route_to", [])))) > 1:  # 行き先が同じなら書かない
                svg.append(text((sx + ex) / 2 + (-50 if i == 0 else 8), (sy + ey) / 2, lab, 12, "bold", colr))
        elif kind == "split_to":
            sx, sy = g["cx"], g["bot"]
            d = f"M{sx:.1f},{sy:.1f} Q{sx:.1f},{ey - 20:.1f} {ex:.1f},{ey:.1f}"
            svg.append(f'<path d="{d}" fill="none" stroke="{COL["flow"]}" stroke-width="2" '
                       f'stroke-dasharray="4 3" stroke-opacity="0.8" marker-end="url(#ah)"/>')
        else:  # overflow_to
            sx, sy = g["cx"] + g["rx"], g["top"]
            d = f"M{sx:.1f},{sy:.1f} Q{sx + 20:.1f},{ey:.1f} {ex:.1f},{ey:.1f}"
            svg.append(f'<path d="{d}" fill="none" stroke="{COL["sub"]}" stroke-width="1.6" '
                       f'stroke-dasharray="3 4" marker-end="url(#ahk)"/>')

    # 両升と振り分け板が同じ軸でつながっていることを示す
    for p in model["parts"]:
        if p["type"] == "vane":
            a, b = geo[p["id"]], geo[p["bucket"]]
            svg.append(f'<line x1="{a["cx"]:.1f}" y1="{a["top"] + 6:.1f}" x2="{b["cx"]:.1f}" '
                       f'y2="{b["top"] + b["ry"] * 3.2:.1f}" stroke="#4a2e12" stroke-width="3" '
                       f'stroke-dasharray="2 4"/>')
            svg.append(text((a["cx"] + b["cx"]) / 2, (a["top"] + b["top"]) / 2 + 4, "同じ軸", 12,
                            "bold", "#4a2e12", anchor="middle"))

    # 注釈
    for p in model["parts"]:
        if p.get("hide_callout"):
            continue
        g = geo[p["id"]]
        dx, dy = p.get("callout", [-290, 6])
        ax, ay = g["cx"] - g["rx"], g["bot"]
        svg += callout(g["cx"] - g["rx"] * 0.7, g["bot"], ax + dx, ay + dy,
                       callout_lines(p, vol.get(p["id"], 0.0), u, case.get("inputs") or {}))

    # 右側のパネル
    px = 1100
    svg += readout_panel(model, case, vol, px, 140)
    proc, ph = procedure_panel(model, px, 305)
    svg += proc
    svg += legend(px, 320 + ph)
    cups = [p for p in model["parts"] if p["type"] == "siphon_cup"]
    if cups:
        svg += cross_section(px, 475 + ph, cups[0], u)

    svg.append(text(W - 20, H - 18, "寸法は設計値（未試作）。❓の前提は YAML の assumptions を参照", 12,
                    fill=COL["sub"], anchor="end"))
    svg.append("</svg>")
    return "\n".join(svg)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("--case", help="図に描く case の id（省略時は readout.default_case）")
    ap.add_argument("-o", "--out", required=True)
    args = ap.parse_args()

    model = load_model(args.model)
    ok = True
    for cid, want, got, good in check_cases(model):
        print(f"case {cid:8s}: want {want} got {got} {'OK' if good else 'NG'}")
        ok &= good
    cid = args.case or model["readout"].get("default_case") or model["cases"][0]["id"]
    case = next(c for c in model["cases"] if c["id"] == cid)
    Path(args.out).write_text(render(model, case), encoding="utf-8")
    print(f"wrote {args.out}（case {cid}）")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
