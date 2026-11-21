# RF版5対照：実TERM/KILL・再開境界・旧参照の再生

2026-10-14 JST。[04の条件別監査](CURVED_RF_GOAL_EFFICIENCY_WORKER_ACCEPTANCE.md)へ接続する。
固定36実行05、GUI/原条件監査06、親N04と全計画は未完。

## 実装した契約

killされたworkerは `failure.json` を書けないため、`interruption_files` は既存の
SIGINT用二ファイルに加え、実supervisorが終了後に閉じた `manifest.json` 一ファイルを扱う。
CLIで既に使っていた四つのbundle関数を `curved_rf_goal_efficiency_bundle.py` へ移した。
元bodyはAST一致、旧script名からのimportも保持する。FEM・RF・選択/停止の式は変更しない。

TERM/KILL再開は、元hash、全ローカルfile/部分byte、前後sourceのUNCHANGED、
実terminal processのSIGTERM/SIGKILL終了、同じinvocation hash/専用script/cwd/native出力を照合する。
誤った出力先・実行行・終了値・source差分、古いcheckpointの選択は再hash後も拒否する。
原processのwall/RSSと未採用native/部分保存を元bundleへ残す。
書けなかった内部phase時間やin-flight求解数を0で補わない。

新しいcheckpointがある場合は最後の完全公開journalだけを採用する。
再開後の最初の新checkpointがまだない場合に限り、起動要求自身に記録された
元journal/path/SHAへ戻る。その元journalも全場/要求/履歴を完全再検証する。
新nativeの `save_complete.json` があっても、未公開checkpointを採用へ昇格しない。
再開は別出力先を要求し、元の全event/native/sample/費用prefixを変更しない。

## 旧参照と追加アーカイブ

旧journalの元実装を全て同じbyteのarchiveから照合しても、参照sourceのpath変更で
保存readerが拒否する反例を先に再現した。固定参照manifestから実際に照合した
source移設だけを扱い、全必須入力のSHAを要求する。
元dataset/grid/manifest/sourceの欠落、違うhash、架空のsource名、不正なSHA型を拒否する。

source archiveを追加した再開では、記録された参照mapが増える場合がある。
親の完全再生で固定入力から得た `reference_binding_context` を用いて照合する。
contextはreaderの返却値だけにあり、journalが自己申告することはできない。
新旧の全必須参照を再検証し、任意の追加sourceも元byteを束縛する。
native/journalの保存schema、元要求、全配列/RF/ID/判断、元の数値閾値は維持する。
source archiveは実行しない。

## 実検証

rawは `out/n04-rf-goal-termination-20261014/`。
最終監査は `acceptance.json`、`audit_final.py`、`audit-final-terminal.log`。
新9を含む52個別unitを、変更ごとに対象を選んで分割PASSした。
主な最終logは `selected-final.log`（27件）、`reference-compat-final.log`（34件）、
`fallback-main-final.log`（25件）、`context-selected-final.log`（30件）。
重複を足さず、SHA型guardの後は影響するintegrity6件だけを1.790秒で補完した。

| 実中断 | 完全prefix | 既存の未公開native | 再開後 |
| --- | --- | --- | --- |
| 球一様・TERM | 1 event | event 2完成 | 2 event、全再生PASS |
| 球一様・KILL | 1 event | event 2完成 | 2 event、全再生PASS |
| 球rf_goal・KILL | 1 event | event 2完成 | 2 event、全再生PASS |
| 一様の再開・新checkpoint前にTERM | 元の2 event | event 3完成 | 元journalから3 event、全再生PASS |
| 一様の再開・新checkpoint後にKILL | 3 event | event 4完成 | 最新journalから4 event、TARGETS_MET/全再生PASS |

五つの再開結果は元無中断と全187 native/sample配列のbyte、全mode/RF辞書が完全一致する。
原の全prefixも一致し、全原journalのbyteは不変。
元三方式/長球の四journal・全12 event/24 sampleを現行の数値処理で再生した。
長球の80→320棄却→元親80から113局所も全分岐・元場・停止を維持した。
旧費用を現在の計測値へ書き換えず、物理誤差上界はnullのまま保持する。

球/長球/丸め形状×両尺度の六初回実行も、開発上限1 eventで実FEM/完全再生した。
全てPAUSEDであり、固定36行の目標達成とは呼ばない。
六ケースの場・周波数・RFを独立Maxwell相似則で確認した。

| 三形状の最大相対差 | 値 |
| --- | ---: |
| 周波数 `2 f(a=2)/f(a=1)` | 1.9984e-15 |
| 両R/Q・G・両peak比の尺度不変 | 1.9673e-13 |
| 元全E/H/物理軸、振幅 `a^-1/2` | 5.9359e-14 |
| Ue/Uhと各指定U/2 | 1.8874e-15 |

全case・全mode・両Gauss次数を使用し、modeごとにHφから一つの符号だけを合わせた。
振幅fitや成分別の符号fitはしない。f/場/RFの各相似差は元1e-10内、energyは1e-12内。
両R/Qの2倍関係も維持する。この尺度則は連続物理精度やpeak収束の保証ではない。

実processの新求解は20回、unit内の小FEM1回は別計上。
保存再生の新固有求解は0。随伴/比較の線形求解は再生にも含まれる。
全16 bundleは各実行内で1511 sourceの前後UNCHANGED、実終了/wait4回収とtool終端を確認した。
後日のPID不在検査はPID再利用/namespace差を区別できないため、終端証拠へ使わない。
readinessの絶対時間には旧journal再生との並行時間もあり、方式速度比には使わない。

初回未実装、digest import、fixtureの元checkpoint移設、参照map増加、SHA型の各失敗を保持した。
完成した3 eventの再開結果は、参照context修正後に**同じ元journalのまま**完全再生した。
再求解せず、元native/元費用/失敗logを上書きしていない。
監査の古いsource hash照合は同一byte archiveへ対応させ、PID検査は実wait4/tool終端へ修正した。

最終 `accepted-source-archives.json` は65個の元SHA→絶対path。
SHAは `3f4ea774098d7257a2bf0633b36987750a72c52605ec3af7ca7d062bea34366c`。
後続の再生はこのmappingとそのSHAを明示する。元コード/数値data・既存8 aliasは不変。
新外部資料/依存/legacy、seed/full validator、GUI、Hosted CIは実行していない。

