# 追跡付き1変数周波数調整 — D02初期実装

2026-09-08。真空・閉PEC・軸接続m=0 TMの実FEM計算を用いる。
`TUNED`は指定された二つの周波数検査を満たしたことを表し、離散化誤差上界や
連続経路全体のモード同一性の証明ではない。D02親課題全体は未受入。

## 実行

```bash
OPENBLAS_NUM_THREADS=1 python -m superfish_ng tune examples/tuning/pillbox_length.json --out out/tune-new --max-new-trials 2
python -m superfish_ng replay-tune out/tune-new/checkpoint-002.json
OPENBLAS_NUM_THREADS=1 python -m superfish_ng resume-tune out/tune-new/checkpoint-002.json --out out/tune-continued
```

出力は毎回新しいディレクトリを指定する。Python APIは`tuning.execute_tune`、
`read_tune`、`replay_tune`。CLI終了値はTUNED/PAUSEDが0、検査未達・探索停止が1、
入力/実行エラーが2。PAUSEDは調整成功を意味しない。JobManagerとGUIへの接続も追加済み。

例は半径100 mmの合成円筒で、長さ60–100 mmからTM011の目標周波数を探す。
初期順位のIDはTM010、TM020、TM011と明示し、長さ変更後の順位交換を場で追跡する。
解析式はf=c/(2π)√[(j₀₁/R)²+(π/L)²]、j₀₁=2.404825557695773。
例題の目標値だけを解析式から作成した。製品の探索は毎回FEMを解き、解析周波数へ置換しない。

## 厳密入力

以下はschema_version=1の単一座標入力。全項目必須で、未知項目と不正な数値/型は拒否する。
連動座標は下記のschema_version=2を使う。

| 項目 | 意味 |
|---|---|
| project | 通常Project。section組立・鏡映なし、正半径の連続profile、閉PEC端 |
| parameter | 既存の`/case/geometry/points_zr_m/<頂点番号>/<0または1>`。0はz、1はr。単位m |
| bounds | 昇順の有限な2値。両端形状と細分設定を計算開始前に検査 |
| target_hz | 正の目標周波数 |
| frequency_tolerance_hz | 粗/細両計算で要求する正の絶対目標許容差 |
| parameter_tolerance | 正の探索幅下限。幅だけで成功にしない |
| max_trials | 2以上の整数。両端を含む探索FEM回数の上限。最終細分は別に最大1回 |
| initial_ids / mode_id | 初期順位ごとの一意IDと調整対象ID。初期ラベルの物理的解釈は入力者が指定 |
| controls | 既存追跡controls。normalized_cylinderまたはnormalized_profileを明示 |
| refinement_scale | 2以上の整数。最終同一形状のnr/nzを倍増、指定された局所辺長も縮小 |
| mesh_frequency_tolerance_hz | 正の粗細周波数差許容値。目標許容差と独立に判定 |

円筒写像で半径が一定でなくなる入力は拒否する。一般曲線・折返し・アフィン等の
試行ごとの写像指定はこの版にない。複数profile座標の線形連動は第2版で追加した。

## 判断と保存

両端を実計算し、2点目以降は保存場の対応で全モードの個別IDが確定した場合だけ
目標IDの周波数を取得する。部分空間だけの同定や曖昧対応はUNVERIFIEDで停止し、
当該試行の周波数評価をnullにする。部分空間へ順位だけでIDを割り当てない。

端点または中点が目標許容差内なら、その同じ形状を細メッシュで再計算する。
細分比較は候補の保存場を親とし、直前試行の順位を流用しない。
それ以外は端点の目標との差の符号を調べ、二分法で符号が反対の区間を維持する。
目標を挟まなければUNBRACKETED、回数上限はITERATION_LIMIT、幅/浮動小数点の
中点限界はPARAMETER_LIMIT。いずれも成功ではない。

細メッシュで目標許容差内、かつ粗細差がmesh_frequency_tolerance_hz以内のときTUNED。
片方でも未達ならREFINEMENT_FAILED。基準や目標を自動で緩めない。
この二水準の差は誤差推定の上界ではなく、RF量やピーク場の収束も保証しない。

