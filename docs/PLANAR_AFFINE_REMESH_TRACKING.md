# 可逆アフィン変換と異なる内部メッシュの平面追跡

後続の[厳密アフィン共通分割API](PLANAR_EXACT_AFFINE_OVERLAY.md)では、変換を有理数で評価し、
境界分割を独立にした幾何基盤を追加した。以下の版6の要求・境界判定は維持する。
新APIは[専用追跡版7](PLANAR_EXACT_AFFINE_TRACKING.md)へ接続した。一般の丸めた境界の対応は残件。

明示多角形の厳密に可逆な2x2アフィン変換（せん断・異方尺度・鏡映・回転の合成を含む）と、内部節点・対角線・接続の独立な再メッシュを同時に宣言し、元の電場部分空間を比較する限定追跡である。要求/結果版は6、写像名は `polygon_affine_remesh`。旧版1〜5の要求・結果・再生の意味は変更しない。

境界の節点列は宣言変換の厳密な像でなければならない。内部の三角形分割は独立でよい。向きを反転する写像では境界の巡回方向と三角形の頂点順を正の向きへ正規化し、元のbarycentric座標で場を評価する。境界の分割密度を独立に選ぶ一般の再メッシュ合成は、binary64座標で厳密被覆を構成できないため未対応である。

## 対象と宣言

対象は、同じ偏波のCartesian遮断TE/TM、直線P1/P2の明示多角形Case版2である。前後の保存場は同じ物理多角形の可逆アフィン像で、三角形数・節点番号・対角線・内部節点位置は異なってよい。写像の行列式は厳密有理数で非零。せん断、異方尺度、鏡映、回転の合成を宣言できる。非線形変形、異なる多角形形状、曲線断面は未対応。

宣言は `x_current = linear_xy × x_previous + translation_xy_m`。`linear_xy` は有限な2x2行列で、`a×d-b×c` がbinary64値の厳密有理数として非零でなければならない。`translation_xy_m` はmの二成分。`inverse: true` は同じ宣言を逆方向 `x_current = A^{-1}(x_previous - t)` に使う。逆係数を別の丸めた値へ展開しない。

幾何の判定は、宣言変換を前の境界節点列へ適用した結果が現在の境界節点列とbinary64で完全一致すること、または宣言変換の厳密な逆評価を現在へ適用した結果が前の境界節点列と完全一致することを要求する。行列積と成分ごとの乗加算の二つの既知の演算順を受理する。頂点から写像を推定・fitしない。向き反転時はポリゴン順序と三角形の頂点順を正の向きへ正規化する。境界節点の密度・位置が異なる場合や、丸め差だけで一致する場合は、面積の厳密被覆が未検証となるため拒否する。

`max_candidate_tests` はBVH候補比較（節点比較と葉の比較の両方）の上限、`max_overlay_triangles` は入力要素数と交差分割数の上限である。資源上限は割当て前に検査する。

## 元場の比較

前の三角形を宣言変換したメッシュと現在の三角形を、binary64座標の有理数クリッピングで厳密に共通分割する。両側の各元三角形について、分割面積の総和が元面積と完全一致することを確認する。辺接触・点接触は面積に数えない。元のFEM多項式は元要素のbarycentric座標で評価し、節点平均や再補間で置き換えない。

TEの現在の横電場は、有効変換 `E`（`inverse` では `A^{-1}`）の余因子 `adj(E)=det(E)E^{-1}` を掛けて前の座標枠へ戻す。これは平面波 `E∝z×∇Hz` のプルバックと整合する宣言した対応で、相似写像では回転に一致する。TMの `Ez` は変換しない。積分は共通分割の物理xy面積で行い、3次と5次の差、Gram行列のPSD・正規化を再計算する。

反射（直交・det=−1）は固有問題の等長変換であり、周波数一致と正規化Gramの恒等を独立解析で確認する。異方尺度の矩形ではCartesian解析則を確認する。せん断は宣言した数値対応であり、厳密な固有周波数や物理収束の受入に含めない。平行移動・回転を含む一般アフィンは、元要素の二次多項式を移送したGram恒等式で検証する。

## 有限細分空間の診断と縮退

現在・前の各保存場について、多角形面積の逆数をシフトに使う回転不変な有限細分診断を行い、上端のguardモードへ帯域が届く場合は `UNVERIFIED` とする。追跡帯域の上には少なくとも1モード多く計算しておく。縮退群はID集合として運び、個別IDを確定しない。曖昧な対応や不足帯域で `UNVERIFIED` とした結果に採用値を与えない。異方尺度で順位が交差する帯域の個別IDは、物理場のGram対応で決まり周波数順位に従わない。

## 要求の生成と実行

