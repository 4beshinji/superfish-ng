# 境界・内部メッシュを独立に選ぶ厳密アフィン追跡

P02の残工程として、[厳密共通分割API](PLANAR_EXACT_AFFINE_OVERLAY.md)を
モード追跡要求・結果版7、保存再生、CLI、実worker、GUI、所有履歴へ接続・限定受入した。
写像名は `polygon_exact_affine_remesh`、Python宣言は
`planar_tracking_exact_mapping.PolygonExactAffineRemeshMapping`。
版1〜6の要求・幾何判定・保存再生の意味は保持する。

## 受け入れ条件と先行反例

- 境界分割数の異なるP1/P2・TE/TMメッシュで、元要素の電場を正逆に比較する。
  宣言写像は各元要素の厳密面積被覆を満たすこと。再補間しない。
- 反射・尺度・非二進有理数の逆写像・せん断の移送恒等式、周波数順位交差、
  縮退ID集合と帯域端の未確認判定を別々に検証する。
- 周波数・電場・磁場・G/Q/単位長壁損失を独立解析と比較し、二尺度・実細分で確認する。
  対応のPASSを場/RFの誤差上界と扱わない。
- 全nativeと要求・結果を保存後に再検証し、hashを作り直した改変も拒否する。
  実workerの中止・管理器再起動・取込、CLI、GUI、所有履歴を通す。
- 既存標準unittest、`scripts/validate.py`、seed周波数とRF量の回帰を確認する。

