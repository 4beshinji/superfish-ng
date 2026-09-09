# 明示多角形の一様尺度によるモード追跡

[受入計画と反例記録](PLANAR_POLYGON_TRACKING_PLAN.md)に基づいて実装した。
最終標準検査・保存照合まで限定受入。親P02と全計画の完了ではない。

対象は真空・単一PECの明示多角形Case版2、Cartesian遮断問題、同偏波のTE/TM。
P1/P2と異なる次数、同一接続または宣言した四分割関係を比較する。
この版2では次の座標を前の座標の正の一様尺度倍とする。平行移動・回転・縦横別尺度・
任意形状変形・任意の番号振替・穴・曲線・材料・伝搬は受け付けない。

回転・平行移動を含む別の要求版3は[相似写像追跡](PLANAR_SIMILARITY_TRACKING.md)を参照。版2の契約を変更するものではない。

## 明示写像と幾何の検証

`PolygonScaleMapping(scale, previous_refinements=0, current_refinements=0)` を用いる。
片側だけが他方より細分されている関係を宣言し、最大8段、共通三角形数は既定250000。
頂点と三角形の数を先に確認し、境界・元頂点・接続・四分割の番号を検証する。
単なる同じ接続を幾何一致の根拠にしない。

尺度変換と中点生成の丸めは、座標成分の大きさと接する最短辺の小さい方の
16機械イプシロン以内に制限する。遠方の小形状で大きな座標値が別形状を隠さないためである。
ゼロ成分には絶対許容差を追加しない。
尺度と細分の順序が異なる場合には、別の演算順から生成した境界・頂点・接続の
完全一致でも関係を検証する。任意座標へのフィットや許容差拡大は行わない。

共通積分領域は前の物理xy領域。両側の元要素番号と重心座標を用い、
元P1/P2多項式と実固有周波数から全電場を評価する。表示補間は使用しない。
自己/相互GramをGauss次数3と5で比較する。矩形版1の単位正方形面積とは
測度が異なり、版2の結果に `previous physical xy area in m^2` と明記する。
規格化された対応には定数面積因子が影響しない。

## 判定と限界

[矩形追跡](PLANAR_TRACKING.md)と同じ一対一割当・競合差・部分空間の主角を用いる。
対象は正固有値の先頭からの帯域とし、上位guardを少なくとも1モード計算しておく。
同じ多角形を四分割した有限FEM空間でシフト逆残差を計算し、
離散分裂による近接群とguardとの重なりを診断する。
この診断は有限空間の近傍固有値に限り、連続スペクトルや真の誤差の上界、
順位隔離、浮動小数点の厳密包囲を証明しない。

縮退は個別ベクトルに名前を付けず、ID集合と部分空間の対応を保存する。
単一対応は元の場への位相符号を保存し、部分空間の個別位相はnull。
guardに達する群や曖昧な対応はUNVERIFIEDで、個別IDを確定しない。
PASSでも集合内の個別IDが未確定の場合がある。
真の周波数・電場精度、連続表面ピーク精度、連続変形経路の同一性とは別の判定である。

## 要求・保存・操作

矩形の要求版1と結果版1はそのまま再生する。多角形は同じformatの版2に限る。
要求のmappingは次のオブジェクトで指定する。

```json
{
  "name": "polygon_uniform_scale",
  "scale": 2.0,
  "previous_refinements": 0,
  "current_refinements": 1
}
```

これは次の領域が前の2倍で、次側の三角形が1回四分割されている場合。
要求文書全体にはformat `superfish_ng_planar_tracking_request`、tracking_version 2、
両側の対象数、元IDまたはID集合、全controlsも必要。GUIの要求保存で完全な文書を作成できる。
APIは既存 `PlanarTrackingRequest` のmappingに `PolygonScaleMapping` を指定する。

```sh
superfish-ng execute-planar-tracking PREVIOUS CURRENT request.json --out out/NEW
superfish-ng replay-planar-tracking out/NEW
```

保存は両側のnativeを全コピーし、全体再生で要求・写像・電場積分・細分診断・対応を再計算する。
未知キー、版の混在、異偏波/Case種別、未対応幾何、保存結果の改変を拒否する。
管理workerの中止・再起動とCLIの経路は矩形と共有する。

平面GUIで「明示多角形：原点まわりの一様尺度」を選び、元の保存場と写像を明示する。
Studyの点や細分診断の水準から保存場を取り込める。
完全条件・全結果の保存、コピー場の取込と表示、URL復元に対応する。
ID集合の引継ぎは各2スナップショット間の検証であり、履歴全体の連鎖を保証する文書ではない。

## 検証結果の所在

- 関連28unitは30.324秒で合格。追加は幾何5・接続4の9検査。
- `out/polygon-tracking-final-correspondence-20260910`：三角形/凹形状、P1/P2、TE/TM、尺度0.37/2、細分0/1の32対応と完全保存再生が合格。
- `out/polygon-tracking-final-analytic-20260910`：保存三角形16条件を独立sin/cos電場と周波数で照合。細分P2の4条件はf相対1e-4・E相対1%の両条件に合格し、粗いP1等の精度未達を別に保持。
- `out/polygon-tracking-final-subspaces-20260910`：8比較16FEMの正方形縮退。任意基底回転による主角不変と帯域切断のUNVERIFIEDが合格。
- `out/polygon-tracking-final-workflow-20260910`：16実worker、両側コピー、実行中中止、管理再起動、CLI実行/再生が合格。
- `out/polygon-tracking-final-gui-independent-20260910`：GUI保存のStudy2点・細分3水準を別の5FEMと照合し、周波数・元係数・RF・コピー・要求/結果download一致を確認。
- Chromeは新多角形6・旧矩形追跡8・細分7・Study8・平面13・軸対称10・再起動6の計58操作が合格。外部HTTPなし。
- `out/polygon-tracking-final-{native,rectangle,study,convergence}-regression-20260910`：旧平面32件/TE10件、矩形追跡11件と取込6件、Study29件61点、細分18件54水準の完全再生が合格。

初期の40FEM nativeはそのまま保持し、最終対応と独立解析ではその元保存係数を再検証して使用した。
最終標準は `out/validation-polygon-tracking-order-fixed-final-20260910` で908件（906合格・2skip、unittest1320.887秒）とconvergenceが終了0。
最終保存再読込は22追跡/44nativeと取込10件で合格。全527sourceの総合照合とTM seed9モード19量の比較も合格した。詳細は同outの `seed_regression.json`。
失敗反例と二つの中止した標準検査は受入計画に記録し、合格値で上書きしていない。
新規外部資料・依存・legacy参照はない。

TM seedの周波数相対差最大は0、RF量の相対差最大は8.882e-16。ベンチマークや許容差を変更していない。
標準末尾の既存 `.manager.lock` 未close ResourceWarningは未解決として保持する。