各試行は通常Jobとして形状・場・RFを保存し、`checkpoint-NNN.json`に全試行の
入力、場対応、評価値、次試行/停止判断、元Jobの全ファイルhashを保持する。
再検証はFEMを再度解かず、保存場から対応と探索判断を再計算する。
入力・controls・過去結果・順序・判断の改変を拒否し、PAUSEDだけ新しい出力先に再開できる。
再開時に過去の点を再計算しない。実行中の既存source変更・実装変更も公開前に拒否する。

形状/solve/検証で例外が出た試行は`failure-NNN.json`へ記録して例外を返す。
既存チェックポイントは保持し、失敗を有利な周波数評価に置き換えない。
失敗の再試行は新しいディレクトリで行う。電源断で未完Jobが残る場合も上書きしない。

## 検証と残件

変更前531件中529合格・2 skip（151.481秒）。未実装importの失敗を確認してから実装。
追加11検査は解析的な円筒長さ、順位交差、二分法、再開、保存改変、実行中改変、
失敗記録、未確認/部分空間停止、二つの細分ゲート、CLIを扱う。

初回の6×8探索でL=83.0078125 mmは粗目標差−87252.09 Hz、細目標差−139668.35 Hz。
粗細差52416.26 Hzは100000 Hz以内でも細目標未達なのでREFINEMENT_FAILEDだった。
`out/d02-tune-refinement-failed-20260908`を保持し、この拒否自体を回帰テストへ追加した。
許容差を緩めず、成功側の探索を12×16へ細分した。

`python scripts/validate_tuning.py --out out/tuning-validation-new`で再現する独立検査は
`out/d02-tuning-accepted-20260908/validation.json`でPASS。尺度1/2とも探索16回＋細分1回。
L=83.00048828125 mm（2倍形はその2倍）、目標長相対差5.88291e-6、細メッシュでの
解析周波数相対差最大1.14697e-7。尺度1の目標差−8722.05 Hz、粗細差3551.50 Hzで
別々の10000 Hz条件を満たす。f/RQ/G相似則相対差最大4.64074e-14。
初期順位3→最終順位2、初期2試行のhash不変、保存再検証を確認した。

一般写像・追跡の枝回復、曲線・組立・非線形変数、細分失敗後の自動再探索、
RF/ピーク制約付き最適化は残る。D01/D02/D03全体や旧tuner互換を完了としない。

最初の標準回帰では調整requestの例を通常Case用examples直下へ置いて2件失敗。
既存Case検査を維持してexamples/tuningへ移動した。初回出力は
out/validation-d02-tuning-20260908に保持する。

最終標準回帰out/validation-d02-tuning-final-20260908はPASS。542件中540合格・2 skip
（163.391秒）。seed周波数差ゼロ、RF/エネルギー相対差最大8.881784197001252e-16。
標準・独立検証のsource_sha256は最終ソースと一致。追加11検査PASS。
数値基準・FEM核・RF核変更なし。新規依存と外部サービスなし。


## JobManagerによる別プロセス実行

2026-09-08。`JobManager.start_tune(request, max_new_trials=None, checkpoint=None)`を追加。
通常のJobManagerと同じ専有workspace内で、FEM調整用の子プロセスを起動する。

```python
import json
from pathlib import Path
from superfish_ng.jobs import JobManager
from superfish_ng.tuning import read_tune

request = json.loads(Path("examples/tuning/pillbox_length.json").read_text())
manager = JobManager("out/tune-workspace-new")
identifier = manager.start_tune(request, max_new_trials=2)
# manager.status(identifier)でqueued/running/complete/failed/cancelledを確認する。
# completeになったらmanager.status(identifier, verify=True)で保存内容も検証する。
# PAUSEDの結果から続ける場合:
# checkpoint = read_tune(manager.directory(identifier) / "tune-results.json")
# continued = manager.start_tune(request, checkpoint=checkpoint)
# 取消しはmanager.cancel(identifier)。全処理を終えたらmanager.close()。
```

この例のstartは非同期で、戻り値は調整結果でなくJob ID。実行直後にcloseすると
管理中のworkerを取り消す。再開は常に新しいJobを作り、古い試行を上書き/再計算しない。

