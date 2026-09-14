# RF制約付き2変数探索 — D03

[要求版2の固定局所履歴](RF_OPTIMIZATION_HISTORY.md)を追加。
固定済みProjectの履歴末尾に全域細分を加え、CLI/worker/GUIと表面評価版2へ接続する。
以下の「履歴なし」は要求版1の契約。版1の入力・保存再生は維持する。

[実行内の祖先再利用](RF_OPTIMIZATION_REUSE.md)を追加。再開の完全再検証を保ち、同じ実行内の重複評価を削減する。

[JobManagerでの実行・中止・再起動・checkpoint再開](RF_OPTIMIZATION_JOBS.md)を接続。[GUI操作](GUI_RF_OPTIMIZATION.md)も接続済み。

曲線Projectのradial_scale/axial_scaleを有限範囲で探索し、各候補を実FEMと
[RF設計評価](RF_DESIGN_CRITERIA.md)で検証する。探索に解析式や補間したRFを使用しない。
元のProjectから毎回変形し、親候補との相対写像から保存個別IDを追跡する。

## 探索と停止

変数の宣言順に正・負方向を試す。範囲外は境界へ切り詰め、既に評価した座標は再評価しない。
改善候補を採用したらその候補を中心として方向を最初に戻す。全方向で改善しなければ
stepを半分（toleranceまで）に減らす。両stepがtoleranceまで到達した全方向の試行を
終えればPARAMETER_LIMIT。最後の確認を除く予算を使えばTRIAL_LIMIT。
どちらも連続設計空間の停留点・局所/大域最適性を証明しない。

各候補は元の二次幾何の3水準を独立に解く。最後の候補は元の開始段数+1/+2/+3の
3水準を新規計算する。max_trialsは初期と最終確認を含み、最大FEM呼出しは
3*max_trials。途中保存による再開では既完了の試行も数える。失敗は例外とfailure文書を
残して停止し、有利な評価へ変換しない。失敗前のcheckpointから別に開始する操作は
別の分岐であり、分岐をまたぐ利用者全体の計算予算の管理はない。

制約違反の改善には、各観測包絡が制約からはみ出す最大距離を使う。
constraint_scalesで量ごとの単位付き正の基準値を明示し、正規化した違反量の最大値を
最小化する。重み付き和ではない。未収束・個別追跡未確認・必要区間欠落の候補は
採用しない。違反量が0になった後だけ、目的関数の保守的採用値について
objective_improvementを超える改善を採用する。単位は目的関数の単位。

SEARCH_COMPLETEは最終細分で設計条件を満たした探索の終了を示す。
FINAL_UNVERIFIED/FINAL_CRITERIA_FAILEDは最終確認の未確認/条件未達を示し、
探索中の粗い候補が合格していても成功としない。初期/最終の評価と採用値を保存する。
観測した3水準の包絡や細分差を物理誤差上界として扱わない。

## 版1の入力

必須項目はschema_version=1、project、variables、criteria、constraint_scales、
objective_improvement、max_trials、initial_ids、mode_id、controls、rf_coordinates。
variablesはname/lower/upper/initial/step/toleranceを持つ2要素配列で、
名前はradial_scaleとaxial_scale。いずれも無次元で正・有限、初期値は範囲内。
stepとtoleranceは正でtolerance<=step。criteriaはRF設計評価の版1。
constraint_scalesは全制約のquantityと一対一に対応する。

controlsは既存affine_remeshの追跡条件だがaffine_mapは指定しない。
試行間の実写像を導出する。各細分ではcurved_same_domainへ切り替える。
全周波数順位の個別ID確認を必要とし、クラスタを単一モード扱いしない。
rf_coordinatesはfixed/axialで明示する。

