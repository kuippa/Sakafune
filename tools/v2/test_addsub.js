// v2 草案（design/11）のテスト：足し算・引き算が、同じ装置と連動した切り替え器で回るか。
// 答えが「1つの桶に、答えの量だけ」入っていることも確かめる（読む人が引き算をしなくてよいこと）。
// 使い方: node tools/v2/test_addsub.js
const { AddSubMachine } = require("./addsub_machine.js");

let fail = 0;
console.log("== 誤差なし：a, b = 0〜9 の全組み合わせ");
for (const mode of ["add", "sub"]) {
  let ok = 0, tot = 0, maxTicks = 0, maxWater = 0;
  for (let a = 0; a <= 9; a++) for (let b = 0; b <= 9; b++) {
    const m = new AddSubMachine(a, b, mode); m.run(); tot++;
    if (m.correct()) ok++; else { fail++; console.log(`  NG ${mode} ${a},${b} → 正 ${m.outP} 負 ${m.outM}`); }
    maxTicks = Math.max(maxTicks, m.ticks); maxWater = Math.max(maxWater, m.used);
  }
  console.log(`  ${mode === "add" ? "足し算" : "引き算"}：${ok}/${tot} 正しい（最大 ${maxTicks} 拍、電源の水 最大 ${maxWater}u）`);
}
for (const [a, b, md] of [[3, 4, "sub"], [7, 3, "sub"], [3, 4, "add"]]) {
  const m = new AddSubMachine(a, b, md); m.run();
  console.log(`  例：${a} ${md === "add" ? "+" : "−"} ${b} → 正の答えの桶 ${m.outP}u、負の答えの桶 ${m.outM}u（a・b は ${m.a()}・${m.b()} に戻る）`);
}

console.log("\n== 定量升の精度（各 300 回、a = 7, b = 9）");
for (const mode of ["add", "sub"]) {
  const row = [];
  for (const sd of [0.01, 0.03, 0.05, 0.1]) {
    let ok = 0;
    for (let i = 0; i < 300; i++) { const m = new AddSubMachine(7, 9, mode, { sd }); m.run(); ok += m.correct(); }
    row.push(`±${sd}u → ${Math.round(ok / 3)}%`);
  }
  console.log(`  ${mode === "add" ? "足し算" : "引き算"}：${row.join("　")}`);
}
process.exit(fail ? 1 : 0);