`kind=tune`。status=completeは要求された処理が終了したことを表す。
`tuning_status`がTUNED/PAUSED/UNVERIFIED/REFINEMENT_FAILED/各探索限界を区別する。
`computed_trials`は再開元を含む総試行数。`can_resume`は確認済みPAUSEDのみtrue。
通常Jobの`numerical_validation`はnot_checkedのまま保持し、全般的な精度検証済みとは表示しない。
TUNEDの二つの判定はtune-results.jsonのdecisionに保持する。

完了公開前に入力/実装の変更を拒否し、request/resultsとexecution以下をmanifestへhash保存する。
verify=Trueは保存場から探索・細分判断を再計算し、再開元の全native試行も再検証する。
Job種類・要約・依頼の試行上限・今回の保存先・manifestの必須checkpoint/試行ファイルを照合する。
処理が失敗した場合はfailedとログを保持する。取消し後は、すでに完全に保存され再検証できる
execution/checkpoint-NNN.jsonから別Jobへ再開できる。書込み途中のJSONを確認済みとは扱わない。
管理器の再起動は旧queued/runningをinterruptedにし、tune種類を保持する。

追加7検査では実workerのPAUSED→TUNEDと順位交差、再起動、祖先改変、実取消し後の再開、
入力/要約/種類/試行上限/manifest欠落、数値未達と実行失敗、実行中入力変更を確認した。
GUI操作・電源断・他OSの受入はここに含めない。

`python scripts/validate_tuning.py --background --out out/tuning-worker-validation-new`は
円筒の独立解析・相似則を実workerの開始/再開と管理器再起動を通して検査する。

今回の独立結果はout/d02-tune-jobs-20260908/validation.json（backend=JobManager）でPASS。
尺度1/2とも17試行でTUNED、解析周波数差最大1.14697e-7、f/RQ/G相似則差最大4.64074e-14。
管理器再起動後に初期2試行を再計算せず再開し、hash不変を確認した。

最終out/validation-d02-tune-jobs-20260908はPASS。549件中547合格・2 skip（168.758秒）。
seed周波数差ゼロ、RF/エネルギー相対差最大8.881784197001252e-16。
標準・独立検証のsource_sha256は最終ソースと一致。FEM/RF核・基準・許容差変更なし。


## GUIからの操作

「同じモードの周波数を調整する」で変更頂点とz/r座標、下限/上限[m]、目標[MHz]、
目標許容差[Hz]、探索幅下限[m]、最大計算回数、最終細分倍率、粗細差許容値[Hz]を指定する。
「現在の形状・追跡設定から入力を作成」は上の形状と円筒/profileの追跡controlsを使用する。
初期IDが空欄なら現在のモード数に対応したmode-1、mode-2…を作成する。これは初期順位への
識別子であり、物理的なTMラベルの自動同定ではない。調整対象IDも明示する。
確認用JSONが実行入力となるため、条件欄を変えたら再作成してから開始する。

計算一覧には処理状態と調整結果を分けて表示し、中止/結果表示できる。調整Jobは単独解の
比較選択欄には混ぜない。結果表は探索/最終細分、座標、対象IDの周波数順位、周波数と
目標差を表示する。未確認の周波数は評価不可とし、細分未達は成功としない。
細メッシュの目標差と粗細差の合否を独立に表示する。表の表示を丸めても保存文書は変えない。

チェックポイントはサーバーが再検証した元JSON文字列のまま保存する。読込は元のnative
保存先を必要とし、改変や別形式は拒否する。失敗した読込で以前の確認済み結果を差し替えない。
PAUSEDからの再開は保存文書の条件を使い、入力欄を編集しても再開条件を変更しない。
TUNEDなら「調整済み最終形状の場・RFを開く」で再検証後に最終試行を通常結果へ取り込み、
対象IDが現在占める順位を選んで場を描く。順位1への固定はしない。

GUI用transport追加3検査がPASS。ブラウザーの操作・画像・数値回帰の記録は
[GUI_ACCEPTANCE.md](GUI_ACCEPTANCE.md)のD02記録を参照。一般曲線/非線形変数の調整と
制約付き最適化、取消し後のチェックポイントの自動一覧選択は残る。

