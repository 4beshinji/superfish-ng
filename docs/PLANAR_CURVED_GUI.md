# 平面曲線の比較・履歴・調整GUI

2026-10-07後続：[実Chrome比較・履歴回復/延長・取消し](PLANAR_CURVED_GUI_HISTORY.md)を分割14項目で受入し、診断全文scroll/未確定表示を修正した。残る大容量調整checkpointとP09全条件は継続。以下は初回GUI接続の検証履歴。

2026-10-07、P09の有界GUI接続。P09はIN_PROGRESS、全123カードgoalは継続する。
受入条件は、専用strict要求の往復、元nativeのE/H・有限guard・個別ID/集合の保持、
実過去anchor回復と延長、要求へ束縛した停止checkpointの再生/新job再開、
元場表示への実周波数順位の受渡しと全元byteの保存である。
科学核は先行の[比較worker](PLANAR_CURVED_TRACKING_JOBS.md)、
[独立履歴worker](PLANAR_CURVED_TRACKING_HISTORY_JOBS.md)、
[調整worker](PLANAR_CURVED_TUNING_JOBS.md)を使用する。

## 操作と保存

主平面RFページから `/planar-curved.html` を開く。
曲線専用の比較要求、順序付き比較job配列/履歴要求、回復要求、調整要求をJSONで編集し、
専用型で正規化・保存・ファイル読込する。完全二次写像、比較分割/求積/guardの予算、
形状法則、探索範囲、対象IDと最終細分を明示する。初期空要求から対応を推測しない。
座標はm、周波数/許容差はHz、変形パラメーターは無次元である。

`gui_planar_curved` は `planar-curved-` の19操作を提供する。
比較/履歴/回復/調整の正規化、各workerへの投入、完了再生、履歴回復/延長、
元native取り込み、停止checkpoint列挙/選択、保存地点の再生/再開とtrial取り込みを扱う。
未知key、重複JSON key、不正型、違うkind、非完了/非停止状態は拒否する。
checkpoint一覧の列挙は `verified=False`、選択時に全物理/作成来歴を再検証する。
比較/履歴の全祖先、調整の全prefixを取り込み前後で検査し、遅い元source変異を拒否する。

表示は元E/Hの独立対応、符号、有限guard、個別IDと継承集合を区別する。
個別ID未確認の周波数はnullを保持する。目標差と最終粗細差の両gateも別に表示する。
元SI、単位長のpeak +i phasor、全RFと二つの名前付きR/QのN/Aを保持する。
元場は既存平面ページへ取り込み、調整対象の実順位を `mode` queryへ渡す。
順位はidentityラベルではない。各元五nativeはbyteコピーし、新求解へ帰属させない。

GUI保存選択は `superfish_ng_planar_curved_tune_selection` / `selection_version=1`。
元scientific checkpoint全体に `owner_job_directory` と `checkpoint_index` を束縛する。
科学checkpoint自体のschemaは変えない。これによりゼロtrial/失敗prefixも実停止jobの
要求・submission/start/claimへ束縛して再生できる。
非ゼロの元所有checkpoint単体も全物理再生する。ゼロprefixには明示ownerを要求する。
再開は検証済みPAUSEDから新jobを作り、元九byte/creator/claimを保持する。
JSON編集と保存/ファイル読込の非同期競合は入力revisionで検出する。

## HTTP容量と表示

先行受入の完全checkpointは円40,980,088 byte、回復付きTE楕円91,932,064 byte。
元chart/診断/全trialを切り捨てず、曲線のreplay/resume/trialの3操作だけ128 MiBを許す。
`X-NG-Action` とbody actionの一致を要求する。hintなし事前上限64 MiB、
既存Hφの64 MiBと一般操作4 MiBは維持する。認証後にstrict JSONを読む。
65 MiB合成文字列のdecoder検査は輸送検査であり、大容量科学checkpointのGUI受入ではない。
その実ファイル往復は後続で確認する。

