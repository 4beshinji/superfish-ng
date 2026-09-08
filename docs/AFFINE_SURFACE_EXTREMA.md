# 直線P1/P2の連続離散表面ピーク

N03の表面収束評価・N04の表面量停止へ接続する基盤として、固定直線三角形上の
表現された場のPECピークを上下から囲む。PASSは離散場の極値を囲んだことを示し、
物理ピークの収束、角の正則性、離散化誤差上界を意味しない。
既存RF値・通常保存形式・適応停止のsurface_status=UNASSESSEDは変更しない。

## 数学と表現

辺の保存端点順にt∈[0,1]を取り、隣接要素のP1/P2形状関数を制限する。
保存された二進浮動小数点の頂点・係数を厳密有理数へ変換する。
アフィンJacobian Jは三頂点の差から有理数で構成し、丸めた物理勾配や
P2中点座標を幾何として補間し直さない。P2の中辺自由度は既存の正規の節点順序で照合する。

u=Hφ/r、参照座標をξ,ηとすると、

- Hφ=r u。
- Erの分子はr(uξ rη−uη rξ)。
- Ezの分子は2u det(J)+r(uξ zη−uη zξ)。
- 電場の分母は正のdet(J)と、既存曲線ピーク契約と同じ二進値float(2π f ε0)の積。

P1では電場は一次・磁場は二次、P2では電場は二次・磁場は三次。
既存のrational_boundsによる厳密有理数Bernstein境界と区間二分を使い、
ベクトルノルムの全区間最大を囲む。sqrtの浮動小数点出力を外向きに丸める。
各PEC辺の下界・上界それぞれの最大を全体の境界として採用する。
角では両側の片側微分を保持し、平均しない。軸・電気/磁気対称面はPECピークに含めない。

既定の相対囲い幅は1e-6、各辺・各量の区間予算は10000。
予算不足や出力精度/範囲の限界ではUNVERIFIEDを含む例外を返し、標本最大だけで成功にしない。
位置は下界を与えた標本の位置であり、唯一の極値位置やその位置誤差の保証ではない。
parameter_fractionはその正確な辺パラメータ、point_rz_mは表示用の浮動小数点座標。

## API・保存・CLI

```python
from superfish_ng.affine_extrema import bound_affine_surface_peaks, save_affine_peaks, read_affine_peaks

bounds = bound_affine_surface_peaks(case, solution, mode=0)
saved = save_affine_peaks("out/native-run", "out/peaks-new.json", mode=0)
verified = read_affine_peaks("out/peaks-new.json")
```

APIのmodeは0始まり、CLIの--modeは1始まりの周波数順位。永続モードIDではない。

```bash
superfish-ng bound-affine-peaks out/native-run --mode 1 --out out/peaks-new.json
superfish-ng replay-affine-peaks out/peaks-new.json
```

CLIの--relative-toleranceと--max-boxes-per-edgeで囲い幅と予算を明示できる。
失敗時は非ゼロ終了し、新規文書を公開しない。出力先の上書きは拒否する。
文書は版1のaffine_discrete_surface_peaksで、元run・対象順位・予算・source hashと上下界を保存する。
再読込はnative場のK/M・固有対・正規化・RF整合を再検査して上下界を再構築し、文書全体を照合する。
元ファイルの変更や改変境界は拒否する。計算途中のsource変更も確認する。

直接APIは製造解による検査のため非固有場も受け取る。これは離散場の囲い込みのAPIであり、
その場合に固有値問題を満たすと認定するものではない。保存run経路では既存native再検証が前提となる。

## 検証と残件

5件の検査で、傾斜要素上の既知多項式場と独立な物理微分、既知の辺内部磁場最大、
区間予算不足、1e±100の振幅・符号・零場、対称面除外、入力/節点順序、native保存/CLI/改変拒否を確認する。
`scripts/validate_affine_extrema.py`は円筒P1/P2×尺度1/2×3メッシュの実FEMを計算し、
f・R/Q・G・Epk/Eacc・Bpk/Eaccを解析値と個別比較する。相似則、Ritz単調性、保存再検証も確認する。
解析式は検証だけに使用し、ソルバーやピーク計算へ渡さない。

角診断、複数水準の表面収束評価への統合、通常RF保存/GUI、適応表面量停止は次段階。
一般形状の物理ピーク受入や曲線局所細分は未完。N03/N04親課題は未受入。

独立初回out/n03-affine-extrema-initial-20260908はPASS。最終P1解析差はf 4.255e-6、
RQ 0.002867、G 3.782e-7。ピーク囲い込みの両端の解析差はE比0.0007910、B比0.001485以内。
P2はf 1.356e-9、RQ 6.556e-7、G 1.179e-8、ピーク両端差はE比2.757e-7、B比3.680e-7以内。
validation.jsonのピーク比較値は上下界中点であり、両端の比較はpeak_interval_reference.jsonへ別保存した。
相似則差最大3.997e-14。これらは円筒に対する数値比較であり、一般形状へ外挿しない。

後続の[直線表面収束評価](AFFINE_SURFACE_CONVERGENCE.md)で、元多角形の角診断と3水準以上の
追跡済み適応チェックポイントのf/RQ/G/ピーク比比較へ接続した。通常RF/GUIと適応停止統合は未完。
