// 四則演算が「盤」の機械で正しく回るかのテスト（Node だけで動く）。
// 使い方: node tools/viewer/test_arith.js
const { PROGRAMS, Machine } = require("./sakafune_machine.js");

let fail = 0;
console.log("== 誤差なし：a, b = 0〜9 の全組み合わせ（割り算は b = 1〜9）");
for (const key of Object.keys(PROGRAMS)) {
  let ok = 0, tot = 0, maxTicks = 0, maxWater = 0;
  for (let a = 0; a <= 9; a++) for (let b = key === "div" ? 1 : 0; b <= 9; b++) {
    const m = new Machine(key, a, b);
    m.run();
    tot++;
    if (m.correct()) ok++; else { fail++; if (fail < 10) console.log(`  NG ${key} a=${a} b=${b} → ${m.result().text}`); }
    maxTicks = Math.max(maxTicks, m.ticks);
    maxWater = Math.max(maxWater, m.poured);
  }
  console.log(`  ${PROGRAMS[key].label}：${ok}/${tot} 正しい（最大 ${maxTicks} 手順、水 最大 ${Math.round(maxWater)}u）`);
}

console.log("\n== 割り算 b = 0：止まらないこと（5000 手順で打ち切り）");
{ const m = new Machine("div", 5, 0); console.log(`  5 ÷ 0 → ${m.run() ? "止まった（おかしい）" : "止まらない（期待どおり）"}`); }

console.log("\n== 升の精度（各 200 回、a = 7, b = 3）。数字は答えが合っていた割合");
for (const key of Object.keys(PROGRAMS)) {
  const row = [];
  for (const sd of [0.01, 0.03, 0.05, 0.1]) {
    let ok = 0;
    for (let i = 0; i < 200; i++) { const m = new Machine(key, 7, 3, { sd }); m.run(); ok += m.correct(); }
    row.push(`±${sd}u → ${Math.round(ok / 2)}%`);
  }
  console.log(`  ${PROGRAMS[key].label}：${row.join("　")}`);
}
process.exit(fail ? 1 : 0);
