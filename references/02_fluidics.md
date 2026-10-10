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

### ❓ Henderson, A., Nicolescu, R., Dinneen, M.J., et al. (2021). Turing Completeness of Water Computing. CDMTCS-554, University of Auckland.
- タンクと管と弁による「水の計算」がチューリング完全であることを論じた技術報告。本プロジェクトのカウンタ機械方式にいちばん近い。
- 元メモに書かれていた情報で、報告番号などは未確認。

## 化学（液体）による計算

### ❓ Gahler, Thomas, Lach, Cronin (2025). Achieving Operational Universality through a Turing Complete Chemputer.
- 化学合成の自動化装置（Chemputer）がチューリング完全であることを示した。元メモに書かれていた情報で、書誌は未確認。

## 要調査

- 壁面付着（コアンダ効果）を使う古典的な流体フリップフロップの基本文献。村上ら2017の「フリップフロップ」説を検討するのに必要。
- 鹿威し・転倒升・サイフォンを使った機械式カウンタの先行事例。
