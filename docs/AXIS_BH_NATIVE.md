# S04: 軸接続P1非線形磁場の保存・失敗再現・CLI

2026-09-13 JST。固定814sourceを主820sourceへ統合し、専用API範囲で限定受入。

[限定計画](AXIS_BH_NATIVE_PLAN.md)の専用成功native、収束失敗native、3 CLIと能力一覧を実装した。CaseにはB-H表/来歴、材料領域、全Jphi、固定a/接線Ht/軸正則境界、求積/Newton設定と明示初期係数を保持する。成功保存はcase.json、mesh.npz、fields.npz、results.json、manifest.jsonの5ファイル。fieldsはa=Aphi/r[T]のみで、全軸DOFを残す。基準や相対係数への変換はしない。

meshには元の頂点/セル/境界/領域/界面/穴/全体積/軸接触、全B-H表とオフセット、疎接線CSR[m⁴/H]、内部gと電流/境界荷重[A m²]を保存する。セルの3頂点のa/Aphi/B/H/接線/表区間/割線/微分係数/半径/エネルギー密度も保持する。頂点標本をセル一定場とは扱わず、任意probeは元P1係数と材料表から再評価する。元6場と片側材料/来歴、JのU/U*、AのH周回、A m²の固定反力、Wbの磁束、q/q+4の診断と全反復履歴を分離する。

再読込は同じCase/求積/設定/初期値で非線形FEMを再実行し、保存係数、決定的履歴、元場と全量の一致を要求する。同じ計算の再検証であり、独立ソルバーの比較ではない。丸めの異なる環境で近い根を自動受理する保証はない。求積差や小さな代数残差を離散化誤差の保証へ変換しない。

失敗保存はcase.json、failure.json、manifest.jsonの3ファイル。failure報告版2はcoefficient_field=aphi_over_r_tとlast_valid_coefficientsを明示する。外側の失敗manifestは版1で、能力一覧に両者の版を別々に示す。読込時に再試行して理由・履歴・最後の有効係数を照合し、成功するCaseを失敗保存として発行しない。solve-axis-bh/replay-axis-bhは成功0、収束失敗1、入力/保存検証エラー2。probe-axis-bhは失敗nativeを拒否する。無効Caseから失敗nativeを作らない。Project/GUI/Studyは未接続。

追加6unitは初回38.309秒でPASS。成功8例、係数/表/元頂点場/接線/荷重/軸DOF/体積/求積/履歴/来歴/単位のハッシュ再計算後の改変拒否、版2失敗3種類と最後の状態/係数名改変拒否を確認した。シンボリックリンク、途中出力、読込中の変更、保存中断、上書きも拒否する。完了manifestは最後に発行する。既存能力一覧3unitとCLI 6回の初期確認も合格。

解析検証済み成功24例と期待失敗8例の独立API/CLI比較は217.580秒でPASS。一様/軸方向二材料8、単一区間電流4、径方向二材料4、折点電流4、旧線形2、零場2を含む。成功48保存の各5ファイルと失敗16保存の各3ファイルがバイト一致し、元6場を含むprobe全JSONと履歴も一致した。軸probeのAphi/Br/Hrは厳密にゼロ。99 CLIで終了0/1/2、失敗probe、無効P2/bool入力、上書き拒否を確認した。288 nativeファイルと98参照ファイルは不変。参照は失敗版2の固定811sourceによる独立96条件で、元の物理解法・解析源を変更していない。

証拠はout/axis-bh-native-independent-trial-20260913/report.json。固定814sourceの標準1294件はout/validation-axis-bh-native-candidate-20260913へ終了0。固定候補は不変。新規依存・追加外部資料・旧版実行なし。合成材料のみ。軸非接続非線形は[後続工程](OFF_AXIS_BH_FORMS_PLAN.md)、対象版モデルとS04、全計画は未完。

標準2598.790秒、1291合格・任意NGSolve参照2件/HTTP環境1件skip、ResourceWarningなし。主6unitは39.211秒でPASS。標準/独立の固定814sourceと主820source（不変egg-info 6件）は完全一致。独立全例を主で再実行したとは扱わない。旧ベンチマーク・許容差不変。統合証拠は標準出力内seed_regression.json。
