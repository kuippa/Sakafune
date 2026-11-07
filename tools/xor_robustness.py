"""XOR 案の強さの検証：注いでいる途中で傾く／サイフォンが起動する場合や、注ぐ量の誤差を含めて調べる。

使い方:
    python tools/xor_robustness.py

render_iso.py のシミュレーションは「1u が一瞬で全部入る」理想化をしている。
このスクリプトは、1u を少しずつ注ぐ・注ぐ量がばらつく、という現実寄りの条件で各案を比べる。
作成：Claude Opus 5.5（2026-11-07）。結果の要約は design/04_sozu-xor.md と design/05_balance-xor.md。

1u を N 刻みで少しずつ注ぐ。各刻みのあとで部品が反応する。
  sozu   : 中身が θ 以上になった瞬間に、その時点の中身だけを出して空に戻る（注ぎ残りはまた溜まる）
  siphon : θ 以上で起動したら、その注ぎが終わるまでに入ってくる水も含めて全部出す
  holed  : θ を超えた分だけ穴から出る（時間に関係しない）
"""
import itertools
import random
import sys

sys.stdout.reconfigure(encoding="utf-8")

N = 200  # 1回の注ぎを何刻みに分けるか


class Cup:
    def __init__(self, kind, th):
        self.kind, self.th, self.v, self.draining = kind, th, 0.0, False

    def pour(self, amount, out):
        """amount を少しずつ注ぐ。出た水は out(量) で受け取る。"""
        for _ in range(N):
            self.v += amount / N
            if self.kind == "sozu" and self.v >= self.th:
                out(self.v)
                self.v = 0.0
            elif self.kind == "siphon":
                if self.v >= self.th:
                    self.draining = True
                if self.draining:
                    out(self.v)
                    self.v = 0.0
        self.draining = False  # 注ぎが終わり、出し切るとサイフォンは切れる


def design04(a, b, kind, th=1.5, pour=lambda: 1.0):
    """設計04：添水（または教訓桝）1つ＋受け樋＋予備の水 c, d"""
    cup = Cup(kind, th)
    got = {"W": 0.0, "Y1": 0.0, "Y0": 0.0}
    for x, route in ((a, "W"), (b, "W")):
        if x:
            cup.pour(pour(), lambda q, r=route: got.__setitem__(r, got[r] + q))
    cup.pour(pour(), lambda q: got.__setitem__("Y1", got["Y1"] + q))
    cup.pour(pour(), lambda q: got.__setitem__("Y0", got["Y0"] + q))
    return got, cup.v


def design02(a, b, hole=1.5, split=0.5, pour=lambda: 2.0):
    """設計02：穴あき桝4つ＋2本の溝。split は分水口が片側へ送る割合"""
    rails = {"a1": a, "a0": 1 - a, "b1": b, "b0": 1 - b}
    amt = {k: (pour() if on else 0.0) for k, on in rails.items()}
    cups = {"11": ("a1", "b1", "X0"), "10": ("a1", "b0", "X1"),
            "01": ("a0", "b1", "X1"), "00": ("a0", "b0", "X0")}
    # 各レールの水を、2つの桝へ split : 1-split で分ける
    first = {"a1": "11", "a0": "01", "b1": "11", "b0": "10"}
    inflow = {k: 0.0 for k in cups}
    for r, q in amt.items():
        targets = [c for c, (x, y, _) in cups.items() if r in (x, y)]
        a_, b_ = targets if targets[0] == first[r] else targets[::-1]
        inflow[a_] += q * split
        inflow[b_] += q * (1 - split)
    out = {"X1": 0.0, "X0": 0.0}
    for c, (_, _, to) in cups.items():
        out[to] += max(0.0, inflow[c] - hole)
    return out


def design05(a, b, deadband=0.5, pour=lambda: 1.0, pan_bias=0.0):
    """設計05：天秤＋指し樋。a を左の皿、b を右の皿へ。重さの差が deadband 未満なら中央（Y0）、
    それ以上なら左右（Y1）へ c が流れる。pan_bias は左右の皿の重さの狂い（u 換算）"""
    left = (pour() if a else 0.0) + pan_bias
    right = pour() if b else 0.0
    return "Y0" if abs(left - right) < deadband else "Y1"


def show(title, rows):
    print(f"\n== {title}")
    for r in rows:
        print("  " + r)


# ---- 1. 理想（一気に注ぐ）と、少しずつ注ぐ場合 ----
for kind, th in (("sozu", 1.5), ("siphon", 1.5), ("sozu", 1.9)):
    rows = []
    for a, b in itertools.product((0, 1), repeat=2):
        got, rest = design04(a, b, kind, th)
        want = "Y1" if a ^ b else "Y0"
        bad = [k for k in ("Y1", "Y0") if (got[k] > 0.05) != (k == want)]
        rows.append(f"a={a} b={b}: Y1={got['Y1']:.2f} Y0={got['Y0']:.2f} 残り={rest:.2f}  "
                    f"{'OK' if not bad else 'NG ' + str(bad)}")
    show(f"設計04 部品={kind} 傾く量θ={th}u（1u を少しずつ注ぐ）", rows)
    if kind == "sozu" and th == 1.5:
        print("  ※ この OK は、注ぎ残りがちょうど境目（1.5u）に乗った偶然。注ぐ量が 1% 多いだけで 3通りが間違える（下のばらつき試験を参照）")

# ---- 2. 注ぐ量のばらつきに対する強さ（モンテカルロ） ----
random.seed(1)
for kind, th in (("sozu", 1.5), ("sozu", 1.9), ("siphon", 1.5)):
    for sd in (0.03, 0.1):
        ok = tot = 0
        for _ in range(2000):
            for a, b in itertools.product((0, 1), repeat=2):
                got, _ = design04(a, b, kind, th, pour=lambda: random.gauss(1.0, sd))
                want = "Y1" if a ^ b else "Y0"
                ok += all((got[k] > 0.05) == (k == want) for k in ("Y1", "Y0"))
                tot += 1
        print(f"設計04 {kind} θ={th}u 注ぐ量のばらつき±{sd}u → 正答率 {ok / tot:.1%}")

for split in (0.5, 0.45, 0.4, 0.3):
    rows = []
    for a, b in itertools.product((0, 1), repeat=2):
        o = design02(a, b, split=split)
        want = "X1" if a ^ b else "X0"
        rows.append(f"a={a} b={b}: X1={o['X1']:.2f} X0={o['X0']:.2f} "
                    f"{'OK' if (o[want] > 0.05 and o['X1' if want == 'X0' else 'X0'] < 0.05) else 'NG'}")
    show(f"設計02 分水口の割合 {split:.2f}:{1 - split:.2f}", rows)

# ---- 3. 設計05：天秤＋指し樋 ----
print("\n== 設計05 天秤＋指し樋（注ぐ量のばらつき・皿の重さの狂いに対する正答率）")
random.seed(2)
for deadband in (0.5, 0.3):
    for sd in (0.03, 0.1, 0.2):
        for bias in (0.0, 0.2):
            ok = tot = 0
            for _ in range(5000):
                for a, b in itertools.product((0, 1), repeat=2):
                    got = design05(a, b, deadband, pour=lambda: random.gauss(1.0, sd), pan_bias=bias)
                    ok += got == ("Y1" if a ^ b else "Y0")
                    tot += 1
            print(f"  中央の受け口の半幅={deadband}u ばらつき±{sd}u 皿の狂い={bias}u → 正答率 {ok / tot:.2%}")
