# N04 曲線の追跡付き適応計算・五量停止・保存再開

[検証済み先祖の実行内再利用](CURVED_VERIFICATION_REUSE.md)を追加した。独立read/replayは全水準を再検証し、保存形式・五量停止条件は維持する。

[一様細分との対照](CURVED_REFINEMENT_EFFICIENCY.md)を追加した。球形例では両者とも五量を確認したが、適応側の効率優位は得られなかった。

2026-09-09、直前基準ba36a86。
要求版4は[曲線残差指標](CURVED_RESIDUAL_INDICATOR.md)、[native局所履歴](CURVED_REFINEMENT_HISTORY.md)、
[親子質量内積追跡](NESTED_CURVED_TRACKING.md)を適応計算へ接続する。
周波数・R/Q・Gと連続離散ピーク比を個別判定し、最後に全域細分を2回要求する。
直線版1/2/3の入力・保存形式・判定は維持する。

## 対象と入力

nativeのgeometry_order=2/element_order=2の真空・軸接続m=0 TMを対象とする。
版4の表面停止は、閉じたPEC/axis輪郭で、元解析曲線の接続と軸極が既存の
SMOOTH_WITHIN_TOLERANCE基準を満たす場合に限る。曲線近似が厳密な滑らかさを持つという証明ではない。
再入角・未確認の接続は版4で明示的に拒否する。単一対称半領域は[鏡映後の表面前提](CURVED_ADAPTIVE_SYMMETRY.md)を確認できる場合に対応する。
従来の全域levelsを持つ初期Caseも扱い、その後はuniform/markedの順序付き履歴を保存する。
細分中に元弦メッシュ・元幾何・RF設定は変更しない。

要求の共通キーはcase、initial_mesh（nullまたは明示した元弦メッシュ）、initial_ids、mode_id、
controls、bulk_fraction、max_levels、max_triangles、relative_tolerances。
版4ではschema_version=4と次の指定を使う。

- controls.mappingはnested_curved。重なり、割当余裕、クラスタ差、最小相対特異値を明示する。
- confirmationはuniform_two_steps。
- surface_relative_tolerancesはepk_over_eaccとbpk_over_eacc_mt_per_mv_per_m。
- minimum_corner_angle_degは曲線写像の頂点接線角の下限。直線版のminimum_angle_degは受け付けない。
- quadrature_check_orderはCaseのquadrature_orderより大きい整数で32以下。
- quadrature_relative_toleranceは高次積分との比較の正の許容値。

max_levelsは5以上。全要素数上限は要求とCaseの上限の小さい方。
元弦メッシュの生成制御と曲線写像の頂点接線角は異なる尺度として検査する。
品質/予算未達時に閾値を下げたり、別方式の細分へ置き換えたりしない。
初期幾何・予算・品質に問題がある場合は出力先やジョブを予約する前に拒否する。

## 判定と積分確認

各水準のnative場を再検証し、全モードの個別IDが確認できる場合だけ対象mode_idの場を選ぶ。
順位だけを前の水準から引き継がない。縮退群や不確かな対応はUNVERIFIEDで停止する。
対象場の要素内・内部辺・自然境界残差からbulk_fractionを満たす要素を選択し、適合性のための隣接分割も行う。

積分誤差をメッシュ変化と混同しないため、Caseの積分次数と指定した高次積分で次を比較する。

- 各残差成分のL1差を、高次積分の全指標二乗で規格化した値。
- 同じ対象場のRayleigh商から得た周波数の相対変化。
- 同じ対象場の質量形式の相対変化。

全てquadrature_relative_tolerance以下であることを要求する。未達はQUADRATURE_UNVERIFIEDで停止し、
表面状態もUNVERIFIEDとする。積分比較を物理誤差上界や全固有対の高次解法による認証とは扱わない。

周波数・R/Q・Gは直近2区間の相対差を別々に判定する。
表面量は連続離散E/Hピークの上下界からEpk/EaccとBpk/Eaccの区間を作り、
区間内の最悪相対変化を比較する。推定値同士の一致で区間幅を隠さない。
加速電場の規格化が未確認の場合はQUANTITY_UNVERIFIEDとする。
RF量が候補条件を満たしたら全域細分へ移り、その後は全域細分を継続する。
五量が直近2区間で基準を満たし、最後の2水準が全域確認である場合だけTARGETS_METとする。

