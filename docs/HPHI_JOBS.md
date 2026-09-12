# P03/O02：正半径HφのProjectとローカルジョブ

2026-09-12、一般断面FEMの後続として以下のProject・ジョブ操作を主ツリーへ統合し、限定受入した。

## 対象と結果の意味

専用 `HphiProject` は閉同軸円筒のCoaxialCase版1と、明示正半径断面のHphiMeshCase版1を扱う。
Projectは `superfish_ng_hphi_project`、project_version 1。Case全体と表示単位m/mmを保存し、物理はSIを保持する。
一般断面の外周・穴・元節点・三角形・P1/P2次数を入力のまま保存する。円筒を一般メッシュへ暗黙に変換しない。
軸接続TM/TEや平面のProjectとは別形式。未対応の鏡映・Study・追跡・調整指定を受理しない。

JobManagerに `start_hphi` と `import_hphi_result` を接続し、kind=`hphi_solve` の専用workerで実行する。
完了にはProject、nativeの全5ファイル、両manifestの整合と完全な幾何/FEM/RF再生が必要。
状態・manifestのkindを通常solveへ書き換えても、元Case/Projectの形式から専用検証を要求する。
summaryのcase_format・版・モード数・physicsも照合する。
`numerical_validation=not_checked` はジョブ単体では離散化精度を判定しないことを意味する。
実行完了と周波数/場/RFの物理収束を混同しない。

## 実行・取込・再起動

workerはqueued状態と投入時Project hashを検査し、一つの排他的claimで実行権を取る。
入力や実装の途中変更、保存失敗、native検証失敗はfailedとし、完了へ進めない。
既存ジョブやclaimを再消費しない。完了済みジョブは再実行先の新しいディレクトリを用いる。
管理器の中止・再起動・未完了状態のinterrupted復旧・終了済み管理器の拒否は既存の運用契約を使う。

取込は直接nativeと管理済み完了ジョブの両方を扱う。コピー前後と完了時に全source hashを照合し、
変更・symlink・不足ファイルを拒否する。所有コピーの元係数・元メッシュ・native bytesを保持する。
再検証のため正スペクトルを再計算するが、取込を新しいFEM実行として記録しない。
元ジョブを消したり更新したりしない。再起動後も公開read_job/明示verify=Trueで完全再検証できる。

```python
from superfish_ng.coaxial import CoaxialCase
from superfish_ng.hphi_project import HphiProject
from superfish_ng.jobs import JobManager
import time

project = HphiProject(CoaxialCase(.025, .05, .18))
manager = JobManager("new-local-workspace")
try:
    identifier = manager.start_hphi(project)
    while manager.status(identifier)['status'] in ('queued', 'running'):
        time.sleep(.1)
    result = manager.status(identifier, verify=True)
    if result['status'] != 'complete':
        raise RuntimeError(result)
finally:
    manager.close()  # Closing a manager cancels its unfinished workers.
```

完了まで実行するCLIは次のとおり。

```sh
python -m superfish_ng execute-hphi-project examples/coaxial/shorted_project.json --out new-coaxial-job
python -m superfish_ng execute-hphi-project examples/hphi_mesh/holes_project.json --out new-hphi-mesh-job
```

Project編集GUI、場表示GUI、Study・収束診断・追跡はこの工程の後続。既存専用solve/replay/probe CLIは保持する。

## 受入条件

1. 二つのCaseをstrict Projectとして保存往復し、通常軸接続/平面Projectへ誤読しない。
2. 両次数の実worker・直接CLI・API・nativeの物理入力、元係数による全場・RFが一致する。
3. 全3D U[J]/P[W]、phasor、加速量N/Aを保持し、二尺度のf/G/Q/P/U/体積とE/H則を確認する。
4. 直接/管理済み取込で全native bytes不変。再起動後の公開検証と保存Projectからの再実行が成功する。
5. kind降格、hash再作成後のProject/RF改変、source/実装の途中変更、失敗、中止、重複worker、未完了復旧を検査する。
6. 既存軸接続TM/TE・平面・円筒Hφ・一般断面Hφの標準回帰と周波数/RF seed比較を通す。

独立 `scripts/validate_hphi_jobs.py` は両幾何・両次数・両尺度の8worker、16取込、24完了ジョブの再起動後検証を実行する。
ここでは操作とSI相似則を検証する。使用する小メッシュを新しい離散化精度の受入証拠にはしない。
相似則のゲートは1e-8、UとUE/UHも1e-8。精度ゲートは既存円筒/一般断面の独立検証を保持する。

## 検証履歴

初回8unitで、CLIの別プロセスの固有ベクトルと新しい直接solveから計算した文書をbit単位で等しいと要求した比較が失敗した。
差は約2.1e-15の直交性診断の末尾で、同じ保存係数からの完全native再生は合格した。
別solve間はRF各量を相対1e-11で比較し、CLI出力と同じ保存係数の再生文書は完全一致を維持した。
修正後8unitは8.681秒で合格。FEMの数値式・既存精度ゲート・nativeの完全一致検証は変更していない。
独立workflowと全体回帰は下記のとおり完了した。

新規外部資料・依存・旧版参照なし。既存自作のPlanarProject/workerの所有・manifest・中止契約を、
明示したHφの二つのnative形式へ接続した。P03/O02と全互換計画は未完。

## 最終受入証拠

標準1007件（1005合格・2skip）は1950.805秒でPASS、ResourceWarningなし。
独立8実worker・16取込・24ジョブの再起動検証は32.940秒、SI相似則の最大相対差4.713e-14。
候補の全574sourceが標準・独立・終了後で一致。主ツリーは同じ574sourceと従来の不変egg-info 6件、計580件。
統合後も8unitを8.299秒で再実行し、同梱2例題の実CLI・公開read_job・保存Projectの完全一致を確認した。
既存seed9モード19量の周波数差は0、最大相対差8.882e-16。既存ベンチマークは更新していない。

証拠はout/hphi-jobs-development-20260912、out/hphi-jobs-independent-20260912、
out/hphi-jobs-examples-candidate-20260912、out/hphi-jobs-examples-main-20260912、
out/validation-hphi-jobs-candidate-20260912/seed_regression.json。hosted CIと新しい旧版実行は行っていない。
次の表示/GUIは[専用計画](HPHI_GUI_PLAN.md)に従い、隔離候補で検証する。
