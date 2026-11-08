// フォールモデル（design/10）：最初に水を置いたら、あとは位置エネルギーだけで、水が上から下へ流れて計算する機械。
// 酒船石とは切り離した、別のモデル。ブラウザ（<script src>）と Node（require）の両方で使う。外部パッケージなし。
// 作成：Claude Opus 5.5（2026-11-08）。
//
// 部品は design/parts_catalog.md の機能部品で書く。高さの順（上から下へしか流れない）：
//   SRC 電源槽 → CLK 拍発生器（P u ずつまとめて落とす）→ DCD デコーダ（PCR 手番レジスタの軸口で出口 k を選ぶ RTE）
//   → 駅 k の SPL 量り分け器 →［JZ のときだけ］RTE 振り分け器（レジスタの軸口で 0 / ≠0）
//   → DLY 遅延升 → いちばん下の ACC 蓄積升（レジスタ REG と手番レジスタ PCR の＋升・−升）
// 状態はすべて「蓄積升に足すだけの水」：値 ＝ ＋升 − −升。上へ運ぶものは何もない。
// コードの中の N・S は、それぞれ＋升・−升を表す。
// 命令：INC r → next ／ JZ r（0 なら z、そうでなければ r を 1 減らして nz）／ HALT。Minsky のカウンタ機械と同じ。
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.Fall = factory();
})(this, function () {
  "use strict";

  const PROGRAMS = {
    add: {
      label: "足し算", symbol: "+", regs: ["a", "b", "答え"], init: (a, b) => [a, b, 0],
      prog: [
        { op: "JZ", r: 0, z: 2, nz: 1, note: "a が 0 でなければ 1 減らす" },
        { op: "INC", r: 2, next: 0, note: "答えに 1 足す" },
        { op: "JZ", r: 1, z: 4, nz: 3, note: "b が 0 でなければ 1 減らす" },
        { op: "INC", r: 2, next: 2, note: "答えに 1 足す" },
        { op: "HALT" },
      ],
      result: v => ({ text: `${v[2]}`, ok: (a, b) => v[2] === a + b }),
    },
    sub: {
      label: "引き算", symbol: "−", regs: ["a", "b", "負の分"], init: (a, b) => [a, b, 0],
      prog: [
        { op: "JZ", r: 1, z: 3, nz: 1, note: "b が 0 になるまで 1 ずつ" },
        { op: "JZ", r: 0, z: 2, nz: 0, note: "a から 1 引く" },
        { op: "INC", r: 2, next: 0, note: "a が足りなければ、負の分に数える" },
        { op: "HALT" },
      ],
      result: v => { const x = v[2] > 0 ? -v[2] : v[0]; return { text: `${x}`, ok: (a, b) => x === a - b }; },
    },
    mul: {
      label: "掛け算", symbol: "×", regs: ["a", "b", "答え", "作業"], init: (a, b) => [a, b, 0, 0],
      prog: [
        { op: "JZ", r: 0, z: 6, nz: 1, note: "a 回くり返す" },
        { op: "JZ", r: 1, z: 4, nz: 2, note: "b を 1 つ取り出す" },
        { op: "INC", r: 2, next: 3, note: "答えに 1" },
        { op: "INC", r: 3, next: 1, note: "作業に 1（b の写し）" },
        { op: "JZ", r: 3, z: 0, nz: 5, note: "作業を b へ戻す" },
        { op: "INC", r: 1, next: 4, note: "b に 1" },
        { op: "HALT" },
      ],
      result: v => ({ text: `${v[2]}`, ok: (a, b) => v[2] === a * b }),
    },
    div: {
      label: "割り算", symbol: "÷", regs: ["a", "b", "商", "作業", "余り"], init: (a, b) => [a, b, 0, 0, 0],
      prog: [
        { op: "JZ", r: 1, z: 2, nz: 1, note: "b を作業へ移す" },
        { op: "INC", r: 3, next: 0, note: "作業に 1" },
        { op: "JZ", r: 3, z: 6, nz: 3, note: "b の数だけくり返す" },
        { op: "INC", r: 1, next: 4, note: "b に 1 戻す" },
        { op: "JZ", r: 0, z: 8, nz: 5, note: "a から 1 引く。尽きたら終わり" },
        { op: "INC", r: 4, next: 2, note: "引いた分を余りへ" },
        { op: "INC", r: 2, next: 7, note: "b だけ引けたので商に 1" },
        { op: "JZ", r: 4, z: 0, nz: 7, note: "余りの皿を 0 に戻す" },
        { op: "HALT" },
      ],
      result: v => ({ text: `${v[2]} 余り ${v[4]}`, ok: (a, b) => b > 0 && v[2] === Math.floor(a / b) && v[4] === a % b }),
    },
  };

  function gauss() {
    let u = 0, w = 0;
    while (u === 0) u = Math.random();
    while (w === 0) w = Math.random();
    return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * w);
  }

  // 駅ごとに要る電源の水（u）。添水が一度に落とす量は、これより少し多くしておく（余りは溢れて捨て溝へ）
  function need(ins, k) {
    if (ins.op === "HALT") return 0;
    if (ins.op === "INC") return 1 + Math.abs(ins.next - k);
    return Math.max(1 + Math.abs(ins.nz - k), Math.abs(ins.z - k));
  }

  class FallMachine {
    // sd：升の精度（1u あたりの標準偏差）。bias：天秤ごとの皿の狂い（±bias の一様乱数）
    // pcCap：手番レジスタ（PCR）の−升の容量（u）。あふれた水は、同じ竿の＋側に吊った「あふれ受け」へ落ちる。
    //   −升が満ちると「戻る」水がすべて＋側に掛かるので、手番は進むだけになり、やがてデコーダの端の
    //   「異常停止」の出口（駅の数 n 以上）に達して止まる。あふれが一度でも起きたら答えは無効（あふれ印）。
    constructor(key, a, b, { sd = 0, bias = 0, pcCap = 400 } = {}) {
      const P = PROGRAMS[key];
      this.key = key; this.P = P; this.a = a; this.b = b; this.sd = sd;
      const init = P.init(a, b);
      this.N = init.slice(); this.S = init.map(() => 0);
      // OUT 出力桶：JZ で読まれないレジスタは、比較器も−升も要らない。ただの桶（値 ＝ 中の水の量）
      this.out = init.map((_, r) => !P.prog.some(ins => ins.op === "JZ" && ins.r === r));
      this.bias = init.map(() => (Math.random() * 2 - 1) * bias);
      this.pcN = 0; this.pcS = 0; this.pcBias = (Math.random() * 2 - 1) * bias;
      this.pulse = Math.max(...P.prog.map(need)) + 1;
      this.pcCap = pcCap; this.overflow = 0; this.fault = false;
      this.ticks = 0; this.used = 0; this.waste = 0; this.lost = false; this.last = null;
    }
    q(u) { return this.sd ? u * (1 + gauss() * this.sd) : u; }
    value(r) { return Math.round(this.N[r] - this.S[r]); }
    values() { return this.N.map((_, r) => this.value(r)); }
    pcRaw() { return this.pcN - this.pcS + this.pcBias; }
    pc() { return Math.round(this.pcRaw()); }               // 目盛り：受け口の幅は ±0.5
    nonzero(r) { return this.N[r] - this.S[r] + this.bias[r] - 0.5 > 0; }   // 南の皿におもり 0.5u
    halted() { const k = this.pc(); return this.lost || this.fault || (this.P.prog[k] && this.P.prog[k].op === "HALT"); }

    // 次の1拍で何が起きるか（状態は変えない）
    plan() {
      const k = this.pc(), ins = this.P.prog[k];
      if (k >= this.P.prog.length) return { k, op: "FAULT" };   // デコーダの端：異常停止の出口
      if (!ins) return { k, op: "LOST" };
      if (ins.op === "HALT") return { k, op: "HALT" };
      const dep = [];
      const movePC = next => { const d = next - k; if (d) dep.push({ to: "pc", pan: d > 0 ? "N" : "S", amt: Math.abs(d) }); };
      if (ins.op === "INC") {
        dep.push({ to: "reg", r: ins.r, pan: "N", amt: 1 });
        movePC(ins.next);
        return { k, op: "INC", r: ins.r, next: ins.next, dep };
      }
      const nz = this.nonzero(ins.r);
      if (nz) dep.push({ to: "reg", r: ins.r, pan: "S", amt: 1 });
      movePC(nz ? ins.nz : ins.z);
      return { k, op: "JZ", r: ins.r, branch: nz ? "nz" : "z", next: nz ? ins.nz : ins.z, dep };
    }

    tick() {
      if (this.halted()) return false;
      const p = this.plan();
      this.last = p;
      this.used += this.pulse;
      let put = 0;
      for (const d of p.dep) {
        const v = this.q(d.amt); put += d.amt;
        if (d.to === "reg") { if (d.pan === "N") this.N[d.r] += v; else this.S[d.r] += v; }
        else if (d.pan === "N") this.pcN += v;
        else {                                         // PCR の−升。容量を超えた分は＋側のあふれ受けへ
          const over = Math.max(0, this.pcS + v - this.pcCap);
          this.pcS += v - over; this.pcN += over; this.overflow += over;
        }
      }
      this.waste += this.pulse - put;
      this.ticks++;
      const k = this.pc();
      if (k >= this.P.prog.length) this.fault = true;        // 異常停止の出口へ
      else if (k < 0) this.lost = true;                      // 目盛りの外（誤差で手番を見失った）
      return true;
    }
    run(max = 5000) { while (!this.halted() && this.ticks < max) this.tick(); return this.halted() && !this.lost; }
    result() { return this.P.result(this.values()); }
    correct() { return !this.lost && !this.fault && !this.overflow && this.halted() && this.result().ok(this.a, this.b); }
    // 止まり方：normal（停止の駅）／overflow（停止の駅に着いたが、あふれ印あり＝答えは無効）／fault（異常停止）／lost／running
    status() {
      if (this.lost) return "lost";
      if (this.fault) return "fault";
      if (this.halted()) return this.overflow ? "overflow" : "normal";
      return "running";
    }
    // 皿に溜まった水の最大（皿の大きさの目安）
    maxPan() { return Math.max(...this.N, ...this.S, this.pcN, this.pcS); }
  }

  return { PROGRAMS, FallMachine, need };
});
