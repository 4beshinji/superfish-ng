# 平面区分写像の元場比較・追跡・所有再生 — P04-a

2026-10-02、P03基準 `eb1f4f3` からの追加。P04-aを受入。
親P04はIN_PROGRESSで、形状法則/調整はP04-b、GUI操作と統合監査はP04-cに残る。

## 入力と数学契約

[P03の連続区分アフィン宣言](PLANAR_PIECEWISE_MAPPING.md)を追跡要求/結果版9へ接続した。
`PlanarTrackingRequest(..., mapping=PlanarPiecewiseMapping(...))` を使用する。
旧版1〜8の正常入力/数値/保存意味を維持する。新版と旧写像名の混用、未知版・型は拒否する。
元の明示多角形Case・TE/TM・ピークphasor・U′[J/m]を保持し、異なる偏極を混ぜない。

`planar_piecewise_overlap.planar_piecewise_overlay` は以下を有理数で実施する。

1. 両側の全境界と、比較/native分割の全域一致をP03と厳密アフィン恒等overlayで確認する。
2. 前側nativeセルと前側比較セルを交差し、各交差片を対応する現側比較セルへ厳密に写す。
3. その片と現側nativeセルを交差し、前側の厳密逆写像で元セルへ戻す。
4. 全nativeセルと全比較セルの面積を両側別々に厳密確認する。欠落/二重計上は停止する。
5. 各元FEMセル番号と重心座標、前側物理xy座標/面積を最後にbinary64へ変換する。

戻り値は `PlanarPiecewiseOverlay`。`overlay` は既存 `PlanarTrackingOverlay`、
`mapping_cells` は交差三角形ごとの比較セル、`current_to_previous_linear` はそのセルのadj(A)。
配列は読み取り専用。現側TE横Eはadj(A)で前側へ移送し、TM縦Ezはscalarの合成で評価する。
積分測度は前側の実xy面積[m²]であり、正逆で各自の前側面積を用いる。
元場の再補間、解析周波数での置換、新たな固有場の生成は行わない。

候補BVHは全て有理数のAABBを使う。`max_candidate_tests` は各探索に個別適用する。
両側の領域検査・中間分割・最終分割を `max_overlay_triangles` で制限し、上限超過は停止する。
最終変換で非有限・非零の0への丸め・面積の非正値が生じれば拒否する。

場Gramを求積次数3/5で独立比較し、各元領域の面積scaleを使う有限細分スペクトル診断、
上側guard、ID集合継承、個別ID判断を通す。guardへ達する集合はUNVERIFIEDのまま保持する。
対応PASSは連続枝の証明、固有値の一般変形則、表面場や連続問題の誤差上界ではない。

## 所有保存と直接消費先

`planar_tracking_jobs._prepare` へ新版の領域/共同分割事前検査を接続した。
不正な写像/予算/型は出力作成前に拒否する。既存所有pair・履歴・CLI-workerは新版宣言と
全元nativeを保存し、元場と有限スペクトルから結果全体を再計算する。
元データ移動後も所有コピーから再生でき、結果にhashを作り直した改変も拒否する。
追跡/履歴の外側保存版やJob種別を新しく増やさず、内側の比較要求/結果版9で区別する。

着手基準の版8以前はP03宣言を受け付けない。隔離した基準モジュールで拒否を再現し、
`out/p04a-planar-piecewise-20261002/baseline-rejection.json` に保存した。
これは新API欠如の確認であり、旧FEMが誤った数値を計算したという反例ではない。

## 条件別検証

