# 矩形平面RFの電場によるモード追跡

[受入計画](PLANAR_TRACKING_PLAN.md)の最初の対象を実装した。
真空、閉じた単一PEC、Cartesian遮断問題の矩形Case版1、TE同士またはTM同士、
P1/P2が対象。異なる格子数・次数・幅・高さ・単位長規格化を比較できる。
一般多角形Case版2は、矩形に見える入力でも未対応として拒否する。
親P02と全計画の完了ではない。

## 写像と元の物理場

`normalized_rectangle` を明示し、両側を `(x,y)=(aρ,bη)` で単位正方形へ写す。
物理xy成分の電場を合成して参照面積 `dρ dη` で積分する。
座標変換に伴う別のベクトル変換や表示補間は行わない。
TEは実固有周波数から得たEx/Eyの直交位相、TMはEzの実位相を用いる。
同偏波の全電場について他成分がゼロとなる契約を維持する。

異なる構造格子の元三角形を有理数座標で交差分割する。
各交差三角形の親要素重心座標で元P1/P2多項式を評価し、
両側自己Gramと相互GramをGauss次数3と5で比較する。
正方形全体への一括Gauss積分は要素境界の区分多項式を積分できず、
先行反例で電気エネルギーが28.3664%ずれた。この方法は採用しない。
共通分割の面積・四次までのモーメント・自己電気エネルギーを別途検査した。
交差三角形と細分三角形の予算は各250000が既定で、超過時は拒否する。

Gramから規格化された特徴を構成し、既存の一対一割当と部分空間の主角を使う。
単一対応には元の場に掛ける位相符号を保存する。部分空間では個別位相はnull。
順位は1始まりであり、IDのラベルとは区別する。

## 離散分裂と帯域端

両側とも最初の正固有値からの連続した帯域を選ぶ。
帯域外の上位guardを少なくとも1モード計算済みにする。
固定周波数間隔だけでは、正方形TM12/TM21の粗いP1離散分裂を見逃すため、
同形状四分割空間への元係数の移送を併用する。

細分行列について `T=(K+sM)⁻¹M`、`s=1/max(a,b)²`、
`μ=1/(λ+s)` とし、`δ=‖Tu−μu‖M/‖u‖M` を計算する。
厳密算術ではTの少なくとも一つの固有値までの距離はδ以下となる。
数値計算では相対1e-10の丸め余裕と線形方程式の残差も別に記録し、
周波数へ戻した近傍範囲の重なり、または既定相対間隔0.001で隣接順位をまとめる。
これは有限の細分空間の診断であり、浮動小数点の厳密包囲、順位の隔離、
連続スペクトルや真の離散化誤差の上界を証明しない。
細分固有ベクトルや解析周波数で保存モードを置き換えることもない。

まとまりが帯域端のguardに達する場合、積分が安定しない場合、対応や競合差が
足りない場合はUNVERIFIEDとなる。個別IDは未確定のままにする。
縮退時はID集合と部分空間の一致を保存し、その後に固有値が分離しても
集合内部の個別IDを自動復元しない。PASSでも `individual_ids_complete=false`
になり得る。PASSは宣言写像上の数値的対応であり、連続変形経路の同一性、
周波数・場の物理精度、連続表面ピーク精度の保証ではない。

## 入出力と操作

APIは `planar_tracking.PlanarTrackingRequest`、`track_planar_modes`、
`planar_tracking_jobs.execute_planar_tracking` / `read_planar_tracking`。
`JobManager.start_planar_tracking` は専用kind `planar_tracking` の実workerを起動する。

```sh
superfish-ng execute-planar-tracking PREVIOUS CURRENT request.json --out out/NEW
superfish-ng replay-planar-tracking out/NEW
```