```python
from pathlib import Path
import json
from superfish_ng.planar_tracking import PlanarTrackingRequest
from superfish_ng.planar_tracking_affine_remesh import PolygonAffineRemeshMapping

mapping = PolygonAffineRemeshMapping(
    linear_xy=[[0.8, 0.3], [-0.2, 1.1]],
    translation_xy_m=(0.04, -0.03),
    max_candidate_tests=2000000,
)
request = PlanarTrackingRequest(1, 1, ["fundamental"], mapping=mapping)
Path("tracking.json").write_text(json.dumps(request.to_dict(), indent=2) + "\n")
```

現在側のCaseは、前のメッシュの境界節点列に `mapping` を適用した座標を持つ独立メッシュとして作る。`PolygonAffineRemeshMapping.transform_mesh(mesh)` は宣言どおりのメッシュを返し（向き反転時は正の向きへ正規化する）、`_scalar_transform_mesh` は成分演算順の別評価を返す。`polygon_affine_remesh_overlay` は両方の演算順と厳密な逆評価を受理する。

```sh
python -m superfish_ng execute-planar-tracking previous-native current-native tracking.json --out new-tracking
python -m superfish_ng replay-planar-tracking new-tracking
```

要求JSONの `tracking_version` は6、`mapping.name` は `polygon_affine_remesh`。写像には `linear_xy`、`translation_xy_m`、`inverse`、`max_candidate_tests` の全項目を保存する。GUIでは「明示多角形：可逆アフィン変換＋異なる内部メッシュ」を選び、a・b・c・dの行列成分、移動、逆向き、候補上限を入力する。要求の読込/保存、結果ダウンロード、保存ジョブからの復元、元場の取込/表示、URL復元を同じ版6へ接続している。

## 判定と保存

3次・5次積分、元電場のGram、PSD、正規化、上端guard、有限細分診断、縮退部分空間を再計算する。結果の `physical_mapping` には宣言、`current_to_previous_linear`（余因子）、参照面積の説明、境界節点列の厳密一致、内部が独立であること、`signed_determinant` と向きの正規化を保存する。

両側の元native、要求、結果を所有コピーとして保存する。保存再生では元FEM場と幾何・対応判定を全再計算し、入力や結果の改変を拒否する。所有履歴では隣接するnative全ファイルの同一性と帯域・ID集合の連続性を要求し、同じ領域を解き直した場を前段の保存場へ黙って置き換えない。

## 受入証拠（2026-09-11）

- 追加9unit（26.041秒）: `tests/test_planar_tracking_affine_remesh.py`（厳密書式・版往復・反射を含む境界認識・独立内部・モーメント・余因子移送の点別恒等式・反射周波数と実FEM対応・異方矩形解析則・縮退/guard・worker/履歴）。
- 独立解析（26条件、75.754秒）: `out/planar-affine-remesh-independent-20260911`
  - 反射8条件: 解析恒等残差最大2.221e-16、P2最終FEM cross最大1.038e-4・周波数3.335e-4、P1最終cross最大4.669e-3・周波数9.311e-3。
  - 異方矩形8条件: P2最終周波数最大8.785e-5、P1最終1.591e-2、解析恒等残差最大2.323e-16。
  - 順位交差2条件: TEは順位[1,3,4,2]の個別IDでPASS、TMは帯域外像のためUNVERIFIEDを保持。
  - せん断8条件: P2多項式移送2.908e-16、P1 5.680e-5、厳密モーメント最大1.554e-15。
  - 拒否6条件: 非正則行列、誤宣言せん断、密度独立境界、非反射候補、候補予算、入力三角形予算。
- 実Chrome 9項目（外部HTTP 0、source不変）: `out/browser-planar-affine-remesh-20260911`
- 標準検証（956件、954合格、2skip、1513.289秒、source 548件不変）: `out/validation-planar-affine-remesh-final-20260911`
- seed回帰: pillbox/shaped_cellの9モード19量、最大相対差8.882e-16（周波数差0）。`out/validation-planar-affine-remesh-final-20260911/seed_regression.json`。

独立解析は、反射の直交性から周波数一致と解析Gram恒等を確認し、異方矩形の解析周波数則を最近傍の全単射で照合した。せん断後は厳密な固有周波数や物理収束を主張しない。

## 限界

- 境界節点列の厳密一致が必要で、境界の分割密度は独立に選べない。内部のみ独立である。
- 非線形・多値写像、異なる多角形形状、曲線断面は未対応。
- せん断・一般アフィンのモード対応は宣言した数値対応であり、連続経路のモード同一性、物理誤差上界、表面ピーク収束の保証ではない。
- 一般の多次元写像・曲線断面・親P02全体は継続する。
