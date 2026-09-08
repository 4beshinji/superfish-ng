# N04 二次曲線FEMの残差指標と局所選択

2026-09-08、直前基準6261292。
[直線残差指標](RESIDUAL_INDICATOR.md)の軸重み付き強形式・流束を、固定された二次幾何へ拡張する。
曲線のCase履歴から計算空間を再構築し、要素内・内部辺・自然境界の残差を分離する。
これは細分優先度であり、幾何近似誤差や周波数/RF/表面ピークの物理誤差上界ではない。

## 物理座標微分と曲線積分

強形式残差は `ρ = r Δu + 3 u_r + λ r u`。
参照座標ξから物理座標x=(r,z)への二次写像をX、J=∂X/∂ξとすると、連鎖律は

```
H_phys(u) = J^(-T) [H_ref(u) - Σ_a (∂u/∂x_a) H_ref(X_a)] J^(-1)
```

となる。括弧内の幾何二階微分項を落とさず、その物理HessianのtraceをΔuとする。
定数成分を引いてから微分し、並進や一定場の丸めによる相殺誤差を抑える。

要素内は `h_T² ∫ r ρ² dr dz`。h_Tは二次Bernstein制御点の凸包直径を使う。
これは曲線要素の直径を覆う幾何尺度の選択で、誤差評価定数の保証ではない。
内部辺は両側の外向き法線で `j = r(grad u_left·n_left + grad u_right·n_right)`。
自然境界のPEC/electric_symmetryは `j = r grad u·n + 2 n_r u`。
曲線の接線から法線とdsを求め、`h_e ∫ r j² ds` を内部辺なら両側へ半分ずつ配分する。
h_eは同じGauss則で計算する曲線辺の弧長。軸・magnetic_symmetryに自然境界罰則は加えない。
magnetic_symmetryの本質的な係数ゼロ拘束は検査する。

曲線では微分・辺積分が一般に有理式や平方根を含むので、多項式積分の厳密性は主張しない。
既定quadrature_order=12で、要素内Duffy積Gaussと各辺のGauss積分を行う。
別途2〜32の整数次数を指定して積分感度を調べられる。積分比較とメッシュ比較を混同しない。
規格化は、最大絶対係数で場を尺度化した後、同じ指標用積分次数で再構築した `u.T K u` を使う。
製品固有値解法・RF積分の式や次数を変更しない。

## APIとnative履歴

```python
from dataclasses import replace
from superfish_ng import solve
from superfish_ng.residual_indicator import residual_indicator, mark_bulk
from superfish_ng.curved_refinement_steps import CurvedRefinementStep

solution = solve(case)  # native curved Case, geometry_order=2
report = residual_indicator(case, solution, mode=0)
marked = mark_bulk(report['cell_relative_squared'], 0.5)
if marked:
    next_case = replace(case, curved_refinement_steps=case.curved_refinement_steps + (
        CurvedRefinementStep('marked', tuple(marked), 5.0),))
    next_solution = solve(next_case)
```

この例はcurved_refinement_levels=0のCaseを前提とする。従来levelsとの混在規約は
[履歴仕様](CURVED_REFINEMENT_HISTORY.md)を参照。modeは0始まりの順位で、永続IDではない。
反復中の交差をこの指標だけで追跡できるという意味ではない。

`curved_residual_indicator(case, solution, mode=0, quadrature_order=24)` で積分次数を変更する。
Case一致、元弦メッシュ・履歴（鏡映なら半領域出所）による幾何配列一致、実係数・非ゼロ場・
正固有値・本質拘束を検査する。solveまたはnative read_solutionで得た解を使う。
計算済み行列を盲信せず、規格化用行列を再構築する。固有値を解き直さない。
この検査は任意の正固有値・場が固有対であることを認証するものではない。

## 鏡映の扱い

磁気対称の奇鏡映は、対称面上の場ゼロと連続する法線微分により、規格化指標を保持する。
電気対称は弱い自然境界条件なので、離散場の点ごとの法線流束は一般にゼロではない。
偶鏡映で対称面は内部辺となり、法線流束ジャンプは半領域側の2倍となる。
半領域の規格化対称面二乗残差をbとすると、全領域でその寄与は2bとなり、
全指標の二乗は半領域の値よりbだけ大きくなる。他の複製寄与は倍のエネルギーで規格化して等しい。
したがって両対称で指標が一律に一致するという基準は使わない。

## 検証と残件

物理座標で一次/二次の既知場による勾配・ラプラシアン、独立した物理式の体積/曲線壁積分、
直線P2極限の三成分、振幅不変性、積分感度、native保存と両対称鏡映の変換則を検査する。
指標は小さい代数残差と同義ではない。複数の未収束メッシュで代数残差と別々に記録する。

scripts/validate_curved_residual_indicator.pyは合成円筒・楕円・双曲線×尺度1/2の孤立した最低モードで、
50%選択による局所細分を2回実行する。native解と指標、f/RQ/G/ピーク比、12対24点積分比較、
DOF/要素数・時間、Ritz単調性、円筒解析参照、相似則と選択番号を保存する。
保存先は新規ディレクトリ。独立検証JSONはnative runの外に保存し、完了manifestを変更しない。
これらの例の指標減少から一般的単調性・信頼性定数・同誤差での効率優位を推論しない。

曲線の追跡付き適応停止・保存再開/GUI、幾何誤差分離、一般形状の精度/効率と物理誤差上界は残る。

## 実行証拠

着手前632件中630合格・2 skip（390.927秒）。追加5検査PASS（5.700秒）。
最終独立検証 out/curved-indicator-selection-set-20260908 はPASS。18 native結果で、
円筒64→96→140、楕円360→423→589、双曲線216→250→354要素となった。
尺度1で指標はそれぞれ0.01267→0.004646、0.01634→0.005746、0.01650→0.006431へ減少。
全系列の最低周波数はRitz単調性を満たし、先頭2固有対の残差は最大7.676e-14。
12対24点積分の三成分L1差/全指標二乗は最大4.218e-13。
指標相似則差最大3.165e-13、五量相似則差最大1.033e-13。全水準で選択集合は同一。
円筒の最終解析差はf=1.263e-7、RQ=2.077e-4、G=2.414e-7、Epk/Eacc=2.676e-4、Bpk/Eacc=1.495e-4。
指標計算（幾何/行列再構築込み）の最大実測時間4.662秒。一般効率の受入ではない。
独立検証中のソース変更なし、記録hashは最終ソースに一致する。

初回out/curved-indicator-initial-20260908は、円筒の優先順位リスト一致条件でFAILを保持する。
選択集合は全水準で同一で、実際の細分はその集合をソートして行う。最終版は選択集合一致を確認し、順位差も別記録する。
数値条件・許容差・指標/選択アルゴリズムは変更なし。独立積分の参照尺度修正、対称面の変換則、
native固有値復元の1 ulp丸めの検査経過は[引継ぎ](CODEX_HANDOFF.md)とout/curved-indicator-development-20260908に記録した。

最終標準検証 out/validation-curved-indicator-20260908 は637件中635合格・2 skip（395.995秒）、PASS。
benchmarks/validationの全9モード・19量で周波数差ゼロ、RF/エネルギー差最大8.882e-16。
標準・独立検証の記録hashは最終ソースに一致する。検証中のソース変更なし。

