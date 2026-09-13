# O02: 静的Projectの実worker・保存・CLI

2026-09-13 JST。固定877sourceを主883sourceへ統合し、専用worker/API/CLIの範囲で限定受入。[受入計画](STATIC_FIELD_JOBS_PLAN.md)。

StaticFieldProjectの既存11種類をそのまま専用FEMへ渡すexecute_static_field_projectと、JobManager.start_static_fieldを追加する。kind=static_field_solve。所有Projectを専用プロセスで実行し、線形/反跳P1/P2とB-H P1の元の数値モデルを維持する。二重workerをexclusive claimで拒否し、既存出力を上書きしない。

成功nativeは元の5ファイル、B-H失敗nativeは元の3ファイル。全Case/SI/材料/境界/初期値と成功量・実失敗の全履歴を、既存の専用native readerで実FEM再検証する。元Projectとnative/実装が途中で変われば完了しない。Job manifestはProjectと全nativeのSHA、実装SHA、outcomeを保持し、最後に終端状態を保存する。成功はstatus=complete、保存された非線形失敗はstatus=failed/solver_status=nonlinear_failed/outcome_saved=true。不正入力/保存/中断の失敗を保存済み非線形失敗へ変換しない。

read_static_field_jobはProject・native・manifest・Jobの全来歴を検査し、同じFEMで成功または実際の失敗を再現して、superfish_ng_static_field_project_result/schema_version=1のproject/outcome/statusを返す。read_jobも成功・保存済み失敗を専用検証へ接続する。kindを除去してもProject/Caseのformatから検証対象を識別する。CLI solve-static-project INPUT --out DIRECTORYとreplay-static-project DIRECTORYは同じ全結果をJSONで返す。成功0、検証済み非線形失敗1、不正/未完/IOエラー2。

単体検証は全11形式/対応次数19 Case、3座標系のB-H各3失敗、元FEMと全Case/結果/履歴の一致、元nativeの5/3ファイル、改変した値と再計算したhashの拒否、入力/実装の途中変更、部分保存・二重実行・非上書き、実workerと再起動/中止/強制終了、CLI 0/1/2を対象とする。初回は改変テストの保存先failureが参照failureと重複しFileExistsErrorとなった。検証用保存先だけをfailure-sourceへ変え、既存の失敗ログを保持する。物理実装と許容差の変更はない。既存RF Jobと磁気報告Jobの13件も37.643秒で合格し、専用静的Jobの検出追加による既存経路への影響を確認した。

独立検証は既存の受入済み33成功Caseと3種類×3座標系の9実失敗Case。API/実worker/CLIの各42 Job、再起動後42件、87 CLI呼出で全Project/nativeバイトと元FEM結果を照合する。元192ファイルと新954所有ファイルを保持する。実行結果・時間・固定sourceと標準回帰の合格は受入時に追記する。

この工程は静的Project求解の操作契約。GUI入力・描画は[次工程](STATIC_FIELD_GUI_PLAN.md)、Studyは後続。小さい離散/Newton残差を場や積分量の精度保証としない。新規数値ソルバー・新規依存・旧版実行/コード再利用はない。O02と全計画は未完。

最終独立比較は335.915秒でPASS。初回独立42例も335.192秒で合格したが、テストの保存先名修正後の全sourceへ拘束するため別出力へ最終比較を実行した。単体の初回8合格/1検証用保存先エラーと、修正済みの1件合格を区別して保持。標準は3452.844秒、1401合格・任意NGSolve参照2件/HTTP環境1件skip、ResourceWarningなし。主6unitは90.673秒でPASS。固定877sourceと主883source（不変egg-info 6件）は完全一致。独立全例を主で再実行したとは扱わない。統合証拠はout/validation-static-field-jobs-candidate-20260913/seed_regression.json。