| 条件 | 独立証拠と結果 |
| --- | --- |
| 全元セル/比較セル被覆 | 非アフィン伸長の正逆、独立3×4/5×3分割、三尺度、各元セル面積とxy再構成。PASS |
| 元P1/P2場積分 | h=1+x+y/4のTM scalar積分131/48、TE curl積分(17/16)/(ωε0)²。両方向次数P1/P2と次数3/5。PASS。製造多項式を固有場とは扱わない |
| 相似極限f/場/U′/RF | 実12×12/16×16 TE/TM、解析遮断周波数、E Gramの尺度則と位相反転、両エネルギー各0.5 J/m、解析G、両R/Q N/A、元全RF/係数不変。PASS |
| 既存厳密アフィン極限 | 既存現側測度と新前側測度の面積比4を別計算し、全Gram一致。PASS |
| 実非アフィン追跡と細分 | 右半分だけ伸長する写像、実TE/TMの独立4/6と8/10メッシュ、解析矩形周波数と細分差、全元RF/係数不変。PASS |
| guard/不完全分割/厳密入力 | 正方形TE縮退がguardへ達してUNVERIFIED、ID null。交差片欠落・予算超過・新版/旧名混用を拒否。PASS |
| 所有pair/履歴/CLI | 全元native byte一致、元削除/移動後の完全再生、CLI結果一致、再hashした比較セル改変拒否。PASS |
| 実worker | 実中止、正常新版job、管理器再起動後complete再検証、元native不変。全子プロセス回収。PASS |
| 独立元物理 | 既存の符号付きMaxwell全成分、単位長の解析G/壁積分・尺度則の専用2ケース。PASS |
| 旧直接消費先 | アフィン/矩形追跡、縮退/guard、所有job・履歴、旧worker/CLIと改変拒否。PASS |

## 実行記録と失敗

証拠ディレクトリは `out/p04a-planar-piecewise-20261002/`。
最終の主選択実行は183.030秒・55件中54PASS/1収集ERROR、終了1。
ERRORは指定した旧アフィンのメソッド名が存在しなかったためで、製品不合格ではない。
正しい既存strictケース1件を別実行し0.001秒PASS/終了0。
独立元場/RFの2ケースは0.048秒PASS/終了0。
合計57件の成功を分割証拠で保持し、単一の57件全PASS実行とは呼ばない。

共通prefix:

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-ng-uv-cache \
uv run --no-sync python -m unittest -v
```

主実行の対象は次の通り（実行ログ `selected-tests.log` に全結果）。

```text
test_planar_piecewise_mapping test_planar_piecewise_tracking
test_planar_tracking_exact_affine test_planar_tracking_overlap test_planar_tracking
test_planar_tracking_exact_mapping test_planar_tracking_jobs test_planar_tracking_history
test_planar_tracking_history_saved.PlanarHistorySavedTests.test_owned_copy_extension_and_portable_replay
test_planar_tracking_history_saved.PlanarHistorySavedTests.test_rehashed_summary_and_kind_downgrade_rejected
test_planar_affine_shape_mapping.PlanarAffineShapeMappingTests.test_strict_affine_shape_mapping
```

最後の存在しない指定は失敗の正確な記録として保持する。
正しい指定は `test_planar_affine_shape_mapping.PlanarAffineShapeMappingTests.test_strict_new_request_units_arrays_and_bounds_before_trial`
（`affine-strict.log`）。追加物理検査は `test_planar_rf.PlanarRFTests.test_signed_maxwell_fields_and_all_complex_components`
と `test_planar_rf.PlanarRFTests.test_per_length_energy_wall_integral_and_scaling`
（`independent-native-fields-rf.log`）。

開発中の失敗も区別する。初回はテストの `planar_result` import先誤りで収集ERROR。
修正後、新4件中3PASS/1FAIL（8.121秒）：粗い6×6/8×8のG相対差0.05827が許容差0.03を超えた。
許容差を維持して12×12/16×16に細分し、該当1件は28.512秒PASS。
追加3件の初回は2PASS/1ERROR（12.214秒）：native保存にjob用snapshot helperを適用したテスト誤り。
native全bytes比較へ修正し、主選択実行で全新7件を確認した。製品物理閾値は変更していない。

主選択実行のsession39306は終了1まで回収し、別実行は全て終了0。
`implementation-start.json` と終了時 `implementation-audit.json` で391製品ファイル不変。
Python 3.12.3 / NumPy 2.5.2 / SciPy 1.18.1、既存.venvをuv `--no-sync` で使用。
全validate/全unittest、seed、GUI、Hosted CI、新Wine比較は未実行。
範囲は専用平面比較と直接消費先に限定でき、canonical TM seed核を変更していない。

来歴：既存自作の有理数clip/BVH・元場Gram・有限スペクトル・所有保存を再利用した。
新外部資料・依存・legacyソース/バイナリ参照はない。
次はP04-bで元形状から各試行を生成し、実調整/最終細分/保存再開へ接続する。