専用ページのtextareaだけパネル幅に合わせる。CSP/localhost/既存共有styleを維持する。
新依存、外部通信、solve時のremote serviceは追加しない。

## 検証と残る範囲

rawは `out/p09-planar-curved-gui-20261007/`、直前基準 `d780c1d`。
API不在を `api-baseline.log` にFEM前記録。独立不変量は実TEの反射parity/rank交換、
真円TE doubletのnull、実TM拡大f逆尺度則と全元native/creatorのbyte保存。
FEM/物理gate/benchmarkは変更していない。

新 `test_gui_planar_curved` の8種類と直接利用先6種類を分割受入した。

| log | 実施範囲 | 結果 |
|---|---|---|
| initial-test.log | strict/decoder/HTTPの3件 | 2成功、socket権限ERROR、4.099秒/終了1 |
| http-test.log | 権限を適用して不足HTTP1件 | PASS、1.844秒/終了0 |
| tracking-test.log | 元二点取り込み/遅い変異、実anchor回復/延長の2件 | PASS、180.548秒/終了0 |
| tuning-test.log | 保存/再開/生存中元source移動、失敗ゼロprefix、真doubletの3件 | PASS、128.969秒/終了0 |
| related-test.log | 既存body上限2、平面worker/調整/回復、Hφ HTTPの6件 | PASS、81.415秒/終了0 |

入口は `OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python -m unittest -v test_gui_planar_curved`。
元試験のworkspace helperは `SUPERFISH_CURVED_TUNING_TEST_ROOT` に未使用保存先を指定する。
このmodule全体を一括実行したとは数えず、上記method選択と関連6件で受入した。

実Chrome 153 / Node 24の新検証器 `verify_gui_planar_curved_tuning.mjs` は共通browser資源管理を使う。
入力の保存/同じファイル再読込、実FEMの1trial PAUSED、checkpoint全再生、
実順位/SI/RF表示、全元五ファイルの実ダウンロード一致、元場画像の6項目が成功した。
その後のnavigation待ち不足で検証器が `tune is not defined` を報告し、元FAILを保全した。
不足操作では実GUIが新2trial jobを作ったが、検証器helperのscope誤りで再びERROR。
helper修正後はこの実作成jobを再利用し、新trialを重複生成せず、再開後PAUSED/実f比1.4と
全元九byte prefix一致の残り1項目をPASSした。7項目の分割受入であり一括PASSではない。
元検証器2版と各report/logを保持する。

最初の画像でJSON欄が狭い表示問題を確認して専用CSS selectorを修正した。
全数値/サーバーhandle終端後にだけ製品sourceを編集し、FEM0のrender-only 1項目をPASS。
可視欄は344/919pxの各親幅と一致し、画像を目視確認した。
初回実作成420源と表示修正後420源の差はHTML/CSSの2assetだけ、元版はarchiveに保存する。
作成時sourceを現在のreader sourceへ書き換えない。

`gui-acceptance.json` / `final-audit.log` は新FEM/物理再構築0の最終byte監査。
完了GUI-owned外側16job（比較7/履歴3/調整6）/調整8trial snapshot、768 manifest entry、
全420 creator源、元五byte import/九byte resume prefixを照合した。
監査器のpath prefix/heading case誤り2ログも保持し、製品変更なしで監査だけ補完した。
元417製品中412は不変、変更5はGUI輸送/ページ/表示、追加3は専用GUI。
全123 TSV/依存/anchorと61 DONE・2 IN_PROGRESS・60 PLANNEDを維持する。
全handle/実worker/両server終端、Chrome slot 0、外部要求0。

実Chromeでの比較・履歴回復/延長・取消し、元受入円/TE大容量checkpointの
実ファイル再生/実順位2の場表示とP09全条件監査は後続。
限定GUI接続をP09全体/全goal完了とは扱わない。
full/seed validator、Hosted CI、Wine/GPU、新外部資料/legacy参照は今回未実施。
先行の受入記録を今回の再実行へ数えない。
