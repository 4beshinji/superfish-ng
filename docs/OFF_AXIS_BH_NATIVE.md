# S04: 軸非接続P1非線形磁場の保存・失敗再現・CLI

2026-09-13 JST。固定826sourceを主832sourceへ統合し、専用API範囲で限定受入。

[限定計画](OFF_AXIS_BH_NATIVE_PLAN.md)の成功5ファイル・版2失敗3ファイルとCLI/能力一覧を実装した。成功のCase/mesh/fields/results/manifestには、全B-H表/来歴、領域/穴/全体積、元相対/絶対psiと基準、疎接線CSR[1/H]、g/電流/境界荷重[A]、全反復履歴とq/q+4差/高次数自由残差を保持する。セル頂点の元psi/Aphi/B/H/接線などは診断標本であり、1/r場を一定場へ置き換えない。任意probeは元係数と表から6場を再評価する。

同じCase/求積/初期値で非線形FEMを再実行し、保存係数/基準・全材料/元場/接線/荷重・決定的履歴/各量の一致を要求する。独立ソルバーでの再現や、丸めの異なる別環境の近い根の自動受理とは扱わない。失敗は版2のcoefficient_field=psi_relative_to_reference_wb、last_valid_coefficientsまたはnullと全履歴を保持し、再試行で同じ失敗であることを照合する。外側manifestは版1で、失敗報告の版とは別に能力一覧へ示す。

solve-off-axis-bh/replay-off-axis-bhは成功0、収束失敗1、入力/native検証エラー2。probe-off-axis-bhは元6場と片側来歴/表区間を返し、失敗nativeを拒否する。無効Caseから失敗nativeを発行しない。Project/GUI/Studyは未接続。

追加6unitは初回86.634秒でPASS。成功8例、基準/相対/絶対psi・表・元頂点場・接線/荷重・体積・求積/履歴/来歴/単位の再ハッシュ改変拒否、3種類の失敗と理由/履歴/係数名/最後の状態の改変拒否を確認した。リンク、途中出力、検証中変更、保存中断、上書きを拒否し、完了manifestは最後に発行する。既存能力一覧3unitも6.452秒でPASS。6 CLIの初期比較で成功5ファイル/失敗3ファイルとprobe全JSONがAPIと一致し、終了0/1/2も確認した。

固定826sourceの標準1311件はout/validation-off-axis-bh-native-candidate-20260913へ終了0。固定823sourceの解法96条件を参照した独立成功24/失敗8のAPI/CLI比較は325.787秒でPASS。固定候補は編集しない。新規依存・追加外部資料・旧版実行なし。合成材料のみ。対象版モデルとS04、全計画は未完。

独立比較は1/r径方向場12、二材料4、電流4、旧線形2、零場2を選び、48成功/16失敗nativeと99 CLIを照合した。成功5ファイル/失敗3ファイルとprobe全JSON、元6場/材料来歴/履歴が一致した。288 native/98参照ファイルは不変。失敗probe・無効P2/bool入力・上書きを終了2で拒否した。証拠はout/off-axis-bh-native-independent-trial-20260913/report.json。

標準2811.777秒、1308合格・任意NGSolve参照2件/HTTP環境1件skip、ResourceWarningなし。主6unitは86.424秒でPASS。標準/独立の固定826sourceと主832source（不変egg-info 6件）は完全一致。独立全例を主で再実行したとは扱わない。旧ベンチマーク・許容差不変。統合証拠は標準出力内seed_regression.json。
