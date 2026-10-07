# N06：元FEM・全参照・停止確認を新プロセスへ接続

2026-10-08 JST。N06の実装部分を限定受入し、固定12実測へ進む。
受入条件は、[N05](N05_ADAPTIVE_EFFICIENCY_PLAN.md)の同じ初期Case/source、独立物理精度と費用、
別々の誤差対DOF/時間、前処理の対称な計測、未達/上限の保全である。
この段階では12実測は0、N06はIN_PROGRESS、全goalは継続する。

`adaptive_efficiency_reference.py` は共有packageと入力SHAを確認する。
円筒/球は元数学から全Gauss16/24配列・RF量を独立再生成して完全一致を要求する。
丸めは元三h/五参照mode、元matrix三個別ID、全Case/sourceと初期native byteを保持する。
実読込で1511入力、全76736点、target/guard-2/guard-3を確認した。新FEMは0。

`adaptive_efficiency_worker.py` は元solve、保存reader、残差/mark/適合細分、実nested追跡、
全P2域検査、求積増次数と離散peak区間を呼ぶ。元科学kernelは変更しない。
41個の明示呼出しaliasを観測し、inline処理はsolveのexclusive残部へ残す。
両次数の全native modeを全供給点で評価し、E/H/軸・周波数・両R/Q・G・peak両端の九gateを個別保存する。
面積/回転体積2e-12、rank Ritz1e-10は元N03条件を保持する。
元RF停止判断を別保存し、独立参照/場が未達なら予算内で元uniform restrictionを続ける。
成功には独立九gate、実ID/域/求積と最後の二つのuniform区間のRF/peak/元場差を全て要求する。
最初の精度到達と確認済み到達を区別し、physical_error_boundはnull。

native経路累積時間はmesh/native水準/次細分のroot inclusive区間を一度だけ加算する。
参照lookup・rootの子区間を重ねて加えない。記録器prefix、Linux共有monotonic originからの
起動/import込みprefix、supervisor全プロセス時間/RSSを別量として残す。
欠測originはnull。元例外は同じobjectで伝播し、失敗費用/先行artifactを保存する。

`scripts/validate_adaptive_efficiency.py` は固定12行を元順序で直列にfresh processへ渡す。
各3600秒/32GiB・BLAS1を保ち、実行間のnative再利用はない。
起動前/終端の全対象source SHA、環境/commit、要求/bindings SHA、共有準備費用を保存する。
終了0だけでは科学成功にせず、上限/失敗/途中checkpointを残す。
二反復双方が同じ目標と二uniform区間を確認した場合だけ範囲付き費用を比較する。
CSVと九量を分けたDOF/時間図を保存し、Matplotlibは既存の任意依存を使う。

## 選択検査と来歴

新15個別unitを分割受入（worker9、validator6）、N06計74個別unit。
実球adaptive二水準・実円筒adaptive二水準を元 `_assemble` で再生し、指標/選択/実ID/RF/peak等の完全一致を確認した。
実円筒uniform三水準の独立全場誤差低下、元source/域/Ritz/全modeと九gateを確認した。
参照vetoは明示したadversarial controlで、実精度/benchmark証拠へ数えない。
uniform五水準とadaptive六水準で、元RF停止を独立参照成功へ置き換えず継続することを確認した。
runner六検査のprocess stand-inも制御契約だけの証拠である。

raw：`out/n06-cost-recording-20261007/worker-*.log`、`validator-*.log`、`worker-validator-acceptance.json`。
最初のworker五検査10.946秒は四PASS/一ERROR。MagicMockの属性が二重wrap検査に掛かったため、
検査doubleをplain functionへ訂正した。追加二検査9.176秒PASS。
費用metadata追加後、関係三検査2.956秒PASS。
runner/affine七検査2.778秒は六PASS/一FAIL（検査の元refinement名の誤記）。
元名 `residual` へ訂正し、adaptive継続を含む三検査9.230秒PASS。
CSV readerの未close警告も訂正して確認した。図/出力追加後、runner直列契約一検査0.348秒PASS。
receipt初回parserはtest行途中へ出る進捗logを読み落とした。再検査せずparserだけ訂正して15個別PASS集合を確認した。

主uv/BLAS1/`PYTHONPATH=src:tests`、standard unittest。
開発新FEM23回、N06累計46回。元1425対象源は全byte不変、新1430対象/1223 Python源。
新seed/full/legacyは0。N03 fullの1405源の証拠を追加源へ昇格しない。
次は下記で実測し、実測中はsrc/tests/scripts/examplesを固定する。

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests MPLCONFIGDIR=/tmp/superfish-ng-matplotlib \
UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python scripts/validate_adaptive_efficiency.py \
  --analytic-reference-manifest out/n06-cost-recording-20261007/analytic-reference-grids/manifest.json \
  --rounded-reference-manifest out/n06-cost-recording-20261007/rounded-reference-grid/manifest.json \
  --rounded-matrix out/n03-native-surface-series-20261007/explicit-resource-matrices/N01-rounded-two-lobe/matrix.json \
  --out out/validation-n06-efficiency-20261008
```
