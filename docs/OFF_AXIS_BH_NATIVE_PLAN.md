# S04: 軸非接続P1非線形磁場の保存・失敗再現・CLI

2026-09-13 JST。後続限定課題。未実装・未受入。

成功nativeはCase/mesh/fields/results/manifestの5ファイルを保持する。全B-H表/来歴、領域/穴/全体積、元の相対/絶対psiと基準、元セル頂点の診断標本、g/接線/電流/境界荷重、求積比較と全Newton履歴を同じ非線形FEMで再検証する。元の1/r場と非線形Hを頂点標本の一定場へ置き換えない。

失敗nativeはCase/failure/manifestの3ファイルとし、版2のcoefficient_field=psi_relative_to_reference_wb、last_valid_coefficientsまたはnull、採用/棄却履歴を保持する。平面版1と軸接続版2の意味を維持し、再試行が同じ失敗であることを照合する。成功読込/probeは失敗nativeを拒否する。

solve-off-axis-bh/replay-off-axis-bh/probe-off-axis-bhと能力一覧を接続する。終了状態は成功0、収束失敗1、無効入力/native検証エラー2。無効Caseから失敗nativeを発行しない。Case・表・係数・基準・元場・接線/荷重・求積/履歴の再ハッシュ改変、リンク、途中出力、読込中変更、保存中断、上書きを拒否する。

解析検証済み成功24例と期待失敗8例をAPI/CLIで保存・読込・元6場probeし、成功5ファイル/失敗3ファイルとprobe全JSON、全履歴の一致と元ファイル不変を確認する。標準と既存周波数/RF差を確認して専用API範囲で限定受入する。Project/GUI/Studyとの接続はこの限定課題に含まない。
