# P0-01: NGSolve独立照合 — 2026-09-07

円筒と円錐台の合成真空PEC空洞について、基本m=0 TMモードを照合した。
実機構造ではない。結果は `out/independent-ngsolve-20260907-first/comparison.json`。
両側3段階の細分、周波数・R/Q・G、内部12点の磁場がPASS。
生JSONはGit対象外だが、入力・再現コマンド・主要数値は本記録とスクリプトに保持する。

## 独立性と検証範囲

NGは既存のu=Hphi/r、P1、構造由来メッシュを使う。
参照はNetgenの独立三角形とNGSolveの3次H1、未知数h=Hphi、軸h=0を使う。
参照弱形式はMaxwellのcurlエネルギーから独立に実装した
`∫ r[(h_r+h/r)(v_r+v/r)+h_z v_z] = k² ∫ r h v`。
PECは自然境界。体積エネルギーと壁磁場積分はNGSolve、軸電圧は参照メッシュの
各軸辺に12点Gauss積分を適用する。軸Ezは体積要素側からの `2 h_r/(omega epsilon)`。
NGのメッシュ・行列組立・場復元・RF積分は参照側へ渡さない。
SciPy/ARPACKの固有値計算、定数値と物理仕様は共通で、完全に独立したスタックではない。

初回試作ではNGSolveの境界勾配を使うと軸の半径微分が消え、R/Q=0となった。
円筒解析解で検出し、体積要素での評価へ修正した。周波数一致だけでは発見できなかった。
円筒のBessel磁場・解析RF量を検査するoptional unittestでこの問題を防ぐ。

全形状は長さ0.12 m。円筒半径0.08 m、円錐台は入口0.08 m、出口0.10 mの直線壁。
円錐台の側壁は滑らかだが端板との接合角を持つ。表面ピーク精度の検証形状ではない。
SI、peak phasor、U=1 J、beta=1、R/Q=|V|²/(omega U)。回路規約の半値も別名で保存。
NGのnr=32/64/128、nz=2nr。参照maxh=0.012/0.006/0.003 m、order=3。

| 最終NG–参照の相対差 | 円筒 | 円錐台 | 許容値 |
|---|---:|---:|---:|
| 周波数 | 2.6734e-7 | 4.3156e-7 | 1e-4 |
| R/Q | 2.4007e-4 | 2.4801e-4 | 0.005 |
| G | 7.8077e-8 | 7.5608e-7 | 0.005 |
| 内部Hphiの12点相対L2差 | 7.0202e-6 | 9.2001e-6 | 0.005 |

最終細分変化も各ソルバーに同じ周波数・RF許容値を適用した。
最大R/Q変化はNG 0.06230%、参照0.0002809%。
円筒の参照対解析差は周波数3.00e-13、R/Q 1.835e-7、G 9.22e-13。
磁場は同じUのまま全体符号のみ揃え、点ごとのフィットはしない。
磁場プローブは体積全体の誤差保証ではなく、表面ピーク・高次モードとは別検査。
同じ値でも未収束ならFAIL、共通の誤りは円筒解析検査でFAILとなることをテストした。

最細NGは各33153自由度、参照は円筒11461/円錐台12844自由度。
この環境で3段階両側のsolve/後処理は各計0.88/0.90秒（import等を除く）。
一般形状や大規模計算の性能比較ではない。計算中のsource/tests/scripts/examples hashは不変。

## 再現

NGSolveは通常の製品依存へ追加していない。検証専用の新しい仮想環境で実行する。
実測環境の全パッケージはDEPENDENCIES.mdに記録。

```bash
python3 -m venv /tmp/superfish-independent-new
/tmp/superfish-independent-new/bin/python -m pip install ngsolve==6.2.2606 numpy==2.5.3 scipy==1.18.1
OPENBLAS_NUM_THREADS=1 /tmp/superfish-independent-new/bin/python scripts/compare_ngsolve.py --out out/independent-new
PYTHONPATH=src OPENBLAS_NUM_THREADS=1 /tmp/superfish-independent-new/bin/python -m unittest discover -s tests -p test_independent_comparison.py -v
```

optional検査は6件PASS。通常環境では参照物理2件を理由付きskipし、判定ロジック4件は実行する。
本体の数式・既定値・ベンチマークを変更していない。既存回帰検証は
`out/validation-independent-20260907/`。旧SUPERFISHの追加実行・参照はない。
通常suiteは107件中105件合格・参照環境専用2件skip。標準数値検証PASS。
seedの円筒6モード・shaped 3モードに対して周波数差ゼロ、
R/Q・G・Q0・Vaccの相対差最大6.67e-16。基準値と許容値の変更なし。

API参照は [NGSolve公式2D geometry](https://ngsolve.org/ngsolve/docs/i-tutorials/unit-4.1.1-geom2d/geom2d.html)
および [公式H1/BilinearFormの説明](https://ngsolve.org/ngsolve/docs/i-tutorials/unit-7-optimization/02_Shape_Derivative_Laplace.html)。
公開APIの利用法を確認し、外部ソルバーの実装コードはコピーしていない。
