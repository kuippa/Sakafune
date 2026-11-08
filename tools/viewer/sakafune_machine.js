// 酒船石の「天秤を釣り合わせる盤」（design/09）を命令にした、水のカウンタ機械。
// ブラウザ（<script src>）と Node（require）の両方で使う。外部パッケージなし。
// 作成：Claude Opus 5.5（2026-11-07）。テスト段階のもの。
//
// レジスタ r ＝ 天秤1本。値 ＝ 北の皿の水 − 南の皿の水（水は足すだけ）。釣り合いの幅 ±0.5u。
// 命令：
//   STEP r → s（符号つき）, nz, z ：盤1枚（酒船石1枚分）。A1 に 3u を注ぐと、r の指し樋が
//       北が重い（r>0）→ 南の列：B → r の南の皿（r が 1 減る）、C → s へ 1 移す、D → 次の手番を nz へ
//       南が重い（r<0）→ 北の列：B → r の北の皿（r が 1 増える）、C → s から 1 引く、D → 次の手番を nz へ
//       釣り合い（r=0）→ 中央の列：E1 → 次の手番を z へ、E2 → F → 下流、G → 捨て溝
//   INC r, next ：駅。r の北の皿に 1u、次の手番を next へ
//   HALT ：止まる
// 1回の手順：手番の水がある駅（盤）だけが電源の水を通す → 全部の駅の皿を空ける → 控えを駅の皿へ。
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.Sakafune = factory();
})(this, function () {
  "use strict";

  const PROGRAMS = {
    add: {
      label: "足し算", symbol: "+",
      regs: ["a", "b", "答え"],
      init: (a, b) => [a, b, 0],
      prog: [
        { op: "STEP", r: 0, to: [2, +1], nz: 0, z: 1, note: "a を答えへ移す" },
        { op: "STEP", r: 1, to: [2, +1], nz: 1, z: 2, note: "b を答えへ移す" },
        { op: "HALT" },
      ],
      result: v => ({ text: `${v[2]}`, ok: (a, b) => v[2] === a + b }),
    },
    sub: {
      label: "引き算", symbol: "−",
      regs: ["a（答え）", "b"],
      init: (a, b) => [a, b, 0].slice(0, 2),
      prog: [
        { op: "STEP", r: 1, to: [0, -1], nz: 0, z: 1, note: "b を 1 ずつ a から引く" },
        { op: "HALT" },
      ],
      result: v => ({ text: `${v[0]}`, ok: (a, b) => v[0] === a - b }),
    },
    mul: {
      label: "掛け算", symbol: "×",
      regs: ["a", "b", "答え", "作業"],
      init: (a, b) => [a, b, 0, 0],
      prog: [
        { op: "STEP", r: 0, to: null, nz: 1, z: 4, note: "a を 1 減らす（a 回くり返す）" },
        { op: "STEP", r: 1, to: [2, +1], nz: 2, z: 3, note: "b を答えへ移す" },
        { op: "INC", r: 3, next: 1, note: "同じ数だけ作業へも足す（b の写し）" },
        { op: "STEP", r: 3, to: [1, +1], nz: 3, z: 0, note: "作業を b へ戻す" },
        { op: "HALT" },
      ],
      result: v => ({ text: `${v[2]}`, ok: (a, b) => v[2] === a * b }),
    },
    div: {
      label: "割り算", symbol: "÷",
      regs: ["a", "b", "商", "作業", "余り"],
      init: (a, b) => [a, b, 0, 0, 0],
      prog: [
        { op: "STEP", r: 1, to: [3, +1], nz: 0, z: 1, note: "b を作業へ移す" },
        { op: "STEP", r: 3, to: [1, +1], nz: 2, z: 3, note: "作業から 1 つ b へ戻す（b 回くり返す）" },
        { op: "STEP", r: 0, to: [4, +1], nz: 1, z: 5, note: "a から 1 引いて余りへ。a が尽きたら終わり" },
        { op: "INC", r: 2, next: 4, note: "b だけ引けたので商を 1 増やす" },
        { op: "STEP", r: 4, to: null, nz: 4, z: 0, note: "引いた分（余りの皿）を空にする" },
        { op: "HALT" },
      ],
      result: v => ({ text: `${v[2]} 余り ${v[4]}`, ok: (a, b) => b > 0 && v[2] === Math.floor(a / b) && v[4] === a % b }),
    },
  };

  function gauss() { // 標準正規乱数
    let u = 0, w = 0;
    while (u === 0) u = Math.random();
    while (w === 0) w = Math.random();
    return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * w);
  }

  class Machine {
    // sd：升の精度（1u あたりの標準偏差）。bias：天秤ごとの皿の狂い（±bias の一様乱数）
    constructor(progKey, a, b, { sd = 0, bias = 0 } = {}) {
      const P = PROGRAMS[progKey];
      this.key = progKey; this.P = P; this.a = a; this.b = b; this.sd = sd;
      const init = P.init(a, b);
      this.N = init.slice();                 // 北の皿
      this.S = init.map(() => 0);            // 南の皿
      this.bias = init.map(() => (Math.random() * 2 - 1) * bias);
      this.token = P.prog.map(() => 0);      // 駅（盤）の皿の手番の水
      this.token[0] = 1;
      this.stage = P.prog.map(() => 0);      // 控え
      this.ticks = 0; this.poured = 0; this.downstream = 0; this.waste = 0;
      this.last = null;                      // 直前の手順で起きたこと（表示用）
    }
    q() { const v = this.sd ? 1 + gauss() * this.sd : 1; this.poured += v; return v; }
    value(r) { return Math.round(this.N[r] - this.S[r]); }
    values() { return this.N.map((_, r) => this.value(r)); }
    tilt(r) {
      const d = this.N[r] - this.S[r] + this.bias[r];
      return Math.abs(d) < 0.5 ? "level" : (d > 0 ? "north" : "south");
    }
    halted() { return this.P.prog.some((ins, k) => ins.op === "HALT" && this.token[k] >= 0.5); }
    current() { return this.token.findIndex(t => t >= 0.5); }

    // 次の1手順で何が起きるか（状態は変えない）。画面の説明に使う
    plan() {
      const k = this.current();
      if (k < 0) return null;
      const ins = this.P.prog[k];
      if (ins.op === "HALT") return { k, op: "HALT" };
      if (ins.op === "INC") return { k, op: "INC", r: ins.r, next: ins.next };
      const t = this.tilt(ins.r);
      if (t === "level") return { k, op: "STEP", r: ins.r, tilt: t, row: "center", next: ins.z };
      const row = t === "north" ? "south" : "north";          // 指し樋は軽い側の列へ
      let dest = null;
      if (ins.to) {                                           // C：s の北の皿（＋）か南の皿（−）へ
        const [s, sign] = ins.to;
        dest = { s, pan: (row === "south") === (sign > 0) ? "N" : "S" };
      }
      return { k, op: "STEP", r: ins.r, tilt: t, row, next: ins.nz, feed: row === "south" ? "S" : "N", dest };
    }

    tick() {
      if (this.halted()) return false;
      const p = this.plan();                       // 手番の水がある駅は1つだけ（門：ほかの駅の電源の水は捨て溝へ）
      this.last = p;
      if (p.op === "INC") {
        this.N[p.r] += this.q();
        this.stage[p.next] += this.q();
      } else if (p.row === "center") {             // 中央の列
        this.stage[p.next] += this.q();            // E1 → 次の手番
        this.downstream += this.q();               // E2 → F → 下流
        this.waste += this.q();                    // G
      } else {                                     // STEP：電源の 3u が、すり切りの升 B・C・D に 1u ずつ入る
        const [q1, q2, q3] = [this.q(), this.q(), this.q()];
        if (p.feed === "S") this.S[p.r] += q1; else this.N[p.r] += q1;   // B：軽い側の皿へ
        if (p.dest) { if (p.dest.pan === "N") this.N[p.dest.s] += q2; else this.S[p.dest.s] += q2; }
        else this.waste += q2;
        this.stage[p.next] += q3;                  // D：次の手番
      }
      // 駅の皿を空けて、控えを移す（停止の駅は空けない）
      this.P.prog.forEach((ins, k) => {
        if (ins.op !== "HALT") { if (this.token[k] >= 0.5) this.waste += this.token[k]; this.token[k] = 0; }
        this.token[k] += this.stage[k];
        this.stage[k] = 0;
      });
      this.ticks++;
      return true;
    }

    run(maxTicks = 5000) {
      while (!this.halted() && this.ticks < maxTicks) this.tick();
      return this.halted();
    }
    result() { return this.P.result(this.values()); }
    correct() { return this.halted() && this.result().ok(this.a, this.b); }
  }

  return { PROGRAMS, Machine };
});
