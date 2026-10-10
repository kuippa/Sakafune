# 04 計算理論

「チューリング完全」とは何か、どこまで作れば足りるのかを決めるための基礎文献です。

## チューリング機械

### 📘 Turing, A. M. (1936). On Computable Numbers, with an Application to the Entscheidungsproblem. *Proceedings of the London Mathematical Society*, s2-42(1), 230–265.
- チューリング機械の原論文。「計算できる」とはどういうことかを定義した。

## カウンタ機械（Minsky機械）

本プロジェクトの設計方針の根拠です。0と1の論理ゲートを組むのではなく、**水の量をそのまま数（カウンタ）として扱う**。

### 📘 Minsky, M. L. (1961). Recursive Unsolvability of Post's Problem of "Tag" and Other Topics in Theory of Turing Machines. *Annals of Mathematics*, 74(3), 437–455.
- カウンタが2本あるだけの機械でも、チューリング機械をシミュレートできることを示した。

### 📘 Minsky, M. L. (1967). *Computation: Finite and Infinite Machines*. Prentice-Hall.
- カウンタ機械を教科書としてまとめた本。命令は次の2種類だけ。
  - INC：カウンタを1増やし、次の命令へ進む
  - DEC：カウンタが0なら別の命令へ分岐し、0でなければ1減らして次へ進む
- 2カウンタでチューリング機械をシミュレートすると、計算時間は指数的に長くなる。

## 設計への対応

| 計算理論の要素 | 水の装置での実現（案） |
|---|---|
| カウンタ | 甕の水量 |
| INC | くぼみで量った「1単位」の水を甕へ注ぐ |
| DEC と 0判定 | 甕の浮きで流れの向きを切り替え、浮き弁で1単位だけ抜く |
| プログラム | 溝のつながり方、または人が栓を開け閉めする手順 |
| 停止 | 水が終端のくぼみに溜まる |

詳しくはリポジトリトップの [README](../README.md) の「設計の考え方」を見てください。
