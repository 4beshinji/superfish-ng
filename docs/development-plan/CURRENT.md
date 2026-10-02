# 現行の作業入口

更新：2026-10-02、開発カードP04-b-a受入、P04-b-b受入、次はP04-b-c（基準 `afd6fdd`）。
原90カードと追加子カードを含む全121カードの計画は継続中。P04をa〜c、P04-bを形状a/所有保存b/worker監査cへ分割。
このページを現行入口とし、各文書の日付付き追記は履歴として読む。

## 横断レビューと計画（2026-09-22）

ユーザー依頼のREVIEW-01として、`a191b4e`基準の[既存実装レビュー](../IMPLEMENTATION_REVIEW_2026-09-22.md)と
[リファクタリング計画](../REFACTORING_PLAN.md)を作成した。所見10件とRF-01〜RF-10の依存・受入・検証・撤回方法を記録。
依存不在のGUIテストエラーを限定再現したが、製品・テスト・検証器は未変更、修正カードは全てPLANNED。
次にリファクタリングを実施する場合の推奨はRF-01（検証来歴）→RF-02（環境/任意依存）。
既存115開発カードの状態は維持する。以下は既存機能開発の次着手であり、今回の文書作成の継続作業ではない。

## 次の着手

**[P04-b-c：区分調整workerの所有中止・再開とP04-b監査](03-planar.md#p04-b-c)**。
[P02条件別監査](../PLANAR_IDENTITY_RECOVERY_ACCEPTANCE.md)と
[P03の区分写像/幾何契約](../PLANAR_PIECEWISE_MAPPING.md)までDONE。
[P04-aの共同比較・追跡・所有再生](../PLANAR_PIECEWISE_TRACKING.md)もDONE。
[P04-b-aの元形状法則・参照比較・新版要求](../PLANAR_PIECEWISE_SHAPE.md)までDONE。
[P04-b-bの実調整・所有保存/移動後再生・CLI再開](../PLANAR_PIECEWISE_TUNING_SAVED.md)までDONE。
次はqueued入力の全先行trialを所有し、新版worker中止/別job再開・管理器再起動を確認する。
`planar_tuning_jobs.py` は旧入力/結果/ancestry集合の前提を持つため、新版所有checkpointへ接続する。
具体的にはqueued prefixコピーと入力hash、相対resultのexecution owner指定、
コピーで変わるtrial pathと不変なProject/native/判断の区別、request/prefix checkpointの集合照合を扱う。
全試行を実FEMで計算し、未確認群は評価しない。GUIと親監査はP04-c。
P03は連続区分アフィンによる全域非アフィン変形に限定する。滑らかな非線形/曲線写像は未対応。
入口は `planar_piecewise_mapping.py`、`planar_tracking_fields.py`、`planar_tracking.py`、`planar_tuning.py`。
検査選択は[TESTING](../TESTING.md)とP04仕様を参照。
親互換課題P02やD02全体を完了とは扱わない。

P03の新7/既存25件、計32件は1.871秒PASS（終了0）。
範囲・初回テスト入力エラー・解析不変量・コマンドは上記専用文書に記録。
全validate/seed/GUIの再実行はしていない。実行handle94126は終了0、生存処理の引継ぎなし。

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

2026-10-02：P04-b-bは初回session30100終了1（新7件、2PASS/3FAIL/2ERROR、85.712秒）。
格子改善後session99948終了1（選択21件、20PASS/CLI期限1ERROR、846.030秒）。
旧版1〜3の14件全PASS。CLI300秒期限の再確認session65480は256.734秒PASS（終了0）。
独立TMはsession12993終了1（8/16gridでiteration limit）後、12/24gridのsession11671が
192.929秒PASS（終了0）。分割22件成功、全数値許容差を保持。395製品hash不変、
全handle終端、src固定解除。証拠 `out/p04bb-planar-owned-20261002/` と[専用記録](../PLANAR_PIECEWISE_TUNING_SAVED.md)。

2026-10-02：P04-b-aは初回session36755終了1（28PASS/1FAIL、146.388秒）。
再生成/幾何検査の順序修正後、session64698の影響17件は45.567秒PASS（終了0）、
非影響の初回12件成功を保持する。各実行の394製品hash不変、全handle終端、src固定解除。
証拠 `out/p04ba-planar-shape-20261002/` と[専用文書](../PLANAR_PIECEWISE_SHAPE.md)。

2026-10-02：P04-aのsession39306は終了1（54PASS/誤メソッド名1収集ERROR）。
正しいstrict1件と独立元場/RF2件は別実行で終了0。分割57件PASS、391製品ファイル不変、
全worker/handle終端、src固定解除。証拠 `out/p04a-planar-piecewise-20261002/`、詳細は専用文書。

履歴Chrome session 91632と調整/新サーバーsession 87997は終了0。
全Chrome/サーバー/managerをclose済み。製品src固定解除、生存handleの引継ぎなし。
証拠は `out/p02-planar-history-browser-20260922/` と `out/p02-planar-tune-browser-20260922/`。
各reportの389製品hashを現行ファイルと照合し不変。
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
