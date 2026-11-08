// v2 草案（design/11）：足し算と引き算を、同じ固定した装置で回す。違いは連動した切り替え器（SW1・SW2、レバー1本）だけ。
// 外部パッケージなし。ブラウザ（<script src>）と Node（require）の両方で使う。作成：Claude Opus 5.5（2026-11-08）。
//
// 2026-11-08 改訂（kuippa の指摘）：前の版の引き算は、b の水を a の−槽へ移すだけで、3 − 4 は「＋槽 3u・−槽 4u」が
//   残るだけだった（答えの −1 は、読む人が差を取って初めて分かる＝装置は計算していない）。
//   そこで、答えを「1つの桶に、答えの量だけ」出すようにした：引き算は a と b を 1 ずつ相殺し、残ったほうを答えの桶へ移す。
//
// 装置（すべて固定。動くのは浮き・竿・振り分け器の樋だけ）：
//   レジスタ a・b：＋槽・−槽と浮き比較器（値 ＝ ＋槽 − −槽、水は足すだけ）
//   答え：OUT の桶2つ（正の答え・負の答え）。計算が終わると、どちらか一方だけに、答えの大きさの水が入っている
//   駅0 相殺：SW1 が足し算なら素通り（→ 駅1）。引き算なら、a = 0 → 駅1、b = 0 → 駅2、どちらも ≠0 → a・b から 1 ずつ（駅0 をくり返す）
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
    // mode：切り替えレバー（"add" / "sub"）。SW1（駅0 の入口）と SW2（駅1 の出口）が連動する。sd：定量升の精度
    // 入力は INP 入力器で入れる：1u のすり切り升 RACK 個の列に、電源槽から順に水を満たし、仕切り（目盛り n）から
    // 先は捨て槽へ。スタートで升の列の栓を一度に開け、レジスタの＋槽へ n u を流す（升1つずつに精度 sd の誤差）。
    constructor(a, b, mode, { sd = 0 } = {}) {
      this.a0 = a; this.b0 = b; this.mode = mode; this.sd = sd;
      this.aP = 0; this.aM = 0; this.bP = 0; this.bM = 0;   // レジスタ（浮き比較器つき）。入力器で満たす
      this.outP = 0; this.outM = 0;                          // 答えの桶（正・負）
      this.pcP = 0; this.pcM = 0;                            // 手番レジスタ
      this.loaded = false;                                   // 入力器の栓を開けたか
      this.ticks = 0; this.used = 0; this.pulse = 3;
    }
    // 入力器：仕切りまでの n 個の升（各 1u）を、一度に＋槽へ流す
    loadInputs() {
      if (this.loaded) return;
      for (let i = 0; i < this.a0; i++) this.aP += this.q(1);
      for (let i = 0; i < this.b0; i++) this.bP += this.q(1);
      this.used += this.a0 + this.b0;
      this.loaded = true;
    }
    q(u) { return this.sd ? u * (1 + gauss() * this.sd) : u; }
    pc() { return Math.round(this.pcP - this.pcM); }
    aNZ() { return this.aP - this.aM - 0.5 > 0; }            // 浮き比較器：水位の差が 0.5u 分を超えるか
    bNZ() { return this.bP - this.bM - 0.5 > 0; }
    halted() { return this.pc() >= 3; }
    a() { return Math.round(this.aP - this.aM); }
    b() { return Math.round(this.bP - this.bM); }
    value() { return Math.round(this.outP) - Math.round(this.outM); }

    // 次の1拍で何が起きるか（状態は変えない）。kind は振り分けの結果、dep は槽へ入れる水
    plan() {
      if (!this.loaded) return { k: -1, kind: "load", dep: [{ to: "aP", amt: this.a0 }, { to: "bP", amt: this.b0 }] };
      const k = this.pc();
      if (k >= 3) return { k, kind: "halt", dep: [] };
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
      if (p.kind === "halt") return false;
      if (p.kind === "load") { this.loadInputs(); return true; }   // 入力は拍に数えない
      this.used += this.pulse;
      for (const d of p.dep) this[d.to] += this.q(d.amt);
      this.ticks++;
      return true;
    }
    run(max = 1000) { while (!this.halted() && this.ticks < max) this.tick(); return this.halted(); }
    expected() { return this.mode === "add" ? this.a0 + this.b0 : this.a0 - this.b0; }
    // 正しい ＝ 答えが合い、かつ答えの水が片方の桶だけに入っている（読む人が引き算をしなくてよい）
    correct() {
      const one = Math.round(this.outP) === 0 || Math.round(this.outM) === 0;
      return this.halted() && one && this.value() === this.expected();
    }
  }
  return { AddSubMachine, STATIONS };
});
