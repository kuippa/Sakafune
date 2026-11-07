"""天秤 XOR（設計05）の竿の動きの簡易計算。ロジックが物理的に通るかを確かめるテスト段階のもの。

使い方:
    python tools/balance_dynamics.py

作成：Claude Opus 5.5（2026-11-07）。外部ライブラリなし（Python 本体だけ）。
流体は計算しない。水は「皿に一定の速さで増えていく重さ」と「落ちる勢い（運動量）」としてだけ扱う。

モデル（竿1本の回転だけを追う）：
  - 竿の両端（支点から L）に皿を吊る。皿は竿の端の点の重さとみなす（皿の振れは無視）
  - 支点の下 h に重り（指し樋を兼ねる）。竿が傾くと元に戻す力 ＝ 重さ×g×h×sinθ
    → 重さの差 Δm で止まる角度は tanθ = Δm・L / (重り×h)。差が小さいと少しだけ傾き、大きいと止め木まで傾く
  - 指し樋の先（支点の下 r）の左右のずれ x = r・sinθ。|x| < w なら中央の受け口（釣り合い＝XNOR）、それ以外は左右（XOR）
  - 止め木 ±θs。ぶつかると反発係数 e で跳ね返る
  - 揺れ止め（減衰）は減衰比 ζ で与える（皿の下に水を張る等の工夫で大きくできる）
  - 予備の水 c が指し樋を流れる間、樋の中の水（樋の長さの真ん中あたり）が竿を戻す向きに働く

θ は「左の皿が下がる向き」を正とする。数値はすべて仮の値（ハンガー・紙コップ程度の大きさ）。
"""
import math
import sys

sys.stdout.reconfigure(encoding="utf-8")

G = 9.8
DT = 5e-4


def base_params(**kw):
    p = dict(
        u=0.100,          # 1u = 水 100mL = 0.1kg
        L=0.15,           # 支点から皿までの腕の長さ [m]
        m_beam=0.05,      # 竿（支点の高さに重心）[kg]
        m_pan=0.02,       # 皿1つ [kg]
        m_bal=0.5,        # 支点の下の重り（指し樋を兼ねる）[kg]
        h=None,           # 重りの深さ [m]。None なら「差 0.5u でちょうど中央の受け口の縁」になるように決める
        r=0.10,           # 指し樋の先までの長さ [m]
        w=0.02,           # 中央の受け口の半幅 [m]
        stop_deg=25.0,    # 止め木の角度
        e=0.3,            # 止め木での反発係数
        zeta=0.3,         # 減衰比
        q=0.05,           # 注ぐ速さ [kg/s]（1u を 2 秒）
        H=0.10,           # 注ぐ高さ [m]（落ちる勢い）
        q_c=0.05,         # 予備の水 c の注ぐ速さ [kg/s]
        transit=0.2,      # c が指し樋を通る時間 [s]
    )
    p.update(kw)
    if p["h"] is None:
        th_edge = math.asin(p["w"] / p["r"])
        p["h"] = 0.5 * p["u"] * p["L"] / (p["m_bal"] * math.tan(th_edge))
    p["k"] = p["m_bal"] * G * p["h"]                       # 戻す力の強さ [N·m/rad]
    I_nom = p["m_beam"] * p["L"] ** 2 / 3 + p["m_bal"] * p["h"] ** 2 + (2 * p["m_pan"] + p["u"]) * p["L"] ** 2
    p["c"] = 2 * p["zeta"] * math.sqrt(p["k"] * I_nom)   # 減衰の強さ
    return p


def region(theta, p):
    return "中央" if abs(p["r"] * math.sin(theta)) < p["w"] else "左右"


