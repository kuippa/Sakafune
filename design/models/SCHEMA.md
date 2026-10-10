# モデル定義（YAML）の書き方

`design/models/*.yaml` は、水の計算装置の構成を書く**正本**です。図（`tools/render_iso.py`）とシミュレーションは、ここから作ります。

## 全体の構成
```yaml
meta:        # id・タイトル・作成者・状態など
units:       # 長さ cm、体積 mL、1単位 u_mL
parts:       # 部品の一覧
procedure:   # 人の操作の手順（判断なし）
cases:       # 入力と、期待される出力
readout:     # 結果の読み方（図の状態パネルに使う）
assumptions: # 前提と未確認事項（✅💭❓）
```

## 部品（parts）
すべての部品に、`id`、`type`、`name`、`inner_diameter_cm`（円筒の内径）、`position: [x, y, z]`（底の中心、cm）を書きます。

| type | 意味 | 追加の項目 |
|---|---|---|
| `metering_cup` | 計量の器。`volume_mL` を超えた分は `overflow_to` へ溢れる | `volume_mL`, `overflow_to`（省略可）, `drain_to`（栓／注ぎ口の行き先） |
| `siphon_cup` | 教訓桝。中身が `threshold_mL` 以上になると、全部が `siphon_to` へ抜ける | `threshold_mL`, `capacity_mL`, `siphon_to`, `siphon_tube_inner_diameter_mm`, `drain_to`（栓の行き先、省略可） |
| `holed_cup` | 穴あき桝。中身が `hole_mL` を超えた分だけ、側面の穴から `hole_to` へ出る | `hole_mL`, `capacity_mL`, `hole_to` |
| `splitter` | 分水口。来た水を `split_to` の行き先へ等分する | `split_to`（リスト） |
| `tipping_bucket` | 両升（左右に升がある転倒升）。上の升に `compartment_mL` 溜まるたびに傾いて中身を出し、向きが 0↔1 と入れ替わる（初めは向き0） | `compartment_mL`, `dump_to: [向き0で傾いたときの行き先, 向き1のとき]` |
| `vane` | 振り分け板。`bucket` の両升と同じ軸で動き、来た水を向きに応じて振り分ける | `bucket`, `route_to: [向き0のとき, 向き1のとき]` |
| `sozu` | 添水（鹿威し）。中身が `threshold_mL` 以上になると傾いて全部を `dump_to` へ出し、空で戻る | `threshold_mL`, `capacity_mL`, `dump_to` |
| `chute` | 受け樋。来た水を、人が向けた先へ流す。初めの向きは `route` | `route`, `route_options`（図に描く行き先の候補） |
| `basin` | 受けの器。ためるだけ | `capacity_mL` |

共通の省略可能な項目：
- `notes`：図の注釈に足す文（リスト）
- `callout: [dx, dy]`：図の注釈の箱の位置（器の左下からのずれ、ピクセル）。見た目の調整用で、物理的な意味はない
- `hide_callout: true`：注釈の箱を出さない
- `tag`：器の真下に書く短い名前

図全体の調整として、`layout.fit_box: [x0, y0, x1, y1]`（装置を収める範囲、ピクセル。y1 が負なら下端からの距離）も書けます。

## 操作（procedure）
人の操作を順に並べます。**中身を見て操作を変えることはしません**（判断なし）。

| 操作 | 意味 |
|---|---|
| `fill: X` | 計量の器 X を、溢れるまで満たす |
| `release: X` | X の中身を全部 `drain_to` へ出す（栓を抜く・注ぐ）。空なら何も起きない |
| `set_route: R, to: Y` | 受け樋 R を Y へ向ける（決まった順に向けるだけ。判断なし） |

各操作の後、水の動き（サイフォン・溢れ）が落ち着くまで待つものとします。`phase` で段階の名前を付けられます。

## 入力と期待される出力（cases）
```yaml
cases:
  - id: a1b0c1
    inputs: {IA: 1, IB: 0, IC: 1}   # 1 の計量の器だけ、最初に満たしておく
    repeat: 1                        # 手順を繰り返す回数（省略時 1）
    expect: {S_out: 0, C_out: 1}     # 1＝水がある、0＝空
```
描画スクリプトは、すべての case をシミュレーションで照合し、食い違いがあれば終了コード1で終わります。

## 結果の読み方（readout）
- `kind: binary` と `order: [S3, S2, S1, S0]`：水のある器を1として、2進数で読む
- `kind: named` と `items: [{id: S_out, label: 和 S}, …]`：出力ごとに読む
