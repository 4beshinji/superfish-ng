# 平面多角形の相似写像による電場追跡

同じ領域で番号・分割が異なるメッシュの比較には[独立再メッシュ版4](PLANAR_REMESH_TRACKING.md)を使える。相似変換との合成は未対応。

明示メッシュの平面 TE/TM（真空・閉 PEC・β=0、P1/P2）について、正の一様尺度、平面回転、SI 平行移動を宣言した二つの保存スペクトルを比較する。要求・結果は版3。保存履歴、CLI、ローカル worker、平面 GUI に接続している。以下の限定条件で受入検証を完了した。

## 座標と電場

宣言する順方向は `x_current = s R(θ) x_previous + t`。`s > 0`、θ は rad、t は m の二成分。`inverse: true` は同じ宣言を逆方向に使い、`x_current = R(θ)^T (x_previous - t) / s` とする。逆係数を別の丸めた尺度・角度・移動へ展開する必要はない。

TE の現在の横電場は順方向で `R^T E_current`、逆方向で `R E_current` として前の座標枠へ戻す。TM の縦電場 Ez は回転しない。元の FEM 係数と元要素の多項式から両場を評価し、前の物理面積上で積分する。保存場や固有値を書き換えない。規格化した Gram 行列で振幅の違いを扱うため、U′の異なる計算も比較できる。

同じ次数・相似なメッシュ・一様尺度 s で、周波数は 1/s、G は不変、同じ壁導電率で Q は √s、壁損失 P′は U′/s^(3/2) に従う。これらの離散的な相似則と、解析解への周波数・電場誤差は別に検証する。表面場のピーク精度はこの追跡からは保証しない。

## 幾何と入力の契約

両側を明示多角形 Case とし、同じ偏波、宣言した元頂点番号・接続・既知四分割を要求する。`previous_refinements` と `current_refinements` は 0〜8 の整数で、同時に正にはできない。後者が1なら現在側が前側より一段細かい。逆向きへ進む際は、細かい側の指定も実際の前後に合わせる。三角形数の予算を割当て前に検査する。

座標の誤差許容値は各点に接続する最短辺の16機械イプシロンを上限とする。外周では隣接外周辺を使う。大きな原点座標に比例させない。回転で座標が零付近となっても同じ局所尺度を使う。

行列積と成分ごとの乗加算、変換してから四分割する場合と四分割してから変換する場合には、浮動小数点の演算順の差がある。局所比較を超えた場合は、これらの既知の構築式またはその逆照合で全点・外周・接続が完全一致したものだけを追加受理する。頂点から写像を推定したり fit したりしない。一般の形状差を吸収する絶対許容値も使わない。

未知項目、非有限数、負または零の尺度、誤った細分回数、異接続・異偏波を拒否する。せん断、異方尺度、鏡映は[可逆アフィン合成追跡](PLANAR_AFFINE_REMESH_TRACKING.md)（要求/結果版6）で対応。非線形変形、独立した任意メッシュ間の境界密度独立追跡は未対応。

## 要求の生成と実行

Python API で厳密な要求全体を生成できる。比較する native スペクトルには、追跡帯域の上端を検証する追加モードも必要。

```python
from pathlib import Path
import json
from superfish_ng.planar_tracking import PlanarTrackingRequest
from superfish_ng.planar_tracking_similarity import PolygonSimilarityMapping

mapping = PolygonSimilarityMapping(
    scale=0.37,
    rotation_radians=0.371,
    translation_xy_m=(0.13, -0.08),
    current_refinements=1,
)
request = PlanarTrackingRequest(
    1, 1, ["fundamental"], mapping=mapping,
)
Path("tracking.json").write_text(json.dumps(request.to_dict(), indent=2) + "\n")
```

写像オブジェクトの `transform_mesh(mesh)` は宣言どおりの新しい明示メッシュを作る。計算はその新メッシュを使って別途 FEM で実行する。

```sh
python -m superfish_ng execute-planar-tracking previous-native current-native tracking.json --out new-tracking
python -m superfish_ng replay-planar-tracking new-tracking
```

要求 JSON の `tracking_version` は3、`mapping.name` は `polygon_similarity`。写像には `scale`、`rotation_radians`、`translation_xy_m`、`inverse`、`previous_refinements`、`current_refinements` の全項目を保存する。版1の矩形写像、版2の原点尺度写像の形式と再生結果は保持する。

