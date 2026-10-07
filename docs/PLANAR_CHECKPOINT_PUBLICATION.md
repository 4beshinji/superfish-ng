# 平面調整checkpointの完全公開

2026-10-07、P09節目全validateで発見した共有保存処理の有界修正。
受入条件は、公開checkpointが存在すれば完全JSONであること、既存targetを上書きしないこと、
元JSON byte/元trial/strict parser/科学計算と取消し時の再開条件を保つこと。
修正・限定検査・共有変更後の全validateとseed f/RF照合はPASS。P09全条件は受入済み。

## 最初の失敗

`out/validation-p09-milestone-20261007/test-run/test_planar_piecewise_tuning_jobs.log` の
`test_actual_cancel_select_prefix_move_resume_and_manager_restart` は、公開checkpointを見て
実workerを取消した後、JSONの途中（3014行目、65576文字目）で読込ERRORとなった。
`planar_tuning_saved._write` が最終pathを `open('x')` してからserializationするため、
ファイルの存在を完全保存とみなせない。取消しの待機条件/時間やJSON再試行で隠さない。

独立の保存不変量も元実装でFAILを確認した。途中serializationで公開先が見え、
非有限値を拒否しても部分JSONが残る（3検査中2FAIL）。
別の実producerを部分serializationの地点で強制終了しても公開先に部分JSONが残る（1FAIL）。
原ログは `out/p09-planar-curved-large-gui-20261007/publication-invariant-baseline.log` と
`publication-killed-producer-baseline.log`。これらは保存不変量の証拠で、FEM精度検査ではない。

## 修正と範囲

同じfilesystem上の私有stageへJSONを完全に書き、flush/fsyncして閉じた後、
`os.link` で上書きなしに最終pathへ公開する。競合して最終pathが既にあれば失敗し、元targetを保持する。
通常/例外経路はstageを削除する。SIGKILLでは私有stageが未完了owner内に残り得るが、
それをcheckpointや完了artifactとして読まない。既存の厳密なowner/native構成検査は緩めない。
これはプロセス取消しに対する完全公開で、停電時のdirectory durability保証ではない。

共有 `_write` の直接消費先は所有平面調整、曲線調整、曲線二点/履歴、曲線調整worker。
旧raw平面調整のcheckpoint/失敗報告にも同じ公開処理を接続する。
indent=2/default ASCII escape/allow_nan=Falseと元の末尾改行有無を維持する。
FEM行列、固有値、場、RF、mode identity判定と許容差は変更しない。

## 検証と終端

新独立検査は途中serialization/非有限値/実producer強制終了、完全payload byte、
上書き拒否、旧失敗報告の末尾改行を扱う。加えて元の実worker取消し/移動/再開/管理器再作成を再検査する。
元全実行は2354検査/478モジュール、3200.524秒、2FAIL・5ERROR・3skipで実終了1。
全report/開始時1365源不変を `full-failed-final-audit.json` で確認し、その後に修正を適用した。
共有保存変更のため、限定検査成功後に新rootで全 `scripts/validate.py` を一度実行した。
元FAILは保全し、新全実行のunittest/seed周波数・RF/指紋を別に監査する。
限定45検査66.391秒、実worker取消し/移動/再開/管理器再作成1検査40.442秒は実終了0/PASS。
原失敗testの取消し待機条件/時間は変更していない。
新全validate handle69844は実終了0/PASS。2359検査/479モジュール、3215.343秒、失敗0/エラー0/skip3。
全1366源は開始/終端/現行一致。元5失敗モジュールと保存の全直接消費先は成功した。
seed9モード/207周波数・RF量は別の相対1e-10照合でPASS、最大相対差f=0/RF=8.881784197001248e-16。
3skipの未実施範囲・既存専用実再生証拠・初回metadata監査AssertionErrorと厳密修正は
[P09受入記録](PLANAR_CURVED_TRACKING_TUNING_ACCEPTANCE.md#修正後の全検証seed照合)に記録した。数値gateは不変。
`new-full-terminal.json` / `p09-final-acceptance.json` / `p09-final-card-audit.log` は終端/全条件監査PASS。
rawは `out/p09-checkpoint-publication-20261007`、原FAILは元rootに保全。

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python -m unittest -v test_planar_checkpoint_publication test_browser_session test_curved_hphi_workspace test_model_contract test_project test_hphi_tuning.HphiTuneRequestTests test_planar_tuning
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python -m unittest -v test_planar_piecewise_tuning_jobs.PlanarPiecewiseTuneJobTests.test_actual_cancel_select_prefix_move_resume_and_manager_restart
OPENBLAS_NUM_THREADS=1 UV_CACHE_DIR=/tmp/superfish-ng-uv-cache MPLCONFIGDIR=/tmp/superfish-ng-matplotlib-p09-publication uv run --no-sync python scripts/validate.py --out out/validation-p09-publication-20261007
```

`bounded-acceptance.json` は両logの実終端/45＋1検査と元source archiveを照合した。
保存2源で変更された定義は `_write`/`execute_planar_tune` のみ、他7/9定義はAST同一。
全8変更path/新1test/1365→1366源を `repair-source-delta.json` に記録した。
これらの監査に新FEM/物理再生は加えていない。新外部依存/外部実装/legacyソース再利用なし。