def simulate(p, pours, t_end, watch=None):
    """pours: [(開始時刻, 行き先 'L'|'R'|'P', 量kg, 速さkg/s)]。'P' は指し樋（予備の水 c）。
    watch=(t0, t1) の間の指し樋の区画を集めて返す。"""
    th = om = 0.0
    mL = mR = 0.0
    regions = set()
    trace = []
    t = 0.0
    stop = math.radians(p["stop_deg"])
    v_fall = math.sqrt(2 * G * p["H"])
    while t < t_end:
        F_L = F_R = m_ptr = 0.0
        for t0, to, amt, q in pours:
            dur = amt / q
            if t0 <= t < t0 + dur:
                if to == "L":
                    mL += q * DT
                    F_L += q * v_fall
                elif to == "R":
                    mR += q * DT
                    F_R += q * v_fall
            if to == "P" and t0 <= t < t0 + dur + p["transit"]:
                m_ptr = q * min(p["transit"], t - t0, t0 + dur - t + p["transit"])
        I = (p["m_beam"] * p["L"] ** 2 / 3 + p["m_bal"] * p["h"] ** 2
             + (2 * p["m_pan"] + mL + mR) * p["L"] ** 2 + m_ptr * (p["r"] / 2) ** 2)
        tau = ((mL - mR) * G + F_L - F_R) * p["L"] * math.cos(th) \
            - (p["k"] + m_ptr * G * p["r"] / 2) * math.sin(th) - p["c"] * om
        om += tau / I * DT
        th += om * DT
        if th > stop:
            th, om = stop, (-p["e"] * om if om > 0 else om)
        elif th < -stop:
            th, om = -stop, (-p["e"] * om if om < 0 else om)
        t += DT
        if watch and watch[0] <= t <= watch[1]:
            regions.add(region(th, p))
        trace.append((t, th))
    return th, regions, trace


def xor_case(p, a, b, wait, order="ab"):
    """a, b を順に注ぎ（1u を 2 秒ずつ、0.5 秒あけて）、最後に注ぎ終えてから wait 秒後に c を注ぐ。
    c を注いでいる間ずっと、指し樋が正しい区画を指していれば True。"""
    pours, t = [], 0.0
    for name in order:
        on = a if name == "a" else b
        if on:
            pours.append((t, "L" if name == "a" else "R", p["u"], p["q"]))
            t += p["u"] / p["q"] + 0.5
    t_in = max(t - 0.5, 0.0)
    tc = t_in + wait
    dur_c = p["u"] / p["q_c"]
    pours.append((tc, "P", p["u"], p["q_c"]))
    _, regions, _ = simulate(p, pours, tc + dur_c + p["transit"], watch=(tc, tc + dur_c + p["transit"]))
    want = "左右" if a ^ b else "中央"
    return regions == {want}, regions


def min_wait(p, order="ab", step=0.25, limit=15.0):
    """4通りすべてが正しくなる、いちばん短い待ち時間（注ぎ終えてから c を注ぐまで）。"""
    w = 0.0
    while w <= limit:
        if all(xor_case(p, a, b, w, order)[0] for a in (0, 1) for b in (0, 1)):
            return w
        w += step
    return None


def fmt(w):
    return "15秒以上（だめ）" if w is None else f"{w:.2f} 秒"


# ---- 1. 止まる角度（静的）：差 0.5u が中央の受け口の縁になるように設計 ----
p = base_params()
print("== 1. 止まる角度（揺れが収まった後）")
print(f"  仮の寸法：腕 L={p['L'] * 100:.0f}cm、重り {p['m_bal'] * 1000:.0f}g を支点の下 h={p['h'] * 100:.1f}cm、"
      f"指し樋 r={p['r'] * 100:.0f}cm、中央の受け口の半幅 w={p['w'] * 100:.0f}cm、止め木 ±{p['stop_deg']:.0f}°")
for du in (0.0, 0.2, 0.4, 0.6, 0.8, 1.0):
    th = math.atan(du * p["u"] * G * p["L"] / p["k"])
    th = min(th, math.radians(p["stop_deg"]))
    print(f"  重さの差 {du:.1f}u → {math.degrees(th):5.1f}°、指し樋の先のずれ {p['r'] * math.sin(th) * 100:4.1f}cm → {region(th, p)}")

