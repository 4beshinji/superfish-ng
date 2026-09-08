# 版3: 連続離散ピーク比を含む適応停止

2026-09-08、直前基準7645883。N04の限定実装。
`adaptive-refine` / `resume-adaptive-refinement` / `replay-adaptive-refinement` と
`execute_adaptive_refinement`、JobManagerで利用する。新しい依存や外部サービスはない。

## 入力と対象

[版2](ADAPTIVE_REFINEMENT.md)の入力を `schema_version: 3` とし、必須の
`surface_relative_tolerances` に `epk_over_eacc` と
`bpk_over_eacc_mt_per_mv_per_m` の正の有限な相対閾値を指定する。
`relative_tolerances` は従来どおり f・accelerator R/Q・G の3量。
`confirmation: uniform_two_steps`、`controls.mapping: nested_affine` を明示する。
Caseのschema_versionとは別の版であり、チェックポイント外側のschema_versionは1を維持する。

対象は直線P1/P2、元の正確な多角形と確認済み境界接続に限る。
元輪郭の[角診断](AFFINE_SURFACE_CONVERGENCE.md)が `NO_REENTRANT_CORNERS` でなければ、
出力ディレクトリ/管理ジョブを作る前に拒否する。再入角・未確認接続・曲線の弦近似は
版2と独立の表面診断で調査できる。角診断の通過は物理的正則性の証明ではない。

```bash
OPENBLAS_NUM_THREADS=1 python -m superfish_ng adaptive-refine \
  examples/adaptive_refinement/pillbox_surface_confirmed.json \
  --out out/surface-stop-new --max-new-levels 4
OPENBLAS_NUM_THREADS=1 python -m superfish_ng resume-adaptive-refinement \
  out/surface-stop-new/checkpoint-004.json --out out/surface-stop-resumed-new
```

例のRF閾値は操作確認用であり、一般物理精度の基準ではない。
独立検証では f=1e-4、R/Q・G=0.005、両ピーク比=0.01を使う。

## 判定と保存

各水準で追跡対象IDの実FEM場から[直線連続離散極値](AFFINE_SURFACE_EXTREMA.md)を囲い込み、
電場をEaccで、磁場をμ0×10^9/Eaccで規格化する。ピーク探索は既存の
relative_tolerance=1e-6、max_boxes_per_edge=10000を使い、失敗時は計算失敗として保存する。
離散極値の探索幅と水準間の収束閾値を混同しない。

正の上下界について、前水準[a,b]と現水準[c,d]の最悪相対変化
`max(abs(d/a - 1), abs(c/b - 1))` を外向き丸めで評価する。
上限値同士だけの差やピーク標本だけで合格させない。
Eaccが有意でない場合や正の有限区間を確認できない場合は `QUANTITY_UNVERIFIED`。
RF量の直近2差が条件を満たすと、ピーク差の未達時にも全域細分へ進む。
以後は全域細分を続け、最後の2回が全域細分で、両区間の5量すべてが条件内の場合だけ
`TARGETS_MET` とする。予算・品質・追跡上限の停止を達成へ置き換えない。

版3だけが各levelの `surface` に区間・離散ピーク証拠・元多角形診断を保存する。
`decision.changes` は従来のRF3量、`decision.surface_changes` はピーク2量の上界・閾値・判定。
`surface_status` は複合停止の達成時 `TARGETS_MET`、量/ID未確認時 `UNVERIFIED`、
途中や上限停止時 `NOT_CONFIRMED`。単独のピーク合格フラグではない。
`physical_error_bound: null` は維持する。

再開は先祖の全native出力、追跡、区間、停止判断を再計算してから新水準だけを解く。
変更された区間・状態・入力・元場は拒否する。版1/版2の保存形式と判断は変更しない。
別途の直線表面評価APIは版3にも使え、固定N03閾値を独立に評価するため、
利用者が版3で指定した閾値と異なれば状態が異なることがある。

## GUIと残件

[版3 GUI](GUI_ADAPTIVE_SURFACE_STOPPING.md)へ接続済み。ピーク比閾値の入力・五量の判定/上下界表示・保存再開を使える。版1/版2の表面未評価表示は維持する。
通常RF表示への統合、一般形状の精度/効率、曲線局所細分、物理誤差上界は未受入。
N03/N04の親課題全体を完了としない。

## 数値実装時（9cee5a4）の検証

着手前613件中611合格・2 skip（327.193秒）。RF一定でピークだけが変化する反例は
変更前に誤ってTARGETS_METとなることを確認した。変更後、ピーク変化・区間幅・確認回数を
別々に検査し、未達なら実際の全域メッシュ細分を継続する。
実P2対象順位2の4水準から1水準だけの再開、区間/元場改変拒否、CLI再検証、
JobManagerの部分実行・再開・状態検証、GUIの版3明示拒否を確認する。
初回追加テストの管理器終了順序だけを修正した（結果削除前にclose）。数値閾値は変えていない。

独立検証入口は `scripts/validate_adaptive_surface_stopping.py --out NEW`。
円筒P1/P2×尺度1/2の実適応計算を行い、5量の各区間端点を解析解と比較し、
fの逆長さ則と規格化RF/ピーク比の相似不変性を検査する。
全5量・2回の全域確認を両次数で必須とする。上限停止を検証合格にしない。

独立初回 `out/n04-surface-stop-initial-20260908/validation.json` はPASS。
P1は10水準（最後2回が全域細分）、79168要素・39817自由度。
尺度1/2の最悪解析端点差は f=7.005e-8、R/Q=3.916e-4、G=2.819e-7、
Epk/Eacc=1.802e-4、Bpk/Eacc=1.955e-4。
P2は5水準、1872要素・3853自由度。同じ順で6.953e-10、1.674e-6、2.756e-9、4.403e-7、5.350e-7。
いずれも停止状態/独立表面判定がTARGETS_MET、相似則の最大相対差8.269e-13。
前回のP1は8水準予算で全域確認待ちだったが、今回は予算を10水準へ増やして確認を完了した。
f/RF/ピーク比の許容値は変更していない。高いP1計算量は残り、一般効率の受入ではない。
独立検証中のソース変更なし、記録hashと最終ソースが一致する。

最終標準検証 `out/validation-n04-surface-stop-20260908` は617件中615合格・2 skip（354.760秒）、PASS。
benchmarks/validationの全9モード・19量に対する周波数差はゼロ、RF/エネルギー差最大8.882e-16。
固有値/RF核の変更はない。標準・独立検証のsource hashは最終コードに一致。
追加実装後の実ブラウザー検査やHosted CI/Wine比較を行ったという主張はしない。
