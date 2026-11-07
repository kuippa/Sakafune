"""天秤で作るカウンタ機械（Minsky 機械）のシミュレーション。設計07のロジックの確認用。

使い方:
    python tools/counter_machine.py

作成：Claude Opus 5.5（2026-11-07）。外部ライブラリなし。結果の要約は design/07_counter-machine.md。

仕組み（水は足すだけ。抜く操作はない）：
  レジスタ r ＝ 天秤1本。値 n ＝（左の皿 A の水）−（右の皿 B の水）。右におもり 0.5u。
      INC r ：A に 1u 足す
      DEC r ：B に 1u 足す
      0 か？：A − B − 0.5u が正なら左が重い（n ≥ 1）、負なら右が重い（n = 0）
  命令 k ＝ 駅。駅の皿に「手番の水」（1u）があるときだけ、駅の天秤（門）が傾き、電源の水を通す。
  1回の手順（人は毎回同じ4つをするだけ。判断なし）：
      1. 次の手番：全部の駅に、電源の水 p2 を 1u ずつ注ぐ。手番のある駅だけが、次の駅の「控え」へ 1u を送る
         JZDEC は、送り先をレジスタの天秤の指し樋で決める（0 なら if_zero、それ以外なら next）
      2. 操作：全部の駅に、電源の水 p1 を 1u ずつ注ぐ。手番のある駅だけが INC（A へ）／DEC（B へ）をする
         （1 より先に 2 をすると、DEC した後の値で分岐してしまうので、この順番）
      3. 全部の駅の皿を空ける（停止の駅は空けない）
      4. 控えの水を駅の皿へ移す
  命令は INC と JZDEC（0 なら飛ぶ、そうでなければ 1 減らして進む）と HALT の3つ。Minsky のカウンタ機械と同じ。
"""
import random
import sys

sys.stdout.reconfigure(encoding="utf-8")

# 命令： ("INC", r, next) / ("JZDEC", r, if_zero, next) / ("HALT",)
PROGRAMS = {
    "足し算 r0 += r1": dict(regs=2, prog=[
        ("JZDEC", 1, 2, 1),   # 0: r1 が 0 なら停止へ、そうでなければ r1 を 1 減らして 1 へ
        ("INC", 0, 0),        # 1: r0 を 1 増やして 0 へ
        ("HALT",)]),
    "2倍 r0 = 2×r1": dict(regs=2, prog=[
        ("JZDEC", 1, 3, 1),
        ("INC", 0, 2),
        ("INC", 0, 0),
        ("HALT",)]),
    "掛け算 r2 = r0×r1（r3 は作業用）": dict(regs=4, prog=[
        ("JZDEC", 0, 6, 1),   # 0: r0 回くり返す
        ("JZDEC", 1, 4, 2),   # 1: r1 を r2 と r3 へ移す
        ("INC", 2, 3),
        ("INC", 3, 1),
        ("JZDEC", 3, 0, 5),   # 4: r3 を r1 へ戻す
        ("INC", 1, 4),
        ("HALT",)]),
}


class Machine:
    def __init__(self, regs, prog, init, sd=0.0, bias=0.0, cw=0.5):
        self.prog, self.sd = prog, sd
        self.A = [float(v) for v in init] + [0.0] * (regs - len(init))
        self.B = [0.0] * regs
        self.bias = [random.uniform(-bias, bias) for _ in range(regs)]   # 皿の狂い（u）
        self.cw = cw
        self.T = [0.0] * len(prog)       # 駅の皿（手番の水）
        self.T[0] = 1.0
        self.S = [0.0] * len(prog)       # 控え
        self.ticks = 0
        self.max_pan = 0.0

    def pour(self):
        return 1.0 + random.gauss(0, self.sd) if self.sd else 1.0

    def gate(self, k):                   # 駅の天秤：皿に手番の水があるか（中央の受け口の半幅 0.5u）
        return self.T[k] >= 0.5

    def nonzero(self, r):                # レジスタの天秤：左が重いか
        return self.A[r] + self.bias[r] - self.B[r] - self.cw > 0

    def halted(self):
        return any(self.T[k] >= 0.5 for k, ins in enumerate(self.prog) if ins[0] == "HALT")

    def tick(self):
        # 1. 次の手番（状態を読んでから）
        for k, ins in enumerate(self.prog):
            if ins[0] == "HALT" or not self.gate(k):
                continue
            q = self.pour()
            if ins[0] == "INC":
                self.S[ins[2]] += q
            else:
                self.S[ins[3] if self.nonzero(ins[1]) else ins[2]] += q
        # 2. 操作
        for k, ins in enumerate(self.prog):
            if ins[0] == "HALT" or not self.gate(k):
                continue
            q = self.pour()
            if ins[0] == "INC":
                self.A[ins[1]] += q
            elif self.nonzero(ins[1]):
                self.B[ins[1]] += q
        # 3, 4. 駅の皿を空け、控えを移す（停止の駅は空けない）
        for k, ins in enumerate(self.prog):
            if ins[0] != "HALT":
                self.T[k] = 0.0
            self.T[k] += self.S[k]
            self.S[k] = 0.0
        self.ticks += 1
        self.max_pan = max(self.max_pan, max(self.A + self.B))

    def run(self, max_ticks=10000):
        while not self.halted() and self.ticks < max_ticks:
            self.tick()
        return [round(a - b) for a, b in zip(self.A, self.B)]


