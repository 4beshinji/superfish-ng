# 平面RFのProjectとローカルジョブ

[平面表示/GUI](GUI_PLANAR.md)も接続・限定受入。以下は保持するProject/JobまたはFEM/nativeの契約と当時の検証記録。Study/追跡等は後続。

専用PlanarProjectと `planar_solve` worker、直接/管理済み取込、再起動・再実行を接続した。主ツリーの独立物理検証・標準/既存数値回帰を確認し、以下の範囲で限定受入。[計画・受入条件](PLANAR_JOBS_PLAN.md)。矩形Case版1と単純多角形Case版2を保持し、軸対称Projectを変更せず別の文書として扱う。

## ProjectとCLI

文書は `format=superfish_ng_planar_project`、`project_version=1`、`case`、`display_length_unit` の四フィールドを全て要求する。caseは既存の平面版1/2。表示単位はmまたはmmで、保存する座標・場・単位長RFはSIのまま。sections、反射、別mesh_dataなどの未知キーを拒否する。多角形の元メッシュはCase版2に含まれる。

```
python -m superfish_ng execute-planar-project examples/planar/project_rectangle_te.json --out out/my-planar-job
python -m superfish_ng execute-planar-project examples/planar/project_triangle_tm.json --out out/my-triangle-job
python -m superfish_ng replay-planar out/my-planar-job/solution
```

付属例は粗い操作例。計算の完了は離散化精度の合格を意味しない。通常の `execute` は従来の軸対称Project用で、平面は明示したコマンドを用いる。出力先は新規ディレクトリに限る。

Pythonの同期実行は `PlanarProject(case, display_length_unit='mm')` と `execute_planar_project(project, directory)`（superfish_ng.planar_jobs）を使う。Project.save/loadは未知キー・重複JSONキーを拒否し、新規ファイルへ保存する。

## ローカルworker

既存 `JobManager` に `start_planar(project)` と `import_planar_result(source)` を追加した。status、list、cancel、closeとworkspace所有ロックを共有する。workerは実FEMを実行し、native保存・固有値/係数再検証を行ってからcompleteを公開する。状態のkindはplanar_solve、physicsはcartesian_cutoff_rf、case_schema_version/modesを保存Caseと照合する。`numerical_validation=not_checked` を保持する。

投入時に保存したProjectのhashをqueued状態に保持する。workerは同じバイト列からProjectを復元し、投入後の変更をFEM実行前に拒否する。完了前後にも入力hashと実装hashを照合する。失敗・中止はcompleteにしない。中止と保存が競合して、既に検証済み完了が公開されていれば完了を保持する。

準備済みworkerの内部入口はqueuedのplanar_solveだけを消費する。worker.claimの排他的作成で二重実行を防ぎ、完了済みディレクトリへの再投入を拒否して元ファイルを保持する。このファイルはプロセスの生存証拠ではない。再実行は保存Projectから新しいジョブを作る。

完了した結果を使う際は `manager.status(identifier, verify=True)` または `read_job(directory)` で検証する。表示用のverify=Falseは完全性を再検証しない。

## 完了と取込

ジョブのmanifestはproject.jsonとsolution内の五ファイル（case.json、mesh.npz、fields.npz、results.json、manifest.json）を過不足なく列挙する。state/manifestのkind、Project/Case/nativeのformatやCartesian座標宣言のどれかが平面を示せば、平面の完全検証を要求する。種別だけを変更して別経路の検証へ逃がさない。

ProjectとnativeのCase・元メッシュの一致、hash、正スペクトル・保存係数・規格化・RF、読込中のファイル変更を検査する。nativeにないmodes.csvを要求しない。リンクしたメタデータ/solution/ファイル、不足・余分なmanifestパスを拒否する。

`import_planar_result` は直接nativeまたはcompleteな平面ジョブを受け取り、元の五ファイルのバイト列を保持して新しい履歴へコピーする。直接nativeの表示単位はmm、管理済みジョブの表示設定は保持する。元データを検証前/コピー後/公開後に照合し、途中変更を拒否する。取込はorigin=importedとし、元係数を新しい解に置き換えない。正スペクトルの再計算は検証のために行う。再起動後も元メッシュを保持して再検証・再実行できる。

## 検証経過

追加14unitはPASS。完了処理中のProject表示設定変更、完了済みworkerの再投入、queued後のProject変更を見逃す反例を先に記録し、入力hash・queued条件・排他的claimを追加して拒否するよう修正した。各失敗と修正後のログはout/planar-jobs-development-20260910に保持する。物理許容差は変更していない。

独立workflowはout/planar-jobs-workflow-final-20260910。矩形/多角形・P1/P2・TE/TM・両尺度16条件の実worker/CLI、直接/管理済み取込32件、実中止、管理器再起動と再実行16件がPASS。物理検証out/planar-jobs-physics-final-20260910は8実workerが終了0（125.642秒）。矩形P1 n256の基本モード、三角形P2 n64の4モードをTE/TM・両尺度で比較した。独立sin/cos場と同じ一つの位相を使い、全成分を体積積分し、壁積分からG/Qを求めた。最大相対誤差はf 1.883e-5、縦場4.872e-5、横場0.006136、G 0.004054、Q 0.004055。実場の独立U′再積分誤差も1e-10未満。f 1e-4、場1%、G/Q 0.5%の別ゲートを満たす。これは選択した細分の精度であり、全ジョブの精度保証ではない。

保存再起動の最終監査out/planar-jobs-persistence-final-20260910で72ジョブ・2同梱Projectの実CLIと全native hashがPASS。監査driverの初回はJobManagerにないcontext managerを使用して失敗したため、try/finally closeへ修正し、両ログを保持した。製品ソースは変更していない。旧平面32件・TE10件の再生out/planar-jobs-native-regression-final-20260910もPASS。標準out/validation-planar-jobs-final-20260910は849件（847合格、2skip、unittest1234.561秒）で終了0。旧TE管理済み8件の再起動検証、TM seed9モード19量f差0/RF最大8.882e-16、標準/独立報告/現在491source一致もPASS。最終seed_regression.jsonとverify_completion.pyを同標準ディレクトリへ保持。全関連実行は終了0。既存.manager.lockのResourceWarningは原因未確定のまま保持する。

[次のGUI工程](PLANAR_GUI_PLAN.md)の受入条件を整理した。GUI、平面Study、追跡・調整・最適化は未接続。曲線・材料・穴/TEM・伝搬は引き続き未対応。
