# 相似変換と異なる内部メッシュの合成追跡

同じ多角形の相似変換（尺度・回転・SI平行移動）と、内部節点・対角線・接続の独立な再メッシュを同時に宣言し、元の電場部分空間を比較する限定追跡である。要求/結果版は5、写像名は `polygon_similarity_remesh`。旧版1〜4の要求・結果・再生の意味は変更しない。

境界の節点列は宣言変換の厳密な像でなければならない。内部の三角形分割は独立でよい。境界を丸め誤差の範囲だけで一致させた二つの領域は、厳密被覆に検証できないスリヴァーを残すため拒否する。この制限を除いた一般の再メッシュ合成は未対応である。

## 対象と宣言

対象は、同じ偏波のCartesian遮断TE/TM、直線P1/P2の明示多角形Case版2である。前後の保存場は同じ物理多角形の相似像で、三角形数・節点番号・対角線・内部節点位置は異なってよい。せん断、異方尺度、鏡映、任意の頂点移動、異なる多角形形状は未対応。

宣言は `x_current = scale × R(rotation_radians) × x_previous + translation_xy_m`。`scale > 0`、`rotation_radians` は rad、`translation_xy_m` は m の二成分。`inverse: true` は同じ宣言を逆方向 `x_current = R(θ)^T (x_previous - t) / scale` に使う。逆係数を別の丸めた値へ展開しない。

幾何の判定は、宣言変換を前の境界節点列へ適用した結果が現在の境界節点列とbinary64で完全一致すること、または宣言変換の厳密な逆評価を現在へ適用した結果が前の境界節点列と完全一致することを要求する。行列積と成分ごとの乗加算の二つの既知の演算順を受理する。頂点から写像を推定・fit しない。境界節点の密度・位置が異なる場合や、丸め差だけで一致する場合は、面積の厳密被覆が未検証となるため拒否する。

`max_candidate_tests` はBVH候補比較（節点比較と葉の比較の両方）の上限、`max_overlay_triangles` は入力要素数と交差分割数の上限である。資源上限は割当て前に検査する。

## 元場の比較

前の三角形を宣言変換したメッシュと現在の三角形を、binary64座標の有理数クリッピングで厳密に共通分割する。両側の各元三角形について、分割面積の総和が元面積と完全一致することを確認する。辺接触・点接触は面積に数えない。元のFEM多項式は元要素のbarycentric座標で評価し、節点平均や再補間で置き換えない。

TEの現在の横電場は `R^T E_current`（`inverse` では `R E_current`）として前の座標枠へ戻し、TMの `Ez` は回転しない。積分は共通分割の物理xy面積で行い、3次と5次の差、Gram行列のPSD・正規化を再計算する。規格化したGramで振幅の違いを扱う。この比較は離散的な二状態の対応であり、連続経路の同一性や物理誤差上界ではない。

相似則（周波数 1/s、G 不変、同一導電率で Q ∝ √s、壁損失 P′ ∝ U′/s^{3/2}）と、縮退部分空間の基底回転は別に検証する。表面場ピーク精度はこの追跡からは保証しない。

## 有限細分空間の診断と縮退

現在・前の各保存場について、多角形面積の逆数をシフトに使う回転不変な有限細分診断を行い、上端のguardモードへ帯域が届く場合は `UNVERIFIED` とする。追跡帯域の上には少なくとも1モード多く計算しておく。縮退群はID集合として運び、個別IDを確定しない。曖昧な対応や不足帯域で `UNVERIFIED` とした結果に採用値を与えない。

## 要求の生成と実行

```python
from pathlib import Path
import json
from superfish_ng.planar_tracking import PlanarTrackingRequest
from superfish_ng.planar_tracking_similarity_remesh import PolygonSimilarityRemeshMapping

mapping = PolygonSimilarityRemeshMapping(
    scale=0.7,
    rotation_radians=0.31,
    translation_xy_m=(0.04, -0.03),
    max_candidate_tests=2000000,
)
request = PlanarTrackingRequest(1, 1, ["fundamental"], mapping=mapping)
Path("tracking.json").write_text(json.dumps(request.to_dict(), indent=2) + "\n")
```

現在側のCaseは、前のメッシュの境界節点列に `mapping` を適用した座標を持つ独立メッシュとして作る。`PolygonSimilarityRemeshMapping.transform_mesh(mesh)` は宣言どおりのメッシュを返し、`_scalar_transform_mesh` は成分演算順の別評価を返す。`polygon_similarity_remesh_overlay` は両方の演算順と厳密な逆評価を受理する。

```sh
python -m superfish_ng execute-planar-tracking previous-native current-native tracking.json --out new-tracking
python -m superfish_ng replay-planar-tracking new-tracking
```

要求JSONの `tracking_version` は5、`mapping.name` は `polygon_similarity_remesh`。写像には `scale`、`rotation_radians`、`translation_xy_m`、`inverse`、`max_candidate_tests` の全項目を保存する。GUIでは「明示多角形：相似変換＋異なる内部メッシュ」を選び、尺度・角度・移動・逆向き・候補上限を入力する。要求の読込/保存、結果ダウンロード、保存ジョブからの復元、元場の取込/表示を同じ版5へ接続している。

## 判定と保存

3次・5次積分、元電場のGram、PSD、正規化、上端guard、有限細分診断、縮退部分空間を再計算する。結果の `physical_mapping` には宣言、`current_to_previous_rotation`、参照面積の説明、境界節点列の厳密一致、内部が独立であることを保存する。

両側の元native、要求、結果を所有コピーとして保存する。保存再生では元FEM場と幾何・対応判定を全再計算し、入力や結果の改変を拒否する。所有履歴では隣接するnative全ファイルの同一性と帯域・ID集合の連続性を要求し、同じ領域を解き直した場を前段の保存場へ黙って置き換えない。

## 受入証拠（2026-09-11）

- 追加8unit（幾何4・積分4、18.244秒）: `tests/test_planar_tracking_similarity_remesh.py`
- 独立解析（右三角形の解析解、P1 16/32・P2 8/16、TE/TM、正逆、16条件、70.0秒）: `out/planar-similarity-remesh-independent-final-20260911`
- 実Chrome 9項目（独立内部メッシュ、逆向き、履歴、要求/結果往復、URL復元、外部HTTP 0、source不変）: `out/browser-planar-similarity-remesh-20260911`
- 標準検証（947件、945合格、2skip、1514.373秒、source 544件不変）: `out/validation-planar-similarity-remesh-final-20260911`

独立解析は、両側の解析固有関数を宣言写像で前の枠へ戻したときの正規化Gramが恒等（最大残差2.221e-16）、FEM側の対応する正規化Gram誤差がP2最終水準で最大1.038e-4、周波数相対誤差がP2最終水準で最大3.335e-4であることを確認した。粗い水準の誤差も保持し、許容差を広げていない。

## 限界

- せん断・鏡映・任意変形・異なる多角形形状は未対応。
- 境界節点列の厳密一致が必要で、境界の分割密度は独立に選べない。内部のみ独立である。
- 二状態の数値対応であり、連続経路のモード同一性、物理誤差上界、表面ピーク収束の保証ではない。
- 一般の多次元写像・曲線断面・親P02全体は継続する。