平面 GUI の追跡写像から相似写像を選び、尺度、角度 rad、移動 x/y m、逆向き、細分回数を入力する。要求の読込・ダウンロードと保存ジョブの復元で同じ宣言を保持する。履歴から次の変換は推測せず、次の二つのスペクトルに対応する要求を明示する。

## 判定と保存

3次・5次積分、元電場の Gram 行列、PSD、正規化、上端 guard、有限細分空間の近傍スペクトル診断、縮退部分空間を再計算する。版3の診断シフトは多角形面積の逆数を用い、回転に依存する bounding box の辺長を使わない。旧版1/2の計算方法はそのまま維持する。この診断は離散化誤差の上界ではない。

縮退群は ID 集合を運び、個別 ID を確定しない。不足帯域や曖昧な対応は `UNVERIFIED` とする。離れた二状態での合格は、その間の連続経路全体の同一性の証明ではない。

保存時は両 native と要求・結果を所有コピーとし、全保存場と対応判定を再生する。[保存履歴](PLANAR_TRACKING_HISTORY.md)では、各段階の完全再生、隣接 native のバイト同一性、帯域と ID 集合の連続性を維持する。変更された入力・結果・祖先を受理しない。旧版の追跡を含む履歴も同じ規則で読む。

実装前の反例と演算順による失敗の記録は[計画書](PLANAR_SIMILARITY_TRACKING_PLAN.md)に保持する。新しい外部ソース・依存は使用していない。

## 受入証拠（2026-09-10）

明示多角形の正の尺度・回転・SI平行移動による追跡を限定受入。要求/結果版3、正逆の元電場積分、完全保存再生・CLI/実worker/GUI・所有履歴を接続した。標準932件（930合格、2skip、1447.175秒）、追加9unit、独立64 FEM/128対応、解析32条件、縮退16 FEM、実追跡32/履歴16worker、中止/再起動、Chrome87操作とGUI56保存ジョブを確認。旧版追跡・22履歴・TM/TE/平面数値回帰と535sourceも合格。独立内部メッシュとの合成は[合成追跡版5](PLANAR_SIMILARITY_REMESH_TRACKING.md)として、可逆アフィン（せん断・異方尺度・鏡映）は[合成追跡版6](PLANAR_AFFINE_REMESH_TRACKING.md)として限定受入済み。非線形変形・境界密度独立の合成・親P02と全計画は未完。

- 標準・535source・TM seed9モード19量: `out/validation-planar-similarity-final-20260910`
- 64 FEM・正逆128対応: `out/planar-similarity-final-independent-20260910`
- 解析三角形32条件: `out/planar-similarity-final-analytic-20260910`
- 縮退8条件16 FEM・基底回転とguard: `out/planar-similarity-final-subspaces-20260910`
- 実追跡32・履歴16worker、中止2件・再起動・CLI・改変拒否: `out/planar-similarity-final-workflow-20260910`
- CLIで版3履歴の作成・追加・全再生: `out/planar-similarity-final-cli-history-20260910`
- 新64 native・元8 nativeの全再生とhash: `out/planar-similarity-final-native-replay-20260910`
- Chrome78項目: `out/planar-similarity-final-browser-20260910`
- 再起動Chrome9項目: `out/browser-planar-similarity-final-restarted-20260910`
- GUI保存場・ダウンロード・再取込の照合: `out/planar-similarity-final-gui-persistence-20260910`
- 旧版22履歴の全再生: `out/planar-similarity-final-history-regression-20260910`
- 旧native/矩形/Study/細分/追跡保存の回帰: `out/planar-similarity-final-regressions-20260910`

細分P2の三角形解析比較は周波数相対誤差最大2.657e-5、電場相対誤差最大0.001425。粗メッシュのゲート未達も保持する。既存TM seedの周波数差は0、RF相対差最大8.882e-16。ベンチマークの数値と許容差は変更していない。ローカル検証であり、hosted CIを実行したとの主張ではない。

標準終了時に既存の一時workspaceの`.manager.lock`解放に関する`ResourceWarning`が再度出た。テスト失敗はなく、受入済み前段でも見られた未解決の資源解放警告として記録する。今回の相似写像で修正したとは扱わない。
