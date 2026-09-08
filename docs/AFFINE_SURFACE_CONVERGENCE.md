# 追跡済み直線要素の表面収束評価

2026-09-08追記: [版3](ADAPTIVE_SURFACE_STOPPING.md)はピーク比区間を含む適応停止をAPI/CLI/JobManagerへ追加。以下の版1/版2の判定・保存契約は維持する。GUIの適応操作は版1/版2のみ。別途の直線表面評価は版3も全域確認条件付きで評価できる。

N03の直線P1/P2表面評価を、保存された適応細分チェックポイントへ接続する。
最低3水準のnative場を全再検証し、個別IDに対応するf・加速器規約R/Q・G・
Epk/Eacc・Bpk/Eaccの直近2区間の変化を別々に評価する。
これは離散結果の変化に対する判定であり、物理誤差上界ではない。

## 前提と角診断

入力チェックポイントは既存の版1/版2の適応再検証を通ること。
初期メッシュから選択・細分・全追跡・元ファイルまで再構築するため、
異なる形状・元要求・未知メッシュへ無断で移る系列は受理しない。
全水準で個別IDが確認できる対象だけを使い、周波数順位をIDの代用にしない。
元の適応の対象と別のIDも、そのIDが全水準で個別確認されていれば評価できる。

角の診断はCaseの元多角形を使う。細分節点の丸めで生じた微小折れを新しい角に数えない。
保存二進値を厳密有理数として、隣接辺ベクトルの外積・内積の符号を求める。

| 接続 | 診断 |
|---|---|
| PEC同士 | 正の外積は凸角、負は再入角、外積0かつ正の内積は直線接続 |
| 軸と壁/対称面 | 接続辺の軸方向成分が厳密に0なら直交、その他は未確認 |
| PECと電気/磁気対称面 | 凸かつ内積0の直角だけを確認、その他は未確認 |
| 同じ軸/対称面の直線分割 | 同じ境界の分割点として扱う |
| 解析曲線の弦近似 | 多角形診断とは別に元解析幾何が未確認であることを保持 |

再入角があればSINGULAR_GEOMETRYとしてピーク受入を妨げる。
これは特異項の係数が必ず非零であることを証明するものではない。
非直交の軸接続・その他の境界接続、arc_profile/curved_contourの弦近似はUNVERIFIED_GEOMETRY。
それ以外はNO_REENTRANT_CORNERSであるが、物理的な正則性の証明ではない。
geometry_approximation_assessed=false、physical_error_bound=nullを維持する。

## 各量の判定

周波数は1e-4、R/Q・Gは0.005、電場・磁場ピーク比は0.01を使い、曲線表面評価と同じ基準を維持する。
直線離散場の[連続ピーク上下界](AFFINE_SURFACE_EXTREMA.md)を各水準で再計算する。
Eaccによる除算と磁場単位換算は有理数で計算し、上下へ外向きに丸める。
各区間の変化は前後の上下界の全組合せを包含する上限から判定し、上側推定値同士だけでは比較しない。
直近2区間の五量がすべて条件内の場合だけTARGETS_MET。
Eaccが有意でない、比が表現不能、比較に必要な正の下界がない場合はUNVERIFIED。
有効な値が基準外ならNOT_CONVERGEDを返す。

版2の系列では最後の2水準がともにuniform_confirmationであることも要求する。
差が条件内でも全域確認が足りなければCONFIRMATION_PENDING。
版1では局所差の診断であることをuniform_confirmation_required=falseとして保持し、自動昇格しない。
幾何の未確認/再入角診断は、数値の細分差が条件内でも上書きされない。

## 保存・CLI

```python
from superfish_ng.adaptive_refinement import read_adaptive_refinement
from superfish_ng.affine_surface_convergence import save_affine_surface_convergence, read_affine_surface_convergence

checkpoint = read_adaptive_refinement("out/adaptive/checkpoint-005.json")
result = save_affine_surface_convergence(checkpoint, "fundamental", "out/surface-new.json")
verified = read_affine_surface_convergence("out/surface-new.json")
```

```bash
superfish-ng assess-affine-surface-convergence out/adaptive/checkpoint-005.json --mode-id fundamental --out out/surface-new.json
superfish-ng replay-affine-surface-convergence out/surface-new.json
```

出力は新規ファイルに限定し、元チェックポイント、対象ID、全水準の区間、連続離散ピーク、
全区間の比較、採用した最後の2区間、元輪郭の角診断と判定を保存する。
再検証は全native場と判断を再構築して文書全体を比較する。改変・元ファイル変更は拒否する。
CLI終了値はTARGETS_METが0、保存された未達・未確認・確認待ちは1。
入力/計算/再検証の失敗は新規結果を公開しない。

元の適応チェックポイントの停止判定やsurface_status=UNASSESSEDは書き換えない。
この文書は別の表面評価であり、適応計算を表面量に基づいて継続・停止させる機能は次段階。

## 検証と残件

5検査で既知凸角/再入角、2の±100乗の尺度、軸/境界分割、対称面/弦近似の扱い、
実P2系列の全域確認途中・対象順位2・保存/CLI再検証、改変/短い系列/未確認IDの拒否、
再入形状の実FEM系列の非受入を確認する。
独立`scripts/validate_affine_surface_convergence.py`はP1/P2円筒の新規適応計算と尺度1/2・U=尺度²を使い、
最終区間の両端を解析f/RQ/G/ピーク比と個別比較する。P1の細分差未達があればその状態も保持する。

通常RF/GUIへの統合、表面量を含む適応停止、一般形状の精度/効率受入、曲線局所細分は未完。
N03/N04親課題全体の完了ではない。

独立初回out/n03-affine-surface-initial-20260908はPASS。P2は5水準（全域2回）でTARGETS_MET。
P1は8水準・4948要素/2533 DOFで元適応がLEVEL_LIMIT、表面はCONFIRMATION_PENDINGを保持した。
直近の変化が基準内でも全域確認は未実施であり、P1の版2確認完了とは数えない。
CONFIRMATION_PENDINGは不足する確認の診断で、元チェックポイントが再開可能という意味ではない。
このP1の元終端判定からは直接再開できない。

最終区間の両端と解析値との相対差はP1 f 1.086e-6、RQ 0.003934、G 5.130e-6、
E比0.0008186、B比0.001981以内。P2はf 6.953e-10、RQ 1.674e-6、G 2.756e-9、
E比4.403e-7、B比5.350e-7以内。相似則差最大2.776e-14。
版1もout/n03-affine-surface-v1-20260908で3水準の新規実計算・保存全再検証を行い、
局所差のTARGETS_METを確認。uniform_confirmation_required=false、two_uniform_steps_present=nullを保持。

## 直線表面評価のGUI接続

[直線表面評価GUI](GUI_AFFINE_SURFACE_CONVERGENCE.md)で、適応結果から個別IDを指定して評価、
保存/再検証、評価した最終対象場の表示を利用できる。表面量を含む適応停止は未完。
