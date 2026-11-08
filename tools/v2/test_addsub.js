// v2 草案（design/11）のテスト：足し算・引き算が、同じ装置と連動した切り替え器で回るか。
// 入力（元栓管理係が計数添水を数えて a・b の槽へ送る）から、評価（カウント係が答えの桶を 1u ずつ数える）まで通す。
// 答えが「1つの桶に、答えの量だけ」入っていること、カウント係の数えた答えが正しいことを確かめる。
// 使い方: node tools/v2/test_addsub.js
const { AddSubMachine } = require("./addsub_machine.js");

let fail = 0;
console.log("== 誤差なし：a, b = 0〜9 の全組み合わせ（入力 → 計算 → 評価）");
for (const mode of ["add", "sub"]) {
  let ok = 0, tot = 0, maxTicks = 0, maxWater = 0, maxTips = 0;
  for (let a = 0; a <= 9; a++) for (let b = 0; b <= 9; b++) {
    const m = new AddSubMachine(a, b, mode); m.run(); tot++;
    if (m.correct()) ok++; else { fail++; console.log(`  NG ${mode} ${a},${b} → 正 ${m.outP} 負 ${m.outM} 数えた ${m.counted()}`); }
    maxTicks = Math.max(maxTicks, m.ticks); maxWater = Math.max(maxWater, m.used); maxTips = Math.max(maxTips, m.tips);
  }
  console.log(`  ${mode === "add" ? "足し算" : "引き算"}：${ok}/${tot} 正しい（計算 最大 ${maxTicks} 拍、計数添水 最大 ${maxTips} 回、電源の水 最大 ${maxWater}u）`);
}
for (const [a, b, md] of [[3, 4, "sub"], [7, 3, "sub"], [3, 4, "add"]]) {
  const m = new AddSubMachine(a, b, md); m.run();
  console.log(`  例：${a} ${md === "add" ? "+" : "−"} ${b} → 正の桶 ${m.outP}u・負の桶 ${m.outM}u → カウント係「${m.evalSign < 0 ? "負の桶から" : "正の桶から"} ${m.evalCount} 回」＝ ${m.counted()}`);
}

console.log("\n== 升・添水の精度（各 300 回、a = 7, b = 9。入力・計算・評価のすべてに誤差）");
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