最終out/validation-d02-tuning-gui-final-20260908はPASS。552件中550合格・2 skip（178.806秒）。
seed周波数差ゼロ、RF/エネルギー相対差最大8.881784197001252e-16。
標準・独立・3ブラウザーのsource_sha256は最終ソースと一致。基準・許容差変更なし。


## 第2版: 一つの変数で複数座標を連動させる

schema_version=2ではparameterを設計変数の名前とし、parameter_unit（mまたは文字列1）と
bindingsを追加する。他の必須項目・探索/細分ゲート・停止/再開契約は第1版と共通。
チェックポイント自体のschema_versionは1のままで、そのrequestが入力の版を保持する。

各bindingはpath、multiplier、offset_mの3項目を持つ。式は
`coordinate_m = multiplier * parameter_value + offset_m`。
offset_mはm、multiplierの単位はm/parameter_unit（変数がmなら無次元、変数が1ならm）。
boundsとparameter_toleranceは設計変数の単位で指定する。単位ラベルを変えるだけで
数値の自動換算はしない。GUIでは単位・係数・範囲を併せて確認する。

```json
{
  "parameter": "radius",
  "parameter_unit": "m",
  "bindings": [
    {"path": "/case/geometry/points_zr_m/0/1", "multiplier": 1, "offset_m": 0},
    {"path": "/case/geometry/points_zr_m/1/1", "multiplier": 1, "offset_m": 0}
  ]
}
```

上は説明用の抜粋。完全な入力はexamples/tuning/pillbox_radius.jsonで、円筒の両端半径を
同じ長さ変数へ結び付ける。pillbox_radius_factor.jsonは無次元変数とmultiplier=0.1 mで
同じ物理的な半径範囲を表す。どちらも通常のtune CLI/API/JobManager/GUIで実行できる。

pathは既存profile頂点のz/rのみ。先頭ゼロのない頂点番号、重複しない座標を要求する。
全ゼロ倍率、空リスト、未知項目、bool/非有限値、表現範囲外の係数/座標、存在しない頂点は拒否。
少なくとも一つの倍率が非ゼロで、範囲の両端が浮動小数点でも異なる形状になることを要求する。
ゼロや負の倍率は他の条件を満たせば使える。固定座標を指定するためのゼロ倍率も許す。
全指定を一つの新しいProjectへ同時に適用し、最後に形状を検査するため、bindingの順序は
形状を変えない。途中の一座標だけを更新した不正形状を理由に有効な連動変形を拒否しない。

既存の正半径連続profile・閉PEC、追跡の全個別ID確認と二分法の契約を維持する。
一般曲線、組立、非線形な結合関数、複数独立変数の最適化ではない。連動指定を変えた
checkpointの再検証や異なるrequestでの再開は拒否する。

GUIで「複数の座標を一つの設計変数に連動させる」を選び、名前・単位・bindingsを指定する。
単一座標欄は無効になり、範囲と探索幅の単位も切り替わる。確認用入力を再作成して開始する。
保存文書を開くと連動指定を復元し、結果表は変数名と単位を示す。再開は引き続き保存条件を使う。

独立検証は`python scripts/validate_coupled_tuning.py --out out/coupled-validation-NEW`。
長さ/無次元の2表現と尺度1/2をJobManager経由で計算し、管理器再起動後の再開、
円筒半径の解析周波数f=c j₀₁/(2πR)、f/RQ/G相似則、単位表現の不変性を検査する。

最終独立結果はout/d02-coupled-tuning-final-20260908/validation.json。
長さ/無次元×尺度1/2の4系列が各15試行でTUNED、半径相対差5.25034e-6、
最終形状の解析周波数差最大4.33668e-9、f/RQ/G相似則差最大2.57572e-14。
単位表現を変えたf/RQ/G差はゼロ。追加6検査とChrome19項目（追加6/既存13）PASS。
初回ブラウザー検査の非同期生成待ち不足は[GUI受入記録](GUI_ACCEPTANCE.md)に保持した。

最終out/validation-d02-coupled-tuning-20260908はPASS。558件中556合格・2 skip（187.376秒）。
seed周波数差ゼロ、RF/エネルギー相対差最大8.881784197001252e-16。
標準・独立・Chrome検証のsource_sha256は最終ソースと一致。基準・許容差変更なし。
