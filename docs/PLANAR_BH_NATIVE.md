# S04: 平面P1非線形磁場の保存・失敗再現・CLI

2026-09-13 JST。固定802sourceを主808sourceへ統合し、専用API範囲で限定受入。

[限定計画](PLANAR_BH_NATIVE_PLAN.md)の成功native、収束失敗native、3 CLIと能力一覧を実装した。CaseにはB-H表/来歴・材料領域・全Jz/Az/Ht・Newton設定・明示初期係数を保持する。成功保存はcase.json、mesh.npz、fields.npz、results.json、manifest.jsonの5ファイル。相対/絶対Azと基準、元セルB/H/接線と表区間/割線/微分磁気抵抗率、疎接線CSR、内部g・電流/境界荷重、領域/界面/DOFを保持する。U/U*、元H周回/反力、元B磁束、採用/棄却を含む全反復履歴を同じ非線形FEMで再検証する。

再読込は同じCase/設定/初期値を再求解し、保存係数と決定的な履歴の一致を要求する。非線形K@Aを内部gへ代用しない。独立ソルバーでの再現ではなく、同じ数値計算の検証である。表/場/接線/荷重・履歴と各量が同時に一致することを確認する。丸めの異なる別環境の近い根をこの形式で自動受理するとは保証しない。

収束失敗は別のcase.json、failure.json、manifest.jsonの3ファイル。理由・Case/設定・全履歴・最後の有効係数またはnullを保存する。失敗読込でも再試行して同じ失敗であることを照合する。成功read/probeでは受け取らない。solve-planar-bhとreplay-planar-bhは成功0、収束失敗1、入力/保存検証エラー2を返す。無効Caseでは収束失敗nativeを作らない。probe-planar-bhは元5場と片側材料の来歴・表区間を返す。Project/GUI/Studyは未接続。

追加6unitは初回2.608秒でPASS。成功7例の保存/再読込、ハッシュ再計算後の係数/表/元場/接線/荷重/履歴/来歴/単位等の改変拒否、反復上限・材料範囲・無効初期場の失敗保持、失敗の履歴/最後の状態改変拒否、シンボリックリンク/途中出力/検証中の変更/保存中断の拒否を確認した。完了manifestは最後に発行し、既存ディレクトリやprobeを上書きしない。既存能力一覧の3unitもPASS。

解析検証済み成功24例と期待失敗8例の独立API/CLI比較は30.710秒でPASS。成功48保存の各5ファイルと失敗16保存の各3ファイルがバイト一致し、probe全JSONも一致。99 CLIを実行し、終了0/1/2の区別、失敗probe/無効P2/bool入力/上書きの拒否を確認した。元の物理解法・独立解析源は変更せず、成功の各積分量/反復履歴と失敗履歴が96条件の既検証記録に一致する。288 nativeファイルと98参照ファイルは不変。

証拠はout/planar-bh-native-independent-trial-20260913/report.json。標準1277件をout/validation-planar-bh-native-candidate-20260913へ終了0。固定候補は不変。新規依存・追加外部資料・旧版実行なし。軸対称非線形・対象版モデル、S04と全計画は未完。

標準2604.034秒、1274合格・任意NGSolve参照2件/HTTP環境1件skip、ResourceWarningなし。主6unitは2.599秒でPASS。標準/独立の固定802sourceと主808source（不変egg-info 6件）は完全一致。独立全例を主で再実行したとは扱わない。旧ベンチマーク・許容差不変。統合証拠は標準出力内seed_regression.json。
