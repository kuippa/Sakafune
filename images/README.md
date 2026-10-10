# images — 図・画像

このフォルダにある図・画像の一覧です。ファイル名の付け方は [AGENTS.md](../AGENTS.md) の「生成物のファイル名」を見てください。

| ファイル | 作成者 | 作成日 | 種類 | 内容・注意 |
|---|---|---|---|---|
| [sakafune_concept-rough_20261010_claude-opus-5-5.png](sakafune_concept-rough_20261010_claude-opus-5-5.png)<br>（元データ [.svg](sakafune_concept-rough_20261010_claude-opus-5-5.svg)） | Claude Opus 5.5（`claude-opus-5-5`） | 2026-10-10 | 模式図 | 東西断面の復元イメージ（路線B）。左下の上面図は模式で、実測図ではない |
| [level1-counter_iso_20261010_claude-opus-5-5.png](level1-counter_iso_20261010_claude-opus-5-5.png)<br>（元データ [.svg](level1-counter_iso_20261010_claude-opus-5-5.svg)） | Claude Opus 5.5（`claude-opus-5-5`） | 2026-10-10 | 模式図（**自動生成**） | 設計01 レベル1「教訓桝カウンタ」の3D斜め見下ろし図。[design/models/level1_counter.yaml](../design/models/level1_counter.yaml) から `tools/render_iso.py` で生成（5回注いだ後の状態）。手で直さず、YAMLを直して作り直す |
| [level2-full-adder_iso_20261010_claude-opus-5-5.png](level2-full-adder_iso_20261010_claude-opus-5-5.png)<br>（元データ [.svg](level2-full-adder_iso_20261010_claude-opus-5-5.svg)） | Claude Opus 5.5（`claude-opus-5-5`） | 2026-10-10 | 模式図（**自動生成**） | 設計01 レベル2「全加算器（栓付きの教訓桝2つ）」の3D斜め見下ろし図。[design/models/level2_full_adder.yaml](../design/models/level2_full_adder.yaml) から生成（a=1, b=0, c=1 の後の状態） |
| [level2b-xor-holes-dualrail_iso_20261010_claude-opus-5-5.png](level2b-xor-holes-dualrail_iso_20261010_claude-opus-5-5.png)<br>（元データ [.svg](level2b-xor-holes-dualrail_iso_20261010_claude-opus-5-5.svg)） | Claude Opus 5.5（`claude-opus-5-5`） | 2026-10-10 | 模式図（**自動生成**） | 設計02「穴あき桝だけの XOR（2本の溝で1ビット）」。[design/models/level2b_xor_holes_dualrail.yaml](../design/models/level2b_xor_holes_dualrail.yaml) から生成（a=1, b=1 の後の状態） |
| [level2c-xnor-toggle-reserve_iso_20261010_claude-opus-5-5.png](level2c-xnor-toggle-reserve_iso_20261010_claude-opus-5-5.png)<br>（元データ [.svg](level2c-xnor-toggle-reserve_iso_20261010_claude-opus-5-5.svg)） | Claude Opus 5.5（`claude-opus-5-5`） | 2026-10-10 | 模式図（**自動生成**） | 設計03「両升と予備の水 c で作る XOR／XNOR」。[design/models/level2c_xnor_toggle_reserve.yaml](../design/models/level2c_xnor_toggle_reserve.yaml) から生成（a=1, b=1 の後の状態）。両升・振り分け板の絵はごく簡単な模式 |
| [level2d-xor-sozu-reserve_iso_20261010_claude-opus-5-5.png](level2d-xor-sozu-reserve_iso_20261010_claude-opus-5-5.png)<br>（元データ [.svg](level2d-xor-sozu-reserve_iso_20261010_claude-opus-5-5.svg)） | Claude Opus 5.5（`claude-opus-5-5`） | 2026-10-10 | 模式図（**自動生成**） | 設計04「添水1つと予備の水で作る XOR／XNOR」。[design/models/level2d_xor_sozu_reserve.yaml](../design/models/level2d_xor_sozu_reserve.yaml) から生成（a=1, b=0 の後の状態）。添水・受け樋の絵はごく簡単な模式 |
| [sakafune_concept-reference_20261010_gemini-3-auto.jpg](sakafune_concept-reference_20261010_gemini-3-auto.jpg) | Gemini 3 系（自動選択。具体的なモデル名は不明） | 2026-10-10 | 参考画像 | 雰囲気をつかむための参考。**事実と合わない点がある**（下記） |

## Gemini参考画像の注意点

この画像は、全体の雰囲気をイメージするための**参考画像**です。考古学的な事実や設計の根拠には使わないでください。事実と合わない点は次のとおりです。

- 石が丸い岩として描かれている。実物は上面が平らな、細長い板状の石（長さ約5.5m・幅約2.3m・厚さ約1m）
- 東から西への約5.5度の傾きが描かれていない
- くぼみの番号が重複している（D4が2つ）。配置も実物と対応していない
- ガラスの水槽のような、飛鳥時代にはない部材が描かれている
- タイトルや「Carry Out」の表示が重複している
