# 全11カードの条件別受入監査

2026-10-14、元計画はコミット`17a21af`の[11カード](REFACTORING_PLAN.md)。
**全11枚の個別実装・受入・ローカルコミットは完了。最終統合validatorは実行中で、計画全体の完了判断はまだ行わない。**
最終製品ソースは`237f6cd`、`src/tests/scripts/examples`の1507ファイルを固定する。
以下は個別受入の条件と証拠であり、最終fullの成功を先取りしない。

## 元条件と個別証拠

| カード | 実装した境界と元条件の確認 | 受入記録 |
| --- | --- | --- |
| RF-11 | P1/P2の半径・長さ・9 J差替えをRF/保存前に拒否。旧不整合5成果物と再hash改変も拒否、正しい旧2成果物・後処理変更・鏡映・外部meshを保持。67選択unit、独立Bessel場/エネルギー/軸電圧/壁量とseed全RFを別確認。保存/完了版1を維持 | [求解契約](AFFINE_SOLUTION_CONTRACT.md)、`out/rf11-input-contract-20261013/` |
| RF-01 | validator開始/終了の一覧を再収集し、内容変更/追加/削除を受入不可とする。子失敗の終了code/logと元例外、skip-testsの範囲を維持。7選択unit。RF-03の実fullでは失敗/成功の両終端で固定ソースを確認 | [前後監査](VALIDATOR_SOURCE_AUDIT.md)、`out/rf01-validator-provenance-20261013/` |
| RF-02 | core/plotとPython3.10/3.12を分離した四環境、Matplotlib不在拒否、core操作、実HTTP/認証/strict要求、wheel資産。8個別IDの16実行。依存範囲/過去benchmarkは不変、Hosted CIは未実行 | [環境契約](DEPENDENCIES.md#current-environments)、`out/rf02-environments-20261013/` |
| RF-03 | 入力→JSON→来歴の三段階抽出と旧転送API。75/143/11互換probe、113例題canonical hash、直接10/17/25unit。NaN/bool/int/重複/encoding/例外と排他/完了契約を保持。初回full失敗を保存し、五つの統合修正を分離、固定full2689件/528module/3910.941秒PASS | [下位共通処理](LOWER_SHARED_HELPERS.md)、`out/rf03-lower-helpers-20261013/` |
| RF-04 | 直線→曲線→材料Hφの明示contract/名前付きcallback。初期prefix等の差を保持。worker14＋GUI service6、pause/resume/cancel/manager再作成/失敗prefix/移動/改変・リンク拒否。旧新12 FEMの元native/Project bytes・全RF・判断一致、六成果物の追加求解なし再生。JobManager/schemaは不変 | [所有worker](OWNED_TUNING_WORKER.md)、`out/rf04-owned-workers-20261014/` |
| RF-05 | ファイル/solver非依存の純粋判断と五物理adapter。114判断/174adapter比較、55選択unit。INITIAL/PAUSED/UNVERIFIED、両周波数gate、反復/parameter/mesh上限、細分成功/失敗、親indexと回復を保持。未確認fはnullのまま。矩形cutoff/同軸TEM/材料二層/曲線尺度・元場の旧gateを維持 | [調整判断](TUNING_DECISION.md)、`out/rf05-tuning-decision-20261014/` |
| RF-06 | 最初の曲線Hφ run/replay/resume三コマンド群を明示登録/実行へ抽出。他170コマンドASTを保持。全173 parser/help/option/default/必須/順序の比較、13選択unitと13旧新出力比較、終了0/1/2・JSON stdout・上書き拒否。公開entrypoint不変 | [CLI境界](CLI_COMMAND_BOUNDARIES.md)、`out/rf06-cli-20261014/` |
| RF-07 | HTTP輸送と172操作の明示表、共有JSの曲線変形workflowを分離。認証/応答/4・64・128MiB/strictキーと物理別formatを保持。20選択unit、実Chrome36項目、元P2全係数/f/全RF/独立Green、wheel17資産、旧新実HTTP認証等13条件と全172 strict操作。初回誤指定の失敗を保持 | [HTTP/画面境界](GUI_COMMAND_BOUNDARIES.md)、`out/rf07-http-workflow-20261014/` |
| RF-08 | Hφ群の四builderと18 inter-test importをsupportへ移動。21 moduleのテストbody、26生成bytes、元2689 IDを保持し、FEM禁止の入力専用3 IDを追加。入力/runner9と保存15を別指定してPASS。独立参照は不変、削除/重複FEM削減/速度改善の主張なし | [fixture境界](TEST_FIXTURE_BOUNDARIES.md)、`out/rf08-fixtures-20261014/` |
| RF-09 | 現行Case/solve/場/量/native/操作/専用仕様の索引、PHYSICS§4/§7を更新。canonical制限と専用入口、N08公開適応、直線/曲線の離散ピーク、N03/P07限定受入を分ける。実在入口/リンクと履歴保持。文書のみ、新数値受入なし | [現行索引](ARCHITECTURE.md#current-architecture)、`out/rf09-current-index-20261013/` |
| RF-10 | 最初の曲線Hφ所有完了検証を測定。1/2/4履歴長・25DOF/3mode、完了PAUSED/UNVERIFIED/実中止prefix、cold/warm/plain/観測を60操作で分離。累積prefix71.4%を根拠に実行内再利用。13選択unitと元9native/27modeの全場/RF/ID/判断・独立尺度、bytes/要求/親/実装改変拒否。履歴4のwarm34.482→9.954秒、読取増/RSSほぼ同等も記録 | [再生費用](OWNED_REPLAY_COST.md)、`out/rf10-replay-cost-20261014/` |

各rawの`acceptance.json`は`commit.json`のSHAとローカル祖先commitへ結び付く。
`out/refactoring-final-acceptance-20261014/original-requirements-audit.json`では元11節の条件が順序を保って残ること、
全カードのSHA付き証拠、現行の下位import方向、索引の実在symbol/local linkを確認した。
原141行は`17a21af`と完全一致し、全152は102 DONE/3 IN_PROGRESS/47 PLANNED。
V02/V03/V05とADD-N04-rf-goal-05の元依存・循環なしを保持する。

## 最終統合の実行状態

`out/validation-refactoring-all11-20261014/`へ次を**一度**開始した。直前の全unittest再実行は行わない。

```sh
OPENBLAS_NUM_THREADS=1 MPLCONFIGDIR=/tmp/superfish-refactoring-final-mpl \
PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-uv-cache \
uv run --offline --no-sync python scripts/validate.py \
  --test-workers 8 --out out/validation-refactoring-all11-20261014
```

実sessionは`3414`、ログは`out/refactoring-final-acceptance-20261014/full.log`。
開始時1507源のSHAは同rawの`source-before.json`、実行条件は`start.json`。
**実際の終端/終了codeとvalidator reportを確認するまでfull PASSとしない。**
次の作業は同sessionの継続確認であり、観測時間切れだけを理由に再実行しない。
終了0を観測して`full-session.json`を更新した後、準備済み`audit_final_full.py`で
全2698 ID/530module、実skipのID/理由、前後source、全seed modeのf/全RF/保存再構築を監査する。
既存RF-03 fullや単なる収集結果を、この最終fullの証拠へ読み替えない。

最終ソースから独立実装packageだけを`/tmp/`へコピーしてwheelを隔離ビルドし、
全製品bytes、RF-10新moduleのimport、17資産の実HTTP GET、entrypoint/依存宣言/LICENSE一致を確認した。
同wheelのcore CLI・Matplotlib不在時の説明付きGUI拒否と17資産はPython3.10/3.12でPASS。
rawは`wheel-audit.json`と`core310-final/`・`core312-final/`。新FEMは0、主ソースは不変。
これは最終fullやサポート版全物理の検証、第三者binaryの配布認証を代替しない。

## 保持する範囲と未移行経路

RF-06は曲線Hφ三コマンド、RF-07のJS分離は曲線変形一workflow、RF-08はHφ fixture、
RF-10の測定/再利用は曲線Hφ所有完了検証から始めるという元計画の単位を維持する。
他のCLI群・画面状態群・static fixture、planar/直線/材料の再生費用は未移行・未測定である。
これらへ今回の性能値を外挿しない。public checkpoint読込・別検証・再起動は全再生し、永続hash-only信頼は導入しない。

数値核・物理許容差・schema・依存は機械的抽出で変更しない。
SI/peak phasor/両R/Q、専用物理の拒否、順位とID、固定P2/離散ピーク/有限guardの限定保証を保つ。
元失敗・未確認・中止・任意依存skip、初回full失敗と五統合修正は各scopeのまま保持する。
新外部資料・legacy資産の参照/転載はない。既存自作実装・合成形状と既存数学だけを使用した。
L06/L07の実測・不確かさ、V02/V03/V05の元配布/統合/互換受入、残る原機能カードの完了は別条件であり、
今回のリファクタリング受入でDONEへ昇格させない。
