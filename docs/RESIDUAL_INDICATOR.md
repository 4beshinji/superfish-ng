# N04 直線P1/P2の残差指標と細分対象選択

2026-09-08。`residual_indicator.py` は、計算済みの真空・軸接続m=0 TM場から
要素内・内部辺・自然境界の残差を計算する。二次曲線幾何は拒否する。
同じ直線多角形領域内の細分優先度であり、解析曲線への幾何近似誤差は含まない。
`physical_error_bound` は常にnull。周波数、RF積分、表面ピークの誤差上界ではない。

## 導出と定義

[PHYSICS.md](PHYSICS.md)の弱形式を要素ごとに部分積分すると、内部の方程式は
`-div(r³ grad u) = λ r³ u`、`λ=k²`、`Hphi=r*u` となる。
要素内の多項式残差を `ρ = r Δu + 3 u_r + λ r u` と置く。
内部分布の残差は `r²ρ` である。内部辺の残差を
`j = r (grad u_left·n_left + grad u_right·n_right)` とし、自然境界では
`j = r grad u·n + 2 n_r u` とする。法線は各三角形から外向き。
PEC壁の `2 n_r u` は必須で、傾斜壁にも適用する。
内部辺では連続なuと逆向き法線のため、この項は相殺する。

各三角形の二乗指標は次の和を使う。

- 要素内: `h_T² ∫_T r ρ² dr dz`。h_Tは最長辺。
- 内部辺: `h_e ∫_e r j² ds` の半分を両隣へ配分する。辺は一度だけ数える。
- PEC/electric_symmetry境界: 同じ辺積分の全量を所有要素へ配分する。

h_eは辺長。軸ではrの重みが消えるため境界罰則を付けず、有限なuを保持する。
magnetic_symmetryは本質条件なので自然境界罰則を付けず、該当自由度のu=0を検査する。
P2のラプラシアンは定数の基底二階微分から計算する。要素内はDuffy積Gaussの5次、
辺は4点Gaussで、直線P1/P2の被積分多項式を丸め誤差の範囲で積分する。
全成分を既存の正のエネルギー `u.T K u` で割り、合計の平方根を無次元指標とする。
二乗前に場を最大絶対係数で割り、符号・正規化の影響を除く。

一般の要素残差/辺残差の分解は[R33](REFERENCES.md)を背景とする。
本重みは本PJの強形式から独自に選んだもので、軸で退化するr³係数の固有値問題に
同資料の一様楕円型問題の誤差評価定理をそのまま適用したものではない。
指標の信頼性定数・誤差上界・最適性は証明していない。代数残差とは別の量である。

## API

```python
from superfish_ng import Case, solve
from superfish_ng.residual_indicator import residual_indicator, mark_bulk
from superfish_ng.marked_refinement import refine_marked_cells
from superfish_ng.mesh_input import mesh_to_dict

case = Case.load('examples/pillbox.json')
solution = solve(case)
indicator = residual_indicator(case, solution, mode=0)
marked = mark_bulk(indicator['cell_relative_squared'], fraction=0.5)
if marked:
    refined = refine_marked_cells(case, solution.mesh, marked)
    next_solution = solve(case, mesh_data=mesh_to_dict(refined.mesh))
```

caseとsolutionの次数・全境界を照合する。solutionはnative solve/read_solutionで得たものを使う。
`mode`は0始まりの順位であり永続IDではない。複数モードをまたぐ反復では別途追跡を行う。
戻り値は要素順の `volume_relative_squared`、`interior_relative_squared`、
`boundary_relative_squared`、その和 `cell_relative_squared` と `relative_indicator` を持つ。
場や入力メッシュは変更しない。不正モード・非有限場・ゼロ場・非正固有値・拘束違反は拒否する。

`mark_bulk` は非負の二乗指標を大きい順に並べ、合計の指定割合を覆う最短の先頭列を返す。
同値は要素番号順、fractionは `(0,1]`、全ゼロなら空配列。fraction=1では正の全要素。
総和のオーバーフローを避けるため最大値で尺度化する。選択は浮動小数点の指標に基づく。
品質/要素上限と隣接閉包による追加細分は[細分API](MARKED_REFINEMENT.md)が検査する。

## 検証と残件

5つのunittestで、全体多項式u=rとu=r²+z²の独立体積/壁積分、折れ曲がる連続P1の
内部辺ジャンプと一回分の配分、軸/両対称面、振幅/長さ相似、不正入力、選択順序を確認する。
円筒の実FEMでは代数残差が小さくても本指標がゼロにならないことを独立に確認する。

`OPENBLAS_NUM_THREADS=1 python scripts/validate_residual_indicator.py --out out/indicator-new`
で円筒・合成折返し輪郭×P1/P2×長さ1/2の孤立した最低モードを再計算し、
指標の50%選択と一様細分を各2回比較する。全水準のnative場・RF・指標、
要素/DOF・指標時間・細分/solve時間・周波数誤差を保存する。
解析円筒周波数、Ritz単調性、指標減少、相似則、尺度間の同じ選択を検査する。
選択の少なさだけで同じ誤差に対して効率が優れるとは判定しない。

一般モードの追跡付き適応停止、RF/表面量の個別停止基準、曲線局所細分、保存再開・CLI/GUI
の製品経路は残る。このAPI追加だけでN04全体を完了にしない。

最終受入: `out/n04-residual-indicator-final-20260908` PASS。指標相似則差最大3.182e-13、
f/RQ/G相似則差最大1.830e-13。円筒局所の周波数相対誤差はP1 1.103e-4→2.504e-5、
P2 1.040e-6→1.382e-7。別の独立積分で非ゼロλ項と傾斜PEC壁も4.663e-15以内で確認。
標準`out/validation-n04-residual-indicator-final-20260908`は576件中574合格・2 skip、
周波数差ゼロ・RF/エネルギー差最大8.882e-16。両検証のソースハッシュは最終実装と一致。
初回PASS後の入力診断修正と再検証の経過は[引継ぎ](CODEX_HANDOFF.md)に保持する。
