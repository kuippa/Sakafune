# 03 数学：流体方程式とチューリング完全性

オイラー方程式・ナビエ–ストークス方程式の解の中にチューリング機械を埋め込めるか、という数学の研究です。

**読むときの注意**：これらの結果は「チューリング機械をシミュレートする流れが、特定の条件の下で数学的に存在する」ことを示すものです。そのため「流体の長期的なふるまいは、原理的に予測できない（決定不能な）場合がある」と言えます。一方で、水で計算機を作る方法を示しているわけではありません。工学的な実装については [02_fluidics.md](02_fluidics.md) を見てください。

## 発端

### 📘 Tao, T. (2016). Finite time blowup for an averaged three-dimensional Navier–Stokes equation. *Journal of the American Mathematical Society*, 29, 601–674.
- ナビエ–ストークス方程式を「平均化」した版で、解が有限時間で発散（爆発）することを示した。
- 流体の中に論理回路のような仕組みを組み込み、自己複製させれば爆発を起こせるのではないか、という「流体コンピュータ」の構想を述べたことで、この分野の出発点の一つになった。

## オイラー流のチューリング完全性

### 📘 Cardona, R., Miranda, E., Peralta-Salas, D., & Presas, F. (2021). Constructing Turing complete Euler flows in dimension 3. *Proceedings of the National Academy of Sciences*, 118(19), e2026818118.
- 3次元のある空間（リーマン多様体）の上に、チューリング完全なオイラー方程式の定常解が存在することを示した。

### ❓ Cardona, R., Miranda, E., & Peralta-Salas, D. (2025). Towards a Fluid Computer. *Foundations of Computational Mathematics*, 25, 1921–1937.
- DOI: 10.1007/s10208-025-09699-6
- 3次元のオイラー流にチューリング機械を埋め込む。元メモに書かれていた書誌で、巻・ページは未確認。

## ナビエ–ストークス方程式（粘性あり）

### ❓ Dyhr, S., González-Prieto, Á., Miranda, E., & Peralta-Salas, D. (2025). Turing complete Navier–Stokes steady states via cosymplectic geometry.
- arXiv:2507.07696。元メモには *PNAS Nexus* 5, pgag131（DOI: 10.1093/pnasnexus/pgag131）への掲載情報もあるが、未確認。
- 粘性のあるナビエ–ストークス方程式の定常解でも、チューリング完全なものが作れることを示した。

## 総説

### ❓ González-Prieto, Á., Miranda, E., & Peralta-Salas, D. (2025). Universality in computable dynamical systems: old and new. *Journal of Physics: Complexity*, 6(3), 035014.
- DOI: 10.1088/2632-072X/ae00b5
- 流体を含む力学系の「普遍性（任意の計算をシミュレートできること）」を、古典から最新まで整理した総説。元メモに書かれていた書誌で、未確認。

## 関連する古典

### 📘 Moore, C. (1990). Unpredictability and undecidability in dynamical systems. *Physical Review Letters*, 64(20), 2354–2357.
- 低次元の力学系（ビリヤード球のような単純な系）でもチューリング機械をシミュレートでき、長期的なふるまいが決定不能になりうることを示した。流体のチューリング完全性の研究は、この考え方を流体方程式に広げたもの。