版6は3×3と4×4の独立境界分割を拒否する。幾何APIの先行反例・被覆証明は
[共通分割の記録](PLANAR_EXACT_AFFINE_OVERLAY.md#先行反例と受入条件)を参照。
もう一つの反例は `A=[[1+2^-27,1],[1,1-2^-27]]`。
通常の積 `a*d-b*c` は0に丸まるが、厳密行列式は `-2^-54` で可逆である。
版7の逆向きTE移送係数は、厳密行列式で除算してからbinary64へ変換する。
幾何が有理数でも移送係数が非有限・非零から0・特異へ潰れる場合は、計算前に拒否する。
この反例は一般の悪条件行列でFEM精度が保証されるという意味ではない。

## 入力・場・判定の契約

同じ偏波の平面真空遮断TE/TM、直線P1/P2、単一PECの明示多角形Case版2が対象。
`x_current=A*x_previous+t` を宣言し、`inverse=true` では
`x_current=A^-1*(x_previous-t)` を同じ入力係数から評価する。
入力のbinary64値を正確な有理数として扱い、写像や逆写像の評価途中では丸めない。
並進はm。境界と内部の節点数・接続・要素番号を独立に選べる。
境界の余分な共線節点を除いた角列と各実境界は、宣言した多角形の厳密な像である必要がある。
1 ULPの境界ずれ・丸めた角列も受け付けない。版6の既知演算順で作ったメッシュを
自動的に版7へ読み替えない。非線形変形・曲線・任意の丸めた境界対応は未実装。

積分測度は**正逆とも現在の物理xy面積[m²]**。有効行列を `E` として、TEの現在の
横電場へ `adj(E)=det(E)E^-1` を掛け、TMの縦電場Ezはスカラーのまま比較する。
`inverse=false` の余因子は `[[d,-b],[-c,a]]`、逆宣言では `A/det(A)`。
これは宣言した場の対応であり、一般せん断に共通の固有周波数則を仮定しない。
元要素番号と重心座標の列順は反射でも保持し、元FEM係数・位相・規格化を変えない。

自己/相互Gramを3次・5次積分で検査し、既存の部分空間割当へ渡す。
各側の面積からシフトを決める有限細分空間診断と上側guardを使う。
追跡数より少なくとも1つ多くモードを計算する。縮退した個別IDは確定せず集合として運び、
帯域端に診断群がかかる場合は `UNVERIFIED` にする。未確認の履歴へ段階を追加しない。
これらは有限個の保存場の対応であり、連続した変形経路の同一性・連続スペクトルの
誤差上界・表面ピーク精度を保証しない。単位長RF、R/QのN/A、SI・peak phasorは保持する。

`max_candidate_tests` はBVHの木/葉の候補比較予算、`max_overlay_triangles` は入力/生成三角形の上限、
`max_refined_triangles` は各側の診断細分の上限。上限や領域不一致は投入前に拒否する。

## 利用と保存

```python
from superfish_ng.planar_tracking import PlanarTrackingRequest
from superfish_ng.planar_tracking_exact_mapping import PolygonExactAffineRemeshMapping

mapping = PolygonExactAffineRemeshMapping(
    linear_xy=[[-1.0, 0.0], [0.0, 1.0]],
    translation_xy_m=(0.0, 0.0),
)
request = PlanarTrackingRequest(1, 1, ["fundamental"], mapping=mapping)
request.save("tracking-exact.json")  # 新規ファイル
```

前の矩形 `[0,.5]×[0,.25]` と、現在の反射矩形 `[-.5,0]×[0,.25]` を例にすると、
両側の境界分割数・内部対角線を別々に選べる。それぞれ独立にFEMで解いてnative保存してから実行する。

```sh
python -m superfish_ng execute-planar-tracking previous-native current-native tracking-exact.json --out new-tracking
python -m superfish_ng replay-planar-tracking new-tracking
```

要求には行列・移動量・逆方向・候補予算をすべて保存する。結果にはその宣言、
実際の場移送行列、元の厳密行列式と有効行列式の有理数字列、積分測度、向き、
両Gram、診断、IDを記録する。保存readerは双方の全nativeを再検証し、対応結果全体を再計算する。
manifestのhashだけを信用せず、積分測度・移送係数・行列式・結果版の改変も拒否する。

GUIの「形状の対応」で「明示多角形：厳密アフィン変換＋境界・内部の独立メッシュ」を選ぶ。
行列・移動・逆方向・予算は保存要求、結果選択、URLから復元できる。
保存した追跡結果を所有履歴へ追加し、次段階へID集合を引き継げる。

## 再現

```sh
python -m unittest discover -s tests -p test_planar_tracking_exact_mapping.py -v
OPENBLAS_NUM_THREADS=1 python scripts/validate_planar_exact_affine_overlay.py --tracking --out out/exact-tracking-new
OPENBLAS_NUM_THREADS=1 python scripts/validate.py --out out/validation-exact-tracking-new
python -m superfish_ng gui --workspace out/exact-tracking-gui-new --no-browser
# 起動表示のURLを使い、別ターミナルから実行
node scripts/verify_gui_planar_affine_remesh_tracking.mjs --url LAUNCH_URL --out out/exact-tracking-browser-new --mapping-contract exact
```

`--tracking` を付けない独立検証器と `--mapping-contract rounded` のブラウザー検証は、
従来の幾何API・版6を引き続き検証する。

## 検証記録

主ツリーの追加9unitは83.359秒で合格。独立検証は16条件・32実FEM/32native保存再読込、
正逆32対応が1088.988秒で合格した。TE/TM・P1/P2・二尺度、
元16→32/現在24→48の独立境界分割を検証し、全解析誤差の細分改善を必須にした。
全対応の最小内積は0.9980373303、3次/5次Gramの最大正規化差は7.566e-15。
二尺度のf/G/Q/単位長損失/規格化相似則の最大差は5.029e-14。

最終水準の解析誤差の最大値（両側・両尺度・両偏波、無次元）：

| 量 | P1 | P2 |
|---|---:|---:|
| 周波数 | 1.205e-03 | 4.506e-07 |
| 電場相対L2 | 2.833e-02 | 3.583e-04 |
| 磁場相対L2 | 4.907e-02 | 9.495e-04 |
| G | 3.622e-03 | 2.394e-03 |
| Q | 3.018e-03 | 2.395e-03 |
| 単位長壁損失 | 1.808e-03 | 2.401e-03 |
| 正規化Gramの解析恒等との差 | 4.908e-04 | 7.531e-08 |

これらは本工程の限定対照であり、一般形状の精度保証ではない。閾値は幾何APIの検証器から維持した。
粗いP2 TMのG誤差約0.94%・磁場L2約0.38%は最終ゲートを超えるため、周波数/Gramだけで受け入れず、
指定した細分後の結果で判定した。

実Chromeは新版10操作と旧版6の9操作で合格。新版の6×6/8×8境界分割、反射せん断、
行列/移動/逆方向/予算の保存復元、結果保存、元場の取込/表示、正逆追跡・所有履歴を確認した。
外部HTTPは0、実行中の製品ソース変更なし。管理器を閉じて再開し、両版を含む保存14ジョブを完全再検証した。
旧版1〜6の保存結果も全文再生に一致した。版6は変更前のa7fbd20で保存した結果を別途作り、
版7導入後のreaderで照合した。旧保存ファイルは不変。追加単体では実workerの中止/再起動・CLI往復も確認した。

最終標準は973件（971合格・2skip、1577.700秒）で合格。
`OPENBLAS_NUM_THREADS=1 python scripts/validate.py` の収束計算とseed9モード19量も合格。
周波数相対差は0e+00、全19量の最大相対差は8.882e-16。既存ベンチマークは更新していない。
既存の `.manager.lock` のResourceWarningは最終標準でも観測し、未解決として保持する。

独立計算は初期標準テストのソース変更を避けるため一時コピーで開始した。
その開始/終了の553 sourceは一致した。主ツリーとの差はGUIの説明/非適用欄、テスト・ブラウザー検証、
幾何APIのmodule docstringの5ファイルだけで、数値実装と独立検証器は同一。
幾何モジュールはdocstringを除いたASTの一致も確認した。主ツリーでは修正した9unit・Chrome両版・
全標準を実行し、固定553 sourceと標準終了時の一致を確認した。
詳細は `out/planar-exact-affine-tracking-20260912/independent-source-comparison.json`。

全証拠は `out/planar-exact-affine-tracking-20260912`、標準とseed照合は
`out/validation-planar-exact-affine-tracking-20260912`。
環境はPython 3.12.3、NumPy 2.5.2、SciPy 1.18.1。
時間は複数検証を並行した局所観測であり、一般性能の受入には用いない。

初回のBLAS未固定の全体テストは、RF探索の1検査が長時間継続した時点でSIGINT終了した。
数値コードは変更前のままで、`baseline-interrupted.log` にKeyboardInterruptを保存した。
この実行を全標準合格には数えず、BLASを1スレッドに固定した上記の最終標準で検証した。
未固定環境の性能・再現性を切り分けたことにはしない。

開発時の失敗を保持する。新規テストの初回は履歴モジュールのimport名誤りで起動失敗。
修正後8件のうち、順位交差例が帯域端の縮退を含み1件FAILとなった。
矩形の縦横比2ではTEのx方向2次とy方向基本が縮退するため、`UNVERIFIED` が正しい。
単独モードの交差例を `.375×.25` から `.28125×.375` へ変更し、別テストで縮退/帯域端拒否を維持した。
閾値や製品の縮退判定は変更していない。