PREVIOUS/CURRENTは直接nativeまたは検証済み管理ジョブ。
要求文書はformat `superfish_ng_planar_tracking_request`、tracking_version 1。
`mapping`、両側の `*_mode_count`、`previous_mode_ids` または
`previous_identity_groups`、全controlsを必須とし、未知キーを拒否する。
ID集合は `{"indices":[1,2],"ids":["a","b"]}` の形で元帯域全体を分割する。
二つの指定方法を混在させない。GUIの条件保存から完全な要求文書を作成できる。

出力には要求、元情報、両側各5ファイルのnativeコピー、写像・全Gram・
細分診断・対応・未達理由、manifestとjob状態を保存する。
再生はコピーから物理場と結果全体を再計算し、外部の元パスを必要としない。
元データのコピー途中変更、投入後変更、完了中変更、kind変更、
結果のhashを付け直した改変、worker再投入を検出する。

平面GUIでStudyの点などを取込み、「前」「次」に明示選択して追跡する。
条件の保存/読込、結果の保存、両側保存場の取込と表示、再起動後のURL復元に対応する。
「次の追跡へID集合を引き継ぐ」は前のcurrentコピーを取込み、集合を次の要求へ渡す。
各ジョブは二つのスナップショットの検証であり、全履歴の来歴連鎖を証明する文書ではない。
軸対称GUIの追跡候補に平面ジョブを混ぜない。

## 検証記録

基準コミットは4045ac1。標準899件（897合格・2skip、unittest1302.292秒）、convergence終了0。最終照合は `out/validation-planar-tracking-final-20260910/seed_regression.json`。source523件と製品hashの一致、早期二報告の検証scriptだけの差を確認した。標準末尾の既存 `.manager.lock` 未close ResourceWarningは未解決として残る。

- 追加20unit：交差分割・エネルギー・細分逆残差・位相・順位交差・縮退・guard・厳密入力・改変・実worker/中止・CLI・GUI。
- `out/planar-tracking-independent-20260910`：TE/TM、P1/P2、二尺度の8比較16FEM。解析sin/cosによる周波数と元電場の精度を別判定し、実順位交差を確認。P1の周波数未達は残し、対応PASSを精度PASSと読み替えない。
- `out/planar-tracking-special-20260910`：正方形8比較と帯域退出、18FEM。部分空間の任意基底回転で主角が不変であり、帯域退出がUNVERIFIED。
- `out/planar-tracking-workflow-20260910`：規格化1/3、独立格子の8実worker・16FEM、コピー、実行中中止、管理再起動。
- `out/planar-tracking-gui-independent-fixed-20260910`：GUI Studyの3保存を独立3FEMと照合し、正方形の対象帯域は部分空間で比較。3追跡の全再生、ダウンロード一致、コピーとID集合引継ぎを確認。
- Chrome新規8操作・旧細分7・旧Study8・旧平面13・旧軸対称10・再起動5の計51操作。全て製品hash不変、外部HTTPなし。`out/browser-planar-tracking-fixed-20260910`、`out/browser-*-regression-tracking-20260910`、`out/browser-planar-tracking-restarted-20260910`。
- `out/planar-tracking-persistence-20260910`：11追跡、コピー22スペクトル、GUI取込6件の完全再生とhash不変。
- `out/planar-tracking-{study,convergence}-regression-20260910`：過去29Study/61点と取込4件、18細分診断/54水準と取込2件を完全再生。
- `out/planar-tracking-native-regression-20260910`：旧平面32件・TE10件。TM seed9モード19量のf差0、RF相対差最大8.882e-16。基準値と許容差の更新はない。

初期19unitは状態更新時のinput hash未保持で失敗し、running/complete双方に保持する修正後に全件合格。
初回Chromeは非同期の候補更新後のスクロールを待たない検証側の競合で失敗した。
候補selectの値を待つ修正後は合格。独立・特殊形状の報告に対して、この検証scriptのhashだけが異なる。
製品srcは固定のままで、科学計算の再実行による証拠の置換は行わない。
GUI独立照合の初稿は報告キー名を誤ってKeyErrorとなり、保存形式に合わせた修正版を別outへ保持する。
新規外部資料・依存・legacyコードの参照や実行はない。
