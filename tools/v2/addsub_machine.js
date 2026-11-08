// v2 草案（design/11）：足し算と引き算を、同じ固定した装置で回す。違いは切り替え器（SW）1つだけ。
// 外部パッケージなし。ブラウザ（<script src>）と Node（require）の両方で使う。作成：Claude Opus 5.5（2026-11-08）。
//
// 装置（すべて固定。動くのは浮き・竿・振り分け器の樋だけ）：
//   SRC → CLK（1拍 P u）→ DCD（PCR の値で駅を選ぶ）→ 駅0：STEP b → a、駅1：停止
//   駅0（STEP b → a）：b の浮き比較器が「≠0」なら、1u を b の−槽へ（b が 1 減る）、1u を切り替え器 SW へ。
//                       SW は、足し算なら a の＋槽へ、引き算なら a の−槽へ（スタート前に手で決める）。
//                       手番はそのまま（駅0 をくり返す）。「0」なら 1u を PCR の＋槽へ（駅1：停止へ）。
//   レジスタの値 ＝ ＋槽 − −槽（水は足すだけ）。a は「0 か」を読まれないので出力（OUT±：2つの桶）でよい。
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

  class AddSubMachine {
    // mode：切り替え器の向き（"add" ＝ a の＋槽へ、"sub" ＝ a の−槽へ）。sd：定量升の精度
    constructor(a, b, mode, { sd = 0 } = {}) {
      this.a0 = a; this.b0 = b; this.mode = mode; this.sd = sd;
      this.aP = a; this.aM = 0;        // a：OUT±（2つの桶）
      this.bP = b; this.bM = 0;        // b：REG（浮き比較器で「0 か」を読む）
      this.pcP = 0; this.pcM = 0;      // PCR
      this.ticks = 0; this.used = 0; this.pulse = 3;
    }
    q(u) { return this.sd ? u * (1 + gauss() * this.sd) : u; }
    pc() { return Math.round(this.pcP - this.pcM); }
    bNonzero() { return this.bP - this.bM - 0.5 > 0; }   // 浮き比較器：水位の差が 0.5u 分を超えるか
    halted() { return this.pc() === 1; }
    value() { return Math.round(this.aP - this.aM); }
    plan() {
      if (this.halted()) return { op: "HALT" };
      if (this.bNonzero()) return { op: "STEP", branch: "nz", to: this.mode === "add" ? "a+" : "a-" };
      return { op: "STEP", branch: "z" };
    }
    tick() {
      const p = this.plan();
      if (p.op === "HALT") return false;
      this.used += this.pulse;
      if (p.branch === "nz") {
        this.bM += this.q(1);
        if (p.to === "a+") this.aP += this.q(1); else this.aM += this.q(1);
      } else this.pcP += this.q(1);
      this.ticks++;
      return true;
    }
    run(max = 1000) { while (!this.halted() && this.ticks < max) this.tick(); return this.halted(); }
    correct() { return this.halted() && this.value() === (this.mode === "add" ? this.a0 + this.b0 : this.a0 - this.b0); }
  }
  return { AddSubMachine };
});
