# 02 流体素子・液体コンピュータ

水・気泡・液滴・化学反応などの流体で計算する、工学・実験の研究です。

## 酒船石を流体素子として見る研究

### ✅ 村上優依・窪田佳寛・望月修（2017）「酒船石が流体素子であった可能性に関する考察」『ながれ』36, 417–420
- URL: https://www.nagare.or.jp/download/noauth.html?d=36-6_tokushu13.pdf&dir=64
- 書誌と考古学側の内容は [01_archaeology.md](01_archaeology.md) にあります。
- 実験の内容：
  - くぼみ部分を約1/30に縮小した模型を3Dプリンタで作製し、約6度傾けて設置
  - A1から一定の水位で注水し、出口Fから出た水で水車を回して、10秒間の回転数を測定
  - 何もつながない基準モデルは56回転。ポートのつなぎ方を変えると49〜57回転
  - A3-BL と A3-CL の1箇所の違いで、57回転と49回転の差が出た
  - フィードバックの組み合わせ63通りのうち11通りで出口に強い影響。DLが最も影響を受けた
- 結論：溝の形は流体素子のフリップフロップ回路のように見え、フィードバックのつなぎ方で流出が変わる。
- 評価：示されたのは「つなぎ方で流量が変わる」ことまで。2つの状態を保持できること（双安定性）は未実証。

### ❓ 野坂弥□（1966）「流体素子の応用について」『島根大学論集（自然科学）』No.16, pp.27–44
- 村上ら2017の引用文献です。著者名の最後の1字は文字化けで判読できませんでした。

## 液体コンピュータの総説

### 📘 Adamatzky, A. (2019). A brief history of liquid computers. *Philosophical Transactions of the Royal Society B*, 374(1774), 20180372.
- DOI: 10.1098/rstb.2018.0372
- 液体を使った計算機の歴史をまとめた総説。全体像をつかむ入口になります。

## 気泡・液滴の論理回路

### 📘 Prakash, M. & Gershenfeld, N. (2007). Microfluidic Bubble Logic. *Science*, 315(5813), 832–835.
- DOI: 10.1126/science.1136907
- マイクロ流路の中の気泡で論理ゲート・記憶・同期を作り、流体だけで普遍的な計算ができることを示した。

### 📘 Katsikis, G., Cybulski, J.S., & Prakash, M. (2015). Synchronous universal droplet logic and control. *Nature Physics*.
- DOI: 10.1038/nphys3341
- 回転磁場をクロックにして、磁性液滴で同期式の論理回路を作った。

### ❓ Abdel-Ghani, Abbas, Maksymov (2025). Reservoir Computing with a Single Oscillating Gas Bubble.
- 単一の気泡の振動をリザバーコンピューティングに使う。元メモに書かれていた情報で、書誌は未確認。

## 水による計算

### ✅ Henderson, A., Nicolescu, R., Dinneen, M.J., Chan, T.N., Happe, H., & Hinze, T. (2021). Turing completeness of water computing. *Journal of Membrane Computing*, 3(3), 182–193.
- DOI: 10.1007/s41965-021-00081-3
- 書誌は大学の論文リポジトリで確認済み（https://researchonline.jcu.edu.au/75511/ ）。本文は未読で、以下は要旨にもとづく。
- 「水の計算」を、膜計算（P systems）の一種として扱った研究。タンクを点、パイプを線とする、ループのない有向グラフで計算する。水は上から下へ一方向にだけ落ちる。流れの制御にはサイフォンではなく弁を使う。
- 改良した設計で、次の3つの課題を解決した。
  - 関数を積み重ねても弁の数が爆発的に増えない
  - 計算の終了を検知できる
  - 装置をリセットできる
- μ再帰関数を組み立てられることを示して、チューリング完全性を証明した。
- 元メモでは「CDMTCS-554（オークランド大学の技術報告）」とされていた。同じ研究の技術報告版の可能性があるが、未確認。
- 関連：同じグループの "Programmable and parallel water computing"（https://portfolio.jcu.edu.au/Publications/JCU178829 ）。書誌は未確認。

## サイフォン（教訓茶碗・ピタゴラスカップ）による計算

ピタゴラスカップ（日本では「教訓茶碗」）は、水位が中央の柱の高さを超えるとサイフォンが起動し、中身が底から全部抜ける器です。「しきい値」と「溜めた水を全部一気に流す」を1つの部品で兼ねているので、論理ゲートの素子になります。

### ❓ Steve Mould による、欲張りカップ（greedy cup）サイフォンの水の加算器（YouTube動画）
- 紹介記事：https://interestingengineering.com/videos/will-a-computer-actually-work-on-logic-gates-running-on-water
- サイフォンを工夫してXORゲートとANDゲートを作り、それをつないで4ビットの2進数の足し算をした。
- 苦労した点：あるゲートの背面を水がサイフォンで伝って漏れる不具合（本人は「メモリリーク」と呼んでいる）。計算のたびに全ゲートの水を抜いてリセットする必要がある。
- 未確認：動画のタイトル・公開年、ゲート内部の具体的な構造。本プロジェクトでは動画を見ていない。

### ❓ FIT2014（第13回情報科学技術フォーラム）講演 A-016：サイフォンと教訓茶碗による計算
- URL: https://www.ieice.org/publications/conference-FIT-DVDs/FIT2014/data/pdf/A-016.pdf
- 検索結果の要約による内容：決まった量の水とサイフォンだけで計算する。水が流れたら1、流れなければ0。必要な水の量は、計算時間ではなく入力の数に比例するだけ。しきい値素子として教訓茶碗を使う。
- 未確認：タイトル・著者。PDFはサーバーがアクセスを拒否し、本文を読めていない。

## 化学（液体）による計算

### ❓ Gahler, Thomas, Lach, Cronin (2025). Achieving Operational Universality through a Turing Complete Chemputer.
- 化学合成の自動化装置（Chemputer）がチューリング完全であることを示した。元メモに書かれていた情報で、書誌は未確認。

## 要調査

- 壁面付着（コアンダ効果）を使う古典的な流体フリップフロップの基本文献。村上ら2017の「フリップフロップ」説を検討するのに必要。
- 鹿威し・転倒升を使った機械式カウンタの先行事例。
- FIT2014 A-016 の本文と著者。
- Steve Mould の動画のゲート構造（動画を見て確認する）。
