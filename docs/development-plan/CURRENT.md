# 現行の作業入口

更新：2026-09-22、P02-d調整フォーム接続中。直前の成果コミットはP02-c `7c84a4f`。
原90カードと追加子カードを含む[全115カード](tasks.tsv)の計画は継続中。
このページを現行の選択・引継ぎ先とし、各文書の日付付き追記は履歴として読む。

## 次の着手

**[P02-d：回復操作GUIとP02条件別監査](03-planar.md#p02-d)**。
先行P02-cは[調整回復/最終細分/CLI/worker](../PLANAR_TUNING_RECOVERY.md)までDONE。親P02は未完。
[調整フォームの版1/2/3保持](../PLANAR_RECOVERY_GUI.md)を接続し、隔離フォーム4例とGUI API新1件/既存4件PASS。
次は履歴回復操作を接続し、実GUIで履歴回復・調整回復・中止再開・再起動後の元場表示を検証する。

| 辿る先 | 用途 |
| --- | --- |
| [planar_tracking_history_saved.py](../../src/superfish_ng/planar_tracking_history_saved.py) | 所有履歴の保存・worker・延長 |
| [planar_identity_recovery.py](../../src/superfish_ng/planar_identity_recovery.py) | 回復要求・元比較・集合判定 |
| [planar_tuning.py](../../src/superfish_ng/planar_tuning.py) | 版1/2/3調整要求と試行/回復/保存再生 |
| [planar_tracking.py](../../src/superfish_ng/planar_tracking.py) | 版1〜8の有限部分空間/guard/個別ID |
| [P01受入](../PLANAR_AFFINE_TUNING.md) / [TESTING](../TESTING.md) | 新しい形状法則、元場対応、直接利用先と検査証拠 |

H17は[損失範囲整理](../MATERIAL_HPHI_LOSS_SCOPE.md)まで実施しIN_PROGRESS。
2026-09-22のユーザー選択は「対象版の資料で必要性を確認してから決める」。
追加損失の採否は資料確認まで未確定とし、独立したP02を進める。

## 受入証拠と依存待ち

| 状態 | 根拠と限界 |
| --- | --- |
| H13 / H15 / H16カード受入済み | [曲線Hφ](../CURVED_HPHI_ACCEPTANCE.md)、[材料追跡](../MATERIAL_HPHI_ACCEPTANCE.md)、[材料調整と操作](../MATERIAL_HPHI_TUNING_ACCEPTANCE.md)。これらは親P03/P04の全旧互換受入ではない |
| B02 / B03整理済み | [B02](B02-reference-audit.md)、[B03](B03-required-scope.md)。C00.Vと未確認仕様の採否は未確定。TM旧集約JSONの欠落、TE集約hash一致を区別する |
| H18依存待ち | H13/H16はDONE。H17、C07-hphi、C07-materialが残る。H16の成功だけで親P03/P04を閉じない |
| 外部資料の不足 | R25改訂/対象版入力、K29/30ツール仕様、K31実機資料。調査カードの完了を、その資料に依存する実装・検証の完了としない |

全カードの着手可能性はTSVの`depends_on`を現在の状態で照合する。
この表は全残件の省略可能リストではなく、直近の引継ぎに必要な抜粋である。
原要件の全件対応は[計画](README.md)、[B01台帳](B01-ledger.md)と最新の専用受入文書を参照する。

## 実行中処理とソース固定

P02-d session 4966（既存GUI transport）、63840（回復GUI transport）はともに終了0。ログは `out/p02-planar-recovery-gui-20260922/`。
生存handleの引継ぎなし。製品srcの固定解除。
P01/P02-aの検査handleは全て終端回収済み。実ブラウザー/検証サーバーはまだ起動していない。
sandbox内のプロセス一覧はホスト全体の不存在証明に使わない。

長時間処理を開始したら、この節にツールsession/cell ID、PID（取得できた場合）、
ジョブ/出力パス、開始時実装hash、次の観測方法、ソース固定範囲を記録する。
引継ぎでは同じhandleを観測し、観測timeoutだけで再実行しない。
古い履歴のPID/「生存中」を現在の生存証拠にせず、終端結果または現存handleで確認する。

## 更新手順

1. 開始時に`git status --short`とTSVを確認し、次カードの条件・専用文書・実装を読む。
2. 作業中はこのページの次着手/処理状態を更新する。BACKLOG・CODEX_HANDOFF・計画READMEの先頭案内は固定し、同じ進捗段落を三重追記しない。
3. 受入時は専用文書へ条件別の結果、実行コマンド/終了状態、失敗/未確認、証拠パスを記録する。TSVは満たしたカードだけ更新し、部分受入と親受入を分ける。
4. このページを次カード・残る依存・生存処理に合わせて更新し、整合したローカルコミットを作る。履歴の大量削除/一括再編はしない。
5. 原計画の全条件と追加必須カードを監査して初めてgoal完了を判断する。履歴の「全goal ACTIVE」「次は」は新しい開始命令ではない。

B04確認：3入口から本ページ、着手条件・実装・検査・受入証拠へのリンク、
全111カードと依存、差分を確認しPASS（リンク節IDを含む、git diff --checkもPASS）。文書のみで数値計算・unittestは実行しない。
