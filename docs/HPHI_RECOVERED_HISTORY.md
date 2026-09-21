# 所有Hφ履歴の個別ID回復（H10-b、受入済み）

[回復核](HPHI_IDENTITY_RECOVERY.md)のanchorを、専用履歴に所有された過去のnative snapshotへ結び付ける。原場・元Project・全対応requestを所有し、回復後だけ個別IDを後続へ継承する。[調整接続（H10-c）と親H10監査](HPHI_TUNING_IDENTITY_RECOVERY.md)も受入済み。

## 写像を持つ保存pair

`HphiTrackingRequest`は`geometry_mapping`を省略すれば従来通り`tracking_version=1, mapping=same_vacuum`を保存する。明示`HphiGeometryMapping`を渡した要求は版2で、完全な`mapping`と`transport=unitary_fixed_cylindrical_components`を保存する。比較APIへ別の写像/尺度を同時指定することは禁止する。

既存`execute-hphi-tracking`とworker・所有再生は同じ要求readerを使い、版2の元領域同士にはH09の厳密写像overlayを適用する。各元FEMと各比較空間の被覆検査はそれぞれの元領域で維持する。元native/RFのコピー形式を変えない。回復要求の内側comparisonは版1のままとし、回復写像は外側の`mapping`で一度だけ宣言する。

## 履歴要求版2

従来の`step_count, max_steps`に、非空の`recoveries`を加える。

```
{
  "after_step_index": 1,
  "request": <完全なHphiIdentityRecoveryRequest>
}
```

各step indexは0始まり・重複なし・昇順で、所有履歴に存在しなければならない。snapshot 0は最初のpairのprevious、snapshot i+1はstep iのcurrentであり、anchorは必ず回復対象より前にある。空配列/null・未来anchor・bool indexは拒否する。回復を宣言しない従来要求の版1形式は変更しない。

再生は各所有pairを完全再検証し、隣接する5 nativeファイルのhash一致を確認する。回復時は、履歴内の指定anchorが確認済み個別IDを持つことと、回復比較のprevious IDsが当時の実順位順と一致することを確認する。ユーザー指定の別パスからanchorを読み込まない。

その所有anchor・previous・currentを回復核へ渡し、継承比較を再計算した結果がpairの保存結果と一致することを確認する。eventにanchor/currentの5 native hashを記録する。再生前後で全pair snapshotを再比較し、途中改変を拒否する。

回復成功時の個別IDだけを次のpairへ渡す。回復失敗または元対応のUNVERIFIED後は後続stepと延長を拒否する。回復前のraw pair結果は改変せず、履歴の有効なID状態と回復eventを別に保持する。延長API/workerは元の全eventを新しい所有履歴へ継承する。

## 受入と限界

新しいCLI/worker経路の検証では、解析的に縮退する同軸TEM/径方向モードの3つの実FEM場を保存する。長い空洞→縮退→短い空洞→長い空洞という離散列で、縮退後の個別ID回復と次の追跡を検査する。過去anchorのID順改変、未解決anchor、guardでの失敗、元pair移動、結果改変と所有コピーの全byte一致を検査する。連続分枝の一意性は主張しない。

`test_hphi_mapped_tracking_saved`の2件は31.469秒PASS、終了0。変更前の版2拒否を`out/h10-mapped-pairs-20260921/before.log`、保存・CLI再生・元場移動後の所有再生を`after.log`に記録した。

`test_hphi_recovered_history`の3件、既存の専用追跡・履歴保存・GUI transport・回復核23件と、調整の直接利用先2件がPASS。調整利用先の最初のコマンドはクラス名を誤指定してFEM前に失敗したため、正しいクラス名で再実行し、両ログを保持する。出力は`out/h10-history-20260921`。これを全suite、seed TM、実ブラウザーの受入には読み替えない。

新規外部資料・依存・legacy参照はない。H09/H10-aの数値移送・独立同軸対照を再利用し、solverや既定許容差は変更しない。

調整の直接利用先2件は39.569秒PASS、終了0。履歴フォームが要求版2を版1へ変換して回復eventを落とす問題を、実フォーム関数の読込→保存で再現した（`gui-form-before.log`）。数値検証終端後に要求保持と所有pair要求ダウンロードを補修し、フォーム回帰と実ブラウザーで確認した。

新しい所有回復履歴3件は842.861秒PASS、終了0（`new.log`）。GUI検証用に完成した履歴48ファイルを`out/h10-browser-workspace-20260921/recovered`へbyte/hash一致でコピーし、元の一時入力ディレクトリ削除後も保持した。数値実行時の349実装hashが現行と一致することを確認済み。

専用回帰23件は1074.543秒PASS、終了0。数値handle終了後、GUI履歴フォームを修正し、読込要求のversion/recoveriesを保持するようにした。実フォーム関数の回帰1件は0.049秒PASS、終了0。履歴表示は明示回復のanchor/status/IDを表示し、各pairの要求ダウンロードは数値比較reportの埋込宣言ではなく所有`tracking.json`を返す。数値検証時から変わったsrcは`gui_hphi.py`、`web/hphi.js`、`web/hphi.html`の3ファイルだけとhash照合した。実ブラウザー受入もPASS（以下）。


## 操作受入と最終照合

`scripts/verify_gui_hphi_recovered_history.mjs`で、元の一時入力が削除された所有履歴を実Chromeから再生した。回復後の実順位/anchor表示、版2要求の完全な保存、元の写像pair要求のダウンロードと正規化、旧版読込によるevent解除と版2再読込の4項目がPASS、終了0。`out/h10-history-browser-20260921/report.json`、`recovered-history.png`を保存し画像を目視した。外部HTTPは0、新FEM候補は投入していない。

`out/h10-history-browser-20260921/acceptance.json`は最終PASS。所有48ファイルが不変で、数値検証後の変更がGUIの3ファイルだけであること、ブラウザー開始時の全349実装hashが現行と一致することを確認した。全検証handleとGUIサーバーは終了済み。新6unit（写像保存2・所有履歴3・フォーム1）と既存25unit（専用回帰23・調整利用先2）の分割証拠であり、全suite/seed/Hosted CIの証拠にはしない。

H10-bの保存・CLI/worker・GUI要求保持は受入済み。H10-cの検索試行/最終細分への調整回復接続も、その専用文書の証拠で受入済み。