# ---- 2. 揺れ止めの強さと、c を注ぐまでに待つ時間 ----
I0 = p["m_beam"] * p["L"] ** 2 / 3 + p["m_bal"] * p["h"] ** 2 + (2 * p["m_pan"] + p["u"]) * p["L"] ** 2
print(f"  竿の揺れの周期（揺れ止めなし）：約 {2 * math.pi * math.sqrt(I0 / p['k']):.2f} 秒")

print("\n== 2. 4通りすべて正しくなるまでに待つ時間（a, b を注ぎ終えてから c を注ぐまで）")
print("  ゆっくり注ぐ（1u を 2 秒）／一気に注ぐ（1u を 0.3 秒、高さ 30cm）")
for zeta in (0.02, 0.05, 0.1, 0.3, 0.7, 1.0):
    pz = base_params(zeta=zeta)
    pf = base_params(zeta=zeta, q=0.33, H=0.3)
    print(f"  減衰比 ζ={zeta:<4} → ゆっくり {fmt(min_wait(pz))}（b が先でも {fmt(min_wait(pz, order='ba'))}）"
          f"／一気に {fmt(min_wait(pf))}（b が先でも {fmt(min_wait(pf, order='ba'))}）")

# ---- 3. 待たずに c を注いだらどうなるか ----
print("\n== 3. 待たずに c を注いだ場合（ζ=0.3）")
for a in (0, 1):
    for b in (0, 1):
        ok, regs = xor_case(p, a, b, 0.0)
        print(f"  a={a} b={b}: {'OK' if ok else 'NG'}　c を注いでいる間に指した区画 {sorted(regs)}")

# ---- 4. 指し樋を流れる c の重さ ----
print("\n== 4. 指し樋を流れる c の重さで、竿の傾きが戻らないか（差 1u、十分に待ってから c を注ぐ）")
for q_c, transit in ((0.05, 0.2), (0.2, 0.2), (0.5, 0.5), (1.0, 1.0)):
    pq = base_params(q_c=q_c, transit=transit)
    pours = [(0.0, "L", pq["u"], pq["q"]), (12.0, "P", pq["u"], q_c)]
    _, _, tr = simulate(pq, pours, 12.0 + pq["u"] / q_c + transit)
    before = [th for t, th in tr if 11.0 < t < 12.0]
    during = [th for t, th in tr if t >= 12.0]
    xb = pq["r"] * math.sin(before[-1]) * 100
    xmin = min(pq["r"] * math.sin(th) for th in during) * 100
    print(f"  c の速さ {q_c * 1000:.0f}g/秒、樋の中の水 最大{q_c * transit * 1000:.0f}g → 指し樋の先 {xb:.1f}cm → 最小 {xmin:.1f}cm"
          f"（中央の縁 {pq['w'] * 100:.0f}cm）{'OK' if xmin > pq['w'] * 100 else 'NG'}")

# ---- 5. 注ぎ方・作りのずれ ----
print("\n== 5. 注ぎ方・作りのずれ（ζ=0.3 で、4通りすべて正しくなるまでの待ち時間）")
for label, kw in (("基準", {}),
                  ("一気に注ぐ（1u を 0.3 秒、高さ 30cm）", dict(q=0.33, H=0.3)),
                  ("止め木の反発が大きい（e=0.8）", dict(e=0.8)),
                  ("重りが浅い（h を半分）", "half_h"),
                  ("重りが深い（h を2倍）", "double_h")):
    if kw == "half_h":
        pp = base_params(h=base_params()["h"] / 2)
    elif kw == "double_h":
        pp = base_params(h=base_params()["h"] * 2)
    else:
        pp = base_params(**kw)
    edge_du = pp["k"] * math.tan(math.asin(pp["w"] / pp["r"])) / (G * pp["L"]) / pp["u"]
    print(f"  {label}: {fmt(min_wait(pp))}（中央の受け口に入る重さの差 ±{edge_du:.2f}u 未満）")

print("\n※ 数値は仮の寸法・仮の減衰による。実物で「揺れが何秒で止まるか」を1回測れば、ζ を当てはめられる。")
