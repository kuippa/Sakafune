"""天秤で作る全加算器・多ビット加算器の強さの検証。

使い方:
    python tools/adder_robustness.py

作成：Claude Opus 5.5（2026-11-07）。結果の要約は design/06_balance-full-adder.md。

比べる方式（どれも人の操作は判断なし）：
  本命（設計06）：1ビットに天秤3つ。B1 = a XOR b、B2 = (a XOR b) XOR c、BM = 多数決（おもり 1.5u と比べる）。
                  天秤は「釣り合い／傾き」の2〜3通りしか読まない（傾くときは止め木まで）。
                  a, b, c は2つの天秤で使う。その配り方を2通り比べる：
                    fanout="pointer"（採用）：入力は 1u ずつ2回注ぐ。桁上りは BM の竿に指し樋を2本つけ、
                                              それぞれに予備の水 1u を注いで、1u の桁上りを2本作る
                    fanout="split"          ：入力も桁上りも 2u にして、分水口で 1u ずつに分ける
  別案（目盛り天秤）：1ビットに天秤1つ。左の皿に a, b, c、右におもり 1.5u。
                  竿の傾きが重さの差に比例する天秤として、傾きの「量」を読む。
                  指し樋2本：和は受け口4つ（差 -1.5, -0.5, +0.5, +1.5u → 0, 1, 0, 1）、桁上りは左右2つ。

誤差の入れ方：
  sd      : 注ぐ量のばらつき（1u あたりの標準偏差。2u なら同じ割合）
  split   : 分水口の偏り（片側へ行く割合の標準偏差。0.05 なら 50%±5%）
  bias    : 天秤ごとの皿の重さの狂い（-bias〜+bias の一様乱数、u 換算）
  gain    : 別案のみ。傾きと重さの差の比例のずれ（標準偏差、割合）
"""
import itertools
import random
import sys

sys.stdout.reconfigure(encoding="utf-8")

DEADBAND = 0.5  # 中央の受け口の半幅（u）


def pour(amount, sd):
    return amount * (1 + random.gauss(0, sd)) if sd else amount


def split(q, sd):
    r = 0.5 + random.gauss(0, sd) if sd else 0.5
    return q * r, q * (1 - r)


def add_main(A, B, n, sd=0.0, split_sd=0.0, bias=0.0, cw_sd=0.0, fanout="pointer"):
    """本命：天秤3つ／ビット。和のビット列と最後の桁上りを整数で返す。"""

    def two(on):  # 1つの信号を2つの皿へ配る
        if not on:
            return 0.0, 0.0
        if fanout == "pointer":
            return pour(1, sd), pour(1, sd)
        return split(pour(2, sd), split_sd)

    total, carry = 0, (0.0, 0.0)
    for i in range(n):
        a, b = (A >> i) & 1, (B >> i) & 1
        bb = [random.uniform(-bias, bias) for _ in range(3)]  # 3つの天秤それぞれの狂い
        a1, a2 = two(a)
        b1, b2 = two(b)
        c1, c2 = carry
        # B1：a XOR b → 予備の水 r1 を B2 の左の皿へ
        x = pour(1, sd) if abs(a1 - b1 + bb[0]) >= DEADBAND else 0.0
        # B2：(a XOR b) XOR c → 和
        s = abs(x - c1 + bb[1]) >= DEADBAND
        # BM：a+b+c とおもり 1.5u → 桁上り（次の段の2つの皿へ）
        cw = 1.5 * (1 + random.gauss(0, cw_sd)) if cw_sd else 1.5
        c = (a2 + b2 + c2 - cw + bb[2]) > 0
        carry = two(c)
        total |= int(s) << i
    return total | (int(c) << n)


def add_scale(A, B, n, sd=0.0, bias=0.0, gain_sd=0.0):
    """別案：目盛り天秤1つ／ビット。"""
    total, carry_amt = 0, 0.0
    for i in range(n):
        a, b = (A >> i) & 1, (B >> i) & 1
        left = (pour(1, sd) if a else 0.0) + (pour(1, sd) if b else 0.0) + carry_amt
        g = 1 + random.gauss(0, gain_sd) if gain_sd else 1.0
        r = g * (left - 1.5 + random.uniform(-bias, bias))  # 竿の振れ（u 換算の目盛り）
        s = (-1.0 <= r < 0.0) or (r >= 1.0)
        c = r > 0
        carry_amt = pour(1, sd) if c else 0.0
        total |= int(s) << i
    return total | (int(carry_amt > 0) << n)


def rate(fn, n, trials, **kw):
    ok = tot = 0
    for _ in range(trials):
        for A, B in itertools.product(range(2 ** n), repeat=2):
            ok += fn(A, B, n, **kw) == A + B
            tot += 1
    return ok / tot


N = 4
print(f"== {N}ビットの加算（{2 ** N}×{2 ** N} 通り）。数字は「足し算の答えが全桁合っていた割合」")
print(f"理想（誤差なし）：本命（指し樋2本）{rate(add_main, N, 1):.0%}　"
      f"本命（分水口）{rate(add_main, N, 1, fanout='split'):.0%}　別案 {rate(add_scale, N, 1):.0%}")

random.seed(7)
T = 40
print("\n-- 本命・配り方＝指し樋2本（採用）")
for sd in (0.03, 0.1, 0.2):
    for bias in (0.0, 0.2):
        for cw_sd in (0.0, 0.05):
            r = rate(add_main, N, T, sd=sd, bias=bias, cw_sd=cw_sd)
            print(f"  注ぐ量±{sd:<4} 皿の狂い±{bias:<3} おもりの狂い±{cw_sd:<4} → {r:.2%}")

print("\n-- 本命・配り方＝分水口（比較用）")
for sd in (0.03, 0.1, 0.2):
    for split_sd in (0.0, 0.05, 0.1):
        for bias in (0.0, 0.2):
            r = rate(add_main, N, T, sd=sd, split_sd=split_sd, bias=bias, fanout="split")
            print(f"  注ぐ量±{sd:<4} 分水の偏り±{split_sd:<4} 皿の狂い±{bias:<3} → {r:.2%}")

print("\n-- 別案（目盛り天秤1つ／ビット）")
for sd in (0.03, 0.1, 0.2):
    for gain_sd in (0.0, 0.1, 0.3):
        for bias in (0.0, 0.2):
            r = rate(add_scale, N, T, sd=sd, bias=bias, gain_sd=gain_sd)
            print(f"  注ぐ量±{sd:<4} 比例のずれ±{gain_sd:<4} 皿の狂い±{bias:<3} → {r:.2%}")

print("\n※ 別案は「竿の傾きが重さの差に比例し、途中の角度で止まる」ことが前提。本命は「釣り合いか、止め木まで傾くか」しか読まない。")