対象は全体の閉PEC・native曲線P2、未組立・未鏡映・局所細分履歴なしのProject。
元の一様細分段数と明示元メッシュは利用できる。一般形状変数・せん断・局所細分履歴・
半領域・追加物理への拡張、一般性能の受入は残る。局所履歴は上記版2で対応する。
既存の物理・幾何・RF収束条件を緩和していない。

## 実行と保存再開

```sh
python -m superfish_ng optimize-rf examples/optimization/curved_rf.json --out out/optimization-new --max-new-trials 1
python -m superfish_ng replay-rf-optimization out/optimization-new/checkpoint-001.json
python -m superfish_ng resume-rf-optimization out/optimization-new/checkpoint-001.json --out out/optimization-resumed
```

Pythonは`rf_optimization.execute_rf_optimization(request, new_directory, checkpoint=None,
max_new_trials=None)`、`read_rf_optimization(path)`、`replay_rf_optimization(document)`。
新規ディレクトリのみへ書き、1試行（3解）の完了ごとにcheckpointを保存する。
全試行のnative Job入力・保存場・ハッシュ・個別追跡・RF評価・探索順序・判定を
再構築して照合する。途中の未完了試行の再開はなく、失敗前の保存地点は別分岐の起点。
終了済み文書の再開や、改変されたrequest/座標/判定/場は拒否する。
CLI終了値0はPAUSEDまたはSEARCH_COMPLETE、未確認/条件未達は1。

例題は合成球形からの2変数探索で、実機構造ではない。周波数最小化とRQ/電場比の
制約を指定し、4試行（最終確認を含む）まで。探索後の両倍率が同じ球形は解析周波数
と対照できるが、製品は例題名や解析式による分岐を持たない。

版1ではcurved_refinement_steps配列による履歴（一様だけの配列を含む）は受理しない。
curved_refinement_levelsによる元の一様段数を使用する。形状輸送/評価器の履歴契約を
拡張してから対応する。

## 検証証拠 — 2026-09-09

基準f976091。既存RF設計5件は21.537秒でPASS。追加4件377.610秒では実FEM9解の
pause/resume・段数1/2/3の最終確認・保存改変/終端再開拒否、2変数試行順序、
予約された最終試行、未確認候補の採用拒否、違反量の単位不変性を確認。
失敗注入の追加1件0.133秒では失敗文書と試行回数を記録し、checkpointを作らない。

`out/rf-optimization-independent-20260909` は終了0。新規球形実FEMを使う両尺度の
4試行、各12解。変数は[1,1]→[1.01,1]→[1.01,1.01]→同値の最終確認。
探索中0/1/2、最終1/2/3の独立solveを保存。CLI実行/途中保存/再開/replayと
最終文書のAPI再検証がPASS。終了理由TRIAL_LIMITを保持し、最適性と呼ばない。
最終球形解析fの相対差は両尺度とも2.472e-5、観測RF包絡のMaxwell相似差は
最大4.930e-14。422対象ソースは実行中不変。JobManager/GUIの新規検証はない。

追加の`restoration-validation.json`は終了0。保存済みの同じ実FEM試行へ元球形の解析
f/1.005を上限制約として追加し、両尺度で初期CONSTRAINTS_VIOLATED（採用値null）から
最終SEARCH_COMPLETEへ進む同じ試行列を再構築・公開replayで照合した。
この追加対照は保存場の再利用で、新しいFEM実行とは扱わない。
最終球形の独立解析相対差はf最大2.472e-5、RQ 2.525e-6、G 1.077e-7、
E比2.314e-4、B比6.077e-6で既存の独立許容差を満たす。

標準`out/validation-rf-optimization-20260909`は終了0、734件中732合格・2skip、
unittest 991.980秒。seed9モード19量f差0/RF差最大8.882e-16。
標準/独立/追加再評価/終了後422対象hashが一致。driverと全ログをoutへ保存。
全関連実行終了、ソース固定解除。D03は部分受入、親全体と全体計画は未完了。
親集計8受入・8進行中・16他未受入・1候補、計33を維持する。