def expected(name, x, y):
    if name.startswith("足し算"):
        return {0: x + y, 1: 0}
    if name.startswith("2倍"):
        return {0: 2 * y, 1: 0}
    return {0: 0, 1: y, 2: x * y, 3: 0}


def init_for(name, x, y):
    if name.startswith("足し算"):
        return [x, y]
    if name.startswith("2倍"):
        return [0, y]
    return [x, y]


# ---- 1. 理想（誤差なし）：小さな入力を全部試す ----
print("== 1. 誤差なし：0〜5 の入力を全部試す")
for name, P in PROGRAMS.items():
    ok = tot = 0
    worst_ticks = worst_pan = 0
    for x in range(6):
        for y in range(6):
            m = Machine(P["regs"], P["prog"], init_for(name, x, y))
            got = m.run()
            want = expected(name, x, y)
            ok += all(got[r] == v for r, v in want.items()) and m.halted()
            tot += 1
            worst_ticks = max(worst_ticks, m.ticks)
            worst_pan = max(worst_pan, m.max_pan)
    print(f"  {name}：{ok}/{tot} 正しい。最大 {worst_ticks} 手順、皿に溜まる水の最大 {worst_pan:.0f}u")

# ---- 2. 注ぐ量のばらつき ----
print("\n== 2. 注ぐ量のばらつき（各 300 回）。数字は答えが全部合っていた割合")
random.seed(11)
cases = [("足し算 r0 += r1", 3, 4), ("2倍 r0 = 2×r1", 0, 8), ("掛け算 r2 = r0×r1（r3 は作業用）", 3, 4)]
for name, x, y in cases:
    P = PROGRAMS[name]
    m0 = Machine(P["regs"], P["prog"], init_for(name, x, y))
    m0.run()
    row = []
    for sd in (0.01, 0.03, 0.05, 0.1):
        ok = 0
        for _ in range(300):
            m = Machine(P["regs"], P["prog"], init_for(name, x, y), sd=sd)
            got = m.run(max_ticks=5 * m0.ticks)
            ok += m.halted() and all(got[r] == v for r, v in expected(name, x, y).items())
        row.append(f"±{sd}u → {ok / 300:.0%}")
    print(f"  {name}（x={x}, y={y}、{m0.ticks} 手順）：" + "　".join(row))

# ---- 3. どこまで数えられるか ----
print("\n== 3. どこまで数えられるか（2倍 r0 = 2×r1 を y を増やして。各 200 回）")
random.seed(12)
name = "2倍 r0 = 2×r1"
P = PROGRAMS[name]
for sd in (0.01, 0.03, 0.05):
    row = []
    for y in (5, 10, 20, 40):
        ok = 0
        for _ in range(200):
            m = Machine(P["regs"], P["prog"], [0, y], sd=sd)
            got = m.run(max_ticks=10 * y + 10)
            ok += m.halted() and got[0] == 2 * y and got[1] == 0
        row.append(f"y={y} → {ok / 200:.0%}")
    print(f"  ±{sd}u：" + "　".join(row))

print("\n※ 水は足すだけなので、皿には「値」ではなく「INC・DEC の回数の合計」が溜まる。皿の大きさは計算の長さで決まる。")
print("※ 誤差は注ぐたびに積み重なる（値＝足した水の差）。長い計算には、すり切りの升の精度が要る。")