TARGETS_METは固定された二次幾何に対する経験的な細分確認である。
元解析曲線への幾何近似誤差、物理誤差上界、一般形状での精度・効率を保証しない。
physical_error_boundは常にnull。

## 実行と保存再開

[球形の要求例](../examples/adaptive_refinement/curved_sphere_confirmed.json)を用意した。独立検証では別途定義した解析基準と照合する。
APIは既存のexecute_adaptive_refinement/requestとreplay_adaptive_refinementを使用する。
版4を曲線用エンジンへ分岐する。JobManager.start_adaptive_refinementも同じ要求を受け取る。

```sh
OPENBLAS_NUM_THREADS=1 .venv/bin/python -m superfish_ng adaptive-refine request.json \
  --out out/curved-first --max-new-levels 3
OPENBLAS_NUM_THREADS=1 .venv/bin/python -m superfish_ng resume-adaptive-refinement \
  out/curved-first/checkpoint-003.json --out out/curved-rest
OPENBLAS_NUM_THREADS=1 .venv/bin/python -m superfish_ng replay-adaptive-refinement \
  out/curved-rest/checkpoint-005.json
```

最後のファイル名は実際の水準数に合わせる。出力先は毎回新規ディレクトリ。
各水準にnative Case・元弦メッシュ・局所履歴・場/RFを保存し、チェックポイントに
元ファイルhash、追跡、残差指標、曲線品質、高次積分比較、ピーク区間、停止判断を保存する。
再開できるのは検証済みPAUSEDだけ。要求の変更や過去の場・判断の改変は拒否する。
max_new_levelsは再開後に追加する計算数の上限で、過去の水準を再計算しない。
再検証は固有値を解き直さず、幾何・行列・RF・履歴・追跡・各判断を確認する。

LEVEL_LIMIT、REFINEMENT_LIMIT、TRACKING_BUDGET、ZERO_INDICATORを合格として扱わない。
実行中の失敗は直前のチェックポイントとfailure記録を残し、既存出力を上書きしない。
[GUIの版4入力・表示・保存再開](GUI_CURVED_ADAPTIVE_REFINEMENT.md)も接続した。[番号指定による履歴編集](GUI_CURVED_REFINEMENT_HISTORY.md)と[履歴を保持する固定形状Study](CURVED_HISTORY_STUDY.md)も接続した。図上の要素選択は残る。

## 実行証拠

着手前642件中640合格・2 skip（407.376秒）。修正後の追加5検査PASS（219.397秒）。
初回の検査API呼出し誤り、行列共用の完全一致確認、単体fixtureの分離は[引継ぎ](CODEX_HANDOFF.md)に記録した。

独立検証の初回out/curved-adaptive-initial-20260909はPASS。
尺度1/2とも球形の実FEMが36→58→81→324→1296要素、5水準でTARGETS_MET。
尺度1はCLIで3水準まで保存→別出力先へ再開。尺度2はAPI実行で、両者とも保存再検証中の固有値計算を禁止した。
f=1e-4、RQ/G=.005、E/Bピーク比=.01の独立解析基準を、ピーク区間の両端点を含めて満たした。
両尺度の最大解析差はf=2.473e-5、RQ=3.152e-5、G=1.591e-7、Epk/Eacc=2.707e-4、Bpk/Eacc=2.055e-5。
五量相似則差最大5.685e-14、高次積分比較差最大2.874e-14。最後の全域確認2回と全個別IDを保持した。
最終周波数変化は約2.009e-7でも球形解析差は約2.473e-5で、固定二次幾何の細分差を全物理誤差上界にできない。

旧保存互換性out/curved-adaptive-old-replay-20260909もPASS。実保存の版1/2/3チェックポイントを再検証し、
全判断・状態を含む文書が完全一致。版1/2のsurface_status=UNASSESSED、版3のTARGETS_METを維持した。
独立・旧保存検証中のソース変更なし、記録hashは最終ソースに一致する。


最終標準検証 out/validation-curved-adaptive-20260909 は647件中645合格・2 skip（629.257秒）、PASS。
benchmarks/validationの全9モード・19量で周波数差ゼロ、RF/エネルギー差最大8.882e-16。
標準・独立球形・旧保存互換性の記録hashは最終ソースに一致し、検証中のソース変更なし。

