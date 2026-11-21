# P08：共通Case・Project・CLI-worker・Study・元場表示

2026-10-07。[専用native](PLANAR_CURVED_NATIVE.md)の続き。P08はIN_PROGRESS。
共通入口の実装と限定操作検査を受入れる。実ブラウザーの曲線フォーム・保存往復・
サーバー再起動と旧版操作の受入は残り、GUI APIの成功でP08をDONEにしない。

受入追記：[実Chromeと別server再生の全条件監査](PLANAR_CURVED_OPERATION_ACCEPTANCE.md)は
35項目PASS/全hash不変/全handle終端。P08 DONE。下記の限定操作検査と実ブラウザー受入を区別する。

## 接続と独立契約

`planar_case_from_dict`と`PlanarProject`は版3を専用曲線parserへ明示dispatchする。
全Domain/numerics/RFを保持し、版/geometryの不一致、非真空・非PEC・非零beta・TEMを拒否する。
新`planar_solve.solve_planar_case`は専用曲線solverを呼ぶ。矩形/多角形は元solverのままである。
共有数学/固有対/正規化/原phasor演算は変更していない。

共通`save_planar_run` / `read_planar_run` / `planar_result`は曲線専用nativeへdispatchする。
読取の外側snapshotも検査し、版3の読取途中変更を拒否する。旧版1/2は従来の保存契約である。
CLI solve/replay/probe-planarと既存Project worker/所有import/Study workerは同じ実FEM/nativeを使う。
所有importは元五ファイルをコピーし、新solveの実装来歴を主張しない。
実workerは完成manifestと実装hashを保持し、新規directoryだけを作る。

Studyのuniform_scaleは全二次nodeを原点から正倍率で変換し、cell/壁の接続を保持する。
energy/σ sweepは全元geometryを保持する。矩形寸法の変更を曲線へ適用しない。
各点は独立正スペクトルであり、モード順位を永続IDとして扱わない。

表示の四分割triangleは元六node cellから作り、各reference中心の全phasor場を元二次写像で評価する。
曲線probeは専用strict point locatorを用いる。壁表示は元二次壁を各辺33点で標本化する。
表示の直線分割/標本はRF積分や連続場の精度証明に使用しない。
plot/probe/GUI APIの結果は元五ファイルのhashと全RF/単位に結び付けられる。

P09で未実装の曲線比較/追跡/収束/調整・直線Project変換は入口で明示拒否し、
曲線Caseを直線meshへ解釈しない。追跡workerは出力作成前に拒否する。

## 反例・検査と範囲

共通parserへ実曲線TE/TMを渡す最初の検査は`unknown keys ['numerics']`で失敗した。
`operations-baseline.log`を保持する。実装後の新9件は分割受入：
初回17.273秒では7件PASS、2件FAIL。独立尺度解の任意位相を固定符号とみなしたテストと
追跡worker APIの引数順の誤りだった。元FAIL logは保存し、製品と許容値を変更せず、
該当2件だけを再実行して5.490秒PASS。位相は元質量内積の絶対overlap=1を独立確認して
符号を整合する。これは独立尺度則の検査であり、未実装のモードID追跡ではない。

新検査は、独立専用APIとProject/共通native/実CLIの元係数・周波数bytesと全RFの一致、
全12 signed SI場、曲線壁/元reference標本、TE/TM二尺度のf/E/H/U′/P′/Q/G則、
energy/σ則、実稼働workerの中止・終端・新job再起動、通常/所有nativeの元byte importと
管理器再作成、GUI APIの起動/全RF/全五ファイルdownload/元点probe/PNG、P09入口拒否を対象とする。
入力は自作の回転/平行移動楕円16cell（中止用は元曲線写像の1024cell制限細分）。
測定構造や連続固有値の精度検査として扱わない。離散化受入はP07の専用証拠を継承する。

直接利用先の48件（曲線native7、旧経路41）は32.964秒/終了0 PASS。
共通dispatch/IOが変わったため専用native7を再検査し、旧jobs/Study/display/GUIと
parser/native/CLI、旧収束/調整/形状/追跡入口を選択した。full discoveryは実行していない。
実装sourceは全実worker終端まで固定し、全テストの所有processをcloseした。

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-ng-uv-cache \
uv run --no-sync python -m unittest -v test_planar_curved_operations
```

上記初回の2件は`test_independent_study_scaling_and_rf_sweeps`と
`test_unimplemented_comparison_and_tuning_reject_before_output`だけを修正・再実行。
直接利用先は次の選択であり、全suiteではない。

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-ng-uv-cache \
uv run --no-sync python -m unittest -v \
  test_planar_curved_saved test_planar_jobs test_planar_study test_planar_display test_gui_planar \
  test_planar_polygon.PlanarPolygonTests.test_strict_v2_and_legacy_reader_separation \
  test_planar_polygon.PlanarPolygonTests.test_native_v1_and_v2_replay \
  test_planar_polygon.PlanarPolygonTests.test_rehashed_case_and_version_tampering \
  test_planar_polygon.PlanarPolygonTests.test_cli_all_components_and_native_protection \
  test_planar_rf.PlanarRFTests.test_cli_save_replay_and_si_probe \
  test_planar_convergence.PlanarConvergenceTests.test_strict_request_roundtrip_budget_and_full_geometry \
  test_planar_tuning.PlanarTuningTests.test_invalid_requests_and_preserved_checkpoint_on_failed_trial \
  test_planar_affine_shape.PlanarAffineShapeTests.test_original_project_area_shear_reflection_and_serialization \
  test_planar_tracking_jobs.PlanarTrackingJobTests.test_portable_copied_native_replay_and_completed_reentry
```

全logは`out/p08-planar-curved-native-20261007/operations-*.log`。
ブラウザーでの実操作、full validate/seed/CI、新外部資料/依存/legacy参照は追加していない。
変更はCartesian操作経路と未実装の直線入口で境界付けられ、専用曲線・共有P2・seedのFEM/RF数学を変更しない。
続く実ブラウザー操作・[P08全条件](PLANAR_CURVED_INTEGRATION_PLAN.md)、P09/原要件/全123カードgoalを継続する。
