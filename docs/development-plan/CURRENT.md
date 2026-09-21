# 現行の作業入口

更新：2026-09-22、P01形状法則第一段階。直前の成果コミットはH17調査 `926d58b`。
原90カードと追加子カードを含む[全111カード](tasks.tsv)の計画は継続中。
このページを現行の選択・引継ぎ先とし、各文書の日付付き追記は履歴として読む。

## 次の着手

**[P01：平面アフィン形状法則を調整要求へ追加](03-planar.md#p01)**。
先行B01はDONE。[多項式形状法則の基盤](../PLANAR_AFFINE_SHAPE.md)は実装/分割検証済み。
P01はIN_PROGRESSで、次は調整要求と試行間の元場比較への接続。
元xy Projectから有限多項式の行列法則で全試行を生成し、
面積行列式・回転/せん断/尺度・全区間退化拒否と固定U′を検証する。

| 辿る先 | 用途 |
| --- | --- |
| [planar_tuning.py](../../src/superfish_ng/planar_tuning.py) | 既存調整要求と試行 |
| [planar_tracking_exact_affine.py](../../src/superfish_ng/planar_tracking_exact_affine.py) | 既存アフィン比較契約 |
| [planar_study.py](../../src/superfish_ng/planar_study.py) | Projectからの候補生成 |
| [TESTING](../TESTING.md) / [共通検証規則](README.md#検証と完了報告) | test_planar_tuning / test_planar_tracking_exact_affine / test_planar_studyから影響先を選ぶ |

H17は[損失範囲整理](../MATERIAL_HPHI_LOSS_SCOPE.md)まで実施しIN_PROGRESS。
追加損失を必須にするか質問中。無回答で採否を確定せず、独立したP01を進める。

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

この更新時に引き継ぐ生存ツールhandle・worker・検証サーバーはない。
H16操作検証の全handle終端記録は上記受入文書にある。B02〜B04は文書調査で新規常駐処理を起動していない。
製品srcの検証待ち固定は解除済み。sandbox内のプロセス一覧はホスト全体の不存在証明に使わない。

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
