// フォールモデル（design/10）で四則演算が正しく回るかのテスト（Node だけで動く）。
// 使い方: node tools/viewer/test_fall.js
const { PROGRAMS, FallMachine } = require("./fall_machine.js");

let fail = 0;
console.log("== 誤差なし：a, b = 0〜9 の全組み合わせ（割り算は b = 1〜9）");
for (const key of Object.keys(PROGRAMS)) {
  let ok = 0, tot = 0, maxTicks = 0, maxWater = 0, maxPan = 0, pulse = 0;
  for (let a = 0; a <= 9; a++) for (let b = key === "div" ? 1 : 0; b <= 9; b++) {
    const m = new FallMachine(key, a, b);
    m.run();
    tot++;
    if (m.correct()) ok++; else { fail++; if (fail < 10) console.log(`  NG ${key} a=${a} b=${b} → ${m.result().text}`); }
    maxTicks = Math.max(maxTicks, m.ticks); maxWater = Math.max(maxWater, m.used); maxPan = Math.max(maxPan, m.maxPan()); pulse = m.pulse;
  }
  console.log(`  ${PROGRAMS[key].label}：${ok}/${tot} 正しい（駅 ${PROGRAMS[key].prog.length}、1拍 ${pulse}u、最大 ${maxTicks} 拍、電源槽から最大 ${maxWater}u、蓄積升の最大 ${Math.round(maxPan)}u）`);
}

console.log("\n== 手番レジスタの−升（容量 400u）は、ふつうの計算ではあふれない");
{
  let maxS = 0, over = 0;
  for (const key of Object.keys(PROGRAMS)) for (let a = 0; a <= 9; a++) for (let b = key === "div" ? 1 : 0; b <= 9; b++) {
    const m = new FallMachine(key, a, b); m.run(); maxS = Math.max(maxS, m.pcS); over += m.overflow > 0;
  }
  console.log(`  −升の最大 ${Math.round(maxS)}u、あふれた計算 ${over} 件`);
  if (over) fail++;
}

console.log("\n== 割り算 b = 0：PCR の−升があふれて止まる（あふれ止め）");
for (const cap of [Infinity, 400, 100]) {
  for (const a of [1, 5]) {
    const m = new FallMachine("div", a, 0, { pcCap: cap });
    m.run(20000);
    const st = m.status();
    console.log(`  ${a} ÷ 0、−升の容量 ${cap === Infinity ? "無限" : cap + "u"} → ${st === "running" ? "止まらない" : st === "fault" ? "異常停止" : st === "overflow" ? "停止の駅に着いた（あふれ印あり＝無効）" : st}（${m.ticks} 拍、あふれ ${Math.round(m.overflow)}u）`);
    if (cap !== Infinity && st !== "fault" && st !== "overflow") fail++;
    if (cap === Infinity && st !== "running") fail++;
  }
}

console.log("\n== 定量升・量り分け器の精度（各 200 回、a = 7, b = 3）。数字は答えが合っていた割合");
for (const key of Object.keys(PROGRAMS)) {
  const row = [];
  for (const sd of [0.005, 0.01, 0.03, 0.05]) {
    let ok = 0;
    for (let i = 0; i < 200; i++) { const m = new FallMachine(key, 7, 3, { sd }); m.run(); ok += m.correct(); }
    row.push(`±${sd}u → ${Math.round(ok / 2)}%`);
  }
  console.log(`  ${PROGRAMS[key].label}：${row.join("　")}`);
}
process.exit(fail ? 1 : 0);
