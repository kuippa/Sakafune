// v2 草案（design/11）：足し算と引き算を、同じ固定した装置で回す。違いは連動した切り替え器（SW1・SW2、レバー1本）だけ。
// 外部パッケージなし。ブラウザ（<script src>）と Node（require）の両方で使う。作成：Claude Opus 5.5（2026-11-08）。
//
// 改訂の記録：
//   第2版（kuippa の指摘）：答えを「1つの桶に、答えの量だけ」出す。引き算は a・b を相殺し、残りを正／負の答えの桶へ。
//   第3版（kuippa）：人の操作と評価も装置に含める。
//     給水係：電源槽へ水を注ぐ（動力）。
//     元栓管理係：レバーを倒し、元栓を開け、計数添水（1u ごとに傾く鹿威し）の回数を数えて、
//                 a 回は a の＋槽へ、b 回は b の＋槽へ、そのあとは CLK へ樋を向ける（入力）。停止したら元栓を閉める。
//     CLK は計数添水 3回分（3u）で1拍。
//     カウント係：停止後、答えの桶の栓を開け、1u ごとに傾く添水の回数を数えて答えを読む（評価）。
//
// 装置（すべて固定。動くのは浮き・竿・振り分け器の樋・添水だけ）：
//   レジスタ a・b：＋槽・−槽と浮き比較器（値 ＝ ＋槽 − −槽、水は足すだけ）
//   答え：OUT の桶2つ（正の答え・負の答え）。計算が終わると、どちらか一方だけに、答えの大きさの水が入っている
//   駅0 相殺：SW1 が足し算なら素通り（→ 駅1）。引き算なら、a = 0 → 駅1、b = 0 → 駅2、どちらも ≠0 → a・b から 1 ずつ
//   駅1 b → 答え：b ≠ 0 なら b から 1、SW2 の向きの桶へ 1（足し算 → 正、引き算 → 負）。b = 0 → 駅2
//   駅2 a → 答え：a ≠ 0 なら a から 1、正の答えの桶へ 1。a = 0 → 駅3
//   駅3 停止
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.AddSub = factory();
})(this, function () {
  "use strict";

  function gauss() {
    let u = 0, w = 0;
    while (u === 0) u = Math.random();
    while (w === 0) w = Math.random();
    return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * w);
  }

  const STATIONS = [
    { name: "駅0 相殺", note: "足し算：素通り／引き算：a・b から 1 ずつ取る" },
    { name: "駅1 b → 答え", note: "足し算：正の桶へ／引き算：負の桶へ（SW2）" },
    { name: "駅2 a → 答え", note: "正の桶へ" },
    { name: "駅3 停止", note: "" },
  ];

  class AddSubMachine {
    // mode：切り替えレバー（"add" / "sub"）。sd：升・添水の精度（1u あたりの標準偏差）
    constructor(a, b, mode, { sd = 0 } = {}) {
      this.a0 = a; this.b0 = b; this.mode = mode; this.sd = sd;
      this.aP = 0; this.aM = 0; this.bP = 0; this.bM = 0;   // レジスタ（浮き比較器つき）。入力で満たす
      this.outP = 0; this.outM = 0;                          // 答えの桶（正・負）
      this.pcP = 0; this.pcM = 0;                            // 手番レジスタ
      this.inA = 0; this.inB = 0; this.loaded = false;       // 入力：元栓管理係が数えた計数添水の回数
      this.evalCount = 0; this.evalDone = false; this.evalSign = 1; this.drained = 0;   // 評価：カウント係が数えた回数
      this.ticks = 0; this.used = 0; this.pulse = 3; this.tips = 0;   // tips：計数添水が傾いた回数（入力＋拍）
    }
    q(u) { return this.sd ? u * (1 + gauss() * this.sd) : u; }
    pc() { return Math.round(this.pcP - this.pcM); }
    aNZ() { return this.aP - this.aM - 0.5 > 0; }            // 浮き比較器：水位の差が 0.5u 分を超えるか
    bNZ() { return this.bP - this.bM - 0.5 > 0; }
    halted() { return this.loaded && this.pc() >= 3; }      // 計算が止まった
    finished() { return this.halted() && this.evalDone; }    // 評価（数え終わり）まで済んだ
    a() { return Math.round(this.aP - this.aM); }
    b() { return Math.round(this.bP - this.bM); }
    value() { return Math.round(this.outP) - Math.round(this.outM); }   // 桶の中身（装置が出した答え）
    counted() { return this.evalSign * this.evalCount; }                 // カウント係が数えた答え

    // 次に何が起きるか（状態は変えない）
    plan() {
      if (!this.loaded) {
        if (this.inA < this.a0) return { k: -1, kind: "loadA", dep: [{ to: "aP", amt: 1 }] };
        if (this.inB < this.b0) return { k: -1, kind: "loadB", dep: [{ to: "bP", amt: 1 }] };
        return { k: -1, kind: "loadEnd", dep: [] };          // 元栓管理係が樋を CLK へ向ける
      }
      const k = this.pc();
      if (k >= 3) return this.evalDone ? { k, kind: "done", dep: [] } : { k, kind: "eval", dep: [] };
      const pcTo = n => ({ to: "pcP", amt: n });
      if (k === 0) {
        if (this.mode === "add") return { k, kind: "bypass", dep: [pcTo(1)], next: 1 };
        if (!this.aNZ()) return { k, kind: "a0", dep: [pcTo(1)], next: 1 };
        if (!this.bNZ()) return { k, kind: "b0", dep: [pcTo(2)], next: 2 };
        return { k, kind: "both", dep: [{ to: "aM", amt: 1 }, { to: "bM", amt: 1 }], next: 0 };
      }
      if (k === 1) {
        if (!this.bNZ()) return { k, kind: "z", dep: [pcTo(1)], next: 2 };
        return { k, kind: "nz", dep: [{ to: "bM", amt: 1 }, { to: this.mode === "add" ? "outP" : "outM", amt: 1 }], next: 1 };
      }
      if (!this.aNZ()) return { k, kind: "z", dep: [pcTo(1)], next: 3 };
      return { k, kind: "nz", dep: [{ to: "aM", amt: 1 }, { to: "outP", amt: 1 }], next: 2 };
    }

    tick() {
      const p = this.plan();
      switch (p.kind) {
        case "done": return false;
        case "loadA": this.aP += this.q(1); this.inA++; this.used += 1; this.tips++; return true;
        case "loadB": this.bP += this.q(1); this.inB++; this.used += 1; this.tips++; return true;
        case "loadEnd": this.loaded = true; return true;
        case "eval": {
          // カウント係：水の入っている答えの桶の栓を開け、1u ごとに傾く添水を数える。最後に半分以上残れば 1 と数える
          if (this.evalCount === 0 && this.drained === 0) this.evalSign = this.outM > this.outP ? -1 : 1;
          const total = this.evalSign > 0 ? this.outP : this.outM, left = total - this.drained;
          if (left >= 0.5) { this.evalCount++; this.drained += Math.min(1, left); }
          if (total - this.drained < 0.5) this.evalDone = true;
          return true;
        }
      }
      this.used += this.pulse; this.tips += this.pulse;
      for (const d of p.dep) this[d.to] += this.q(d.amt);
      this.ticks++;
      return true;
    }
    run(max = 2000) { let n = 0; while (!this.finished() && n++ < max) this.tick(); return this.finished(); }
    expected() { return this.mode === "add" ? this.a0 + this.b0 : this.a0 - this.b0; }
    // 正しい ＝ 答えが片方の桶だけに入り、カウント係の数えた答えが正しい
    correct() {
      const one = Math.round(this.outP) === 0 || Math.round(this.outM) === 0;
      return this.finished() && one && this.counted() === this.expected();
    }
  }
  return { AddSubMachine, STATIONS };
});
