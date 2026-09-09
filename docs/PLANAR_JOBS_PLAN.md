# 平面RFのProject・ローカルジョブ接続計画

[矩形・単純多角形の平面RF](PLANAR_POLYGON_RF.md)を、再実行可能な編集文書とローカルworkerへ接続する次工程。現在は設計であり、PlanarProjectや平面ジョブの製品対応を宣言しない。

## 独立した文書と実行種別

現行Project版1/2は軸対称Case、sections、z端反射、別mesh_dataを前提とする。平面にダミーの軸対称Caseや無意味なz端を与えない。専用 `PlanarProject` を `format=superfish_ng_planar_project`、`project_version=1`、平面Case版1/2、`display_length_unit=m|mm` のstrict文書として用意する。元の明示xyメッシュはCase版2に保持する。表示単位をSIの保存量へ混入させず、sections/反射/別mesh_dataは拒否する。

従来Project/executeを変更せず、明示した平面Project実行API・CLIと、`JobManager.start_planar` を追加する。ジョブ種別は `planar_solve`。workerは実 `solve_planar` と既存native保存を呼び、入力Project・実装hashの前後一致を要求する。計算完了とメッシュ精度合格を区別し、workerの完了だけで離散化精度をcheckedとしない。

## 完了と保存結果の結び付け

平面nativeにはmodes.csvがなく、既存solveジョブの必須ファイル集合をそのまま流用できない。平面ジョブはproject.jsonとsolution内の五nativeファイルを完全に列挙し、保存の完了manifestとジョブ側manifestを双方検証する。ProjectのCaseと保存Case/明示メッシュが一致し、保存固有値・係数・場/RFを完全再検証できることを完了条件とする。

state/manifestのkind、Projectのformat、nativeのformat/physicsのいずれかが平面を宣言する場合は平面の厳密検証を要求する。kindだけを削除・変更して軸対称の検証経路へ逃がさない。relative path・symlink・hash・読込中の変更を拒否し、完了markerは最後に公開する。

## 管理器と取込

既存JobManagerの単一workspace所有・process追跡・中止/kill・再起動履歴を共有し、平面workerを独立したmoduleとして起動する。失敗/中止をcompleteとしない。完了保存が中止と競合して先に完成した場合は、検証済み完了を保持する。閉じた管理器への投入を拒否する。

直接の平面nativeと管理済み平面ジョブを、明示した `import_planar_result` 経路で取り込む。取込で新しいFEM解を生成・置換せず、検証済みの元ファイルと明示メッシュを保持する。保存Projectと取込先を再検証し、元ファイルhashを検証前/コピー後/公開後に確認する。元管理ジョブのProjectやmanifestが途中で変わった場合も失敗させる。再実行は取込とは別ジョブとして行う。

## 受入条件

- 矩形版1/多角形版2、P1/P2、TE/TM、表示単位、strict未知キー拒否とProject保存往復。
- API/CLI/実workerの同じ入力・FEM結果、Project/nativeの完全結合、必須ファイル不足・再hash改変・版/種別変更・コピー中変更拒否。
- 直接/管理済み取込、元メッシュの番号保持、元hash不変、再起動後のverify=Trueと再実行。
- 実workerの中止、再投入、管理器close/reopen、放置runningのinterrupted分類。既存の所有ロックを維持。
- 独立三角形/矩形のf・場・単位長RFと両尺度、既存TM/TE/平面native、標準回帰。粗い操作例の保存一致と細分した物理精度を区別する。

GUI・Study・追跡/調整/最適化は続く工程。既存の管理器終了時に出ている.manager.lockのResourceWarningは原因未確定の別残件として保持する。再現なしに原因を断定したり、警告を抑制して解決扱いにしない。
