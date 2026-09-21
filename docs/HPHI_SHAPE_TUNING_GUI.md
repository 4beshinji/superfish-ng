# Hφ形状調整のworker・GUI受入（H09-d、進行中）

要求版2の同軸寸法と穴付き非一様変形について、実workerの中止・所有コピーからの再開・管理器再起動、実ブラウザー操作、元native/RFの一致を検査する。親H09は本受入と統合監査の完了まで未完了。

## 検証器

- `scripts/validate_hphi_shape_tuning_jobs.py --out out/<new-name>`：両形状を実workerへ投入し、最初の永続checkpointで中止する。GUI APIから再検証・別ジョブ再開し、元ジョブを移動して管理器を作り直す。要求・履歴prefix・各試行の5 nativeファイル（場・メッシュ・RF・manifestを含む）のbyte一致を検査する。
- `scripts/verify_gui_hphi_shape_tuning.mjs --url <local-hphi-url> --out out/<new-name> --request <request.json> --workspace <server-workspace>`：既存のChrome DevTools検証方式を使う。実マウス操作で開始・中止・保存地点選択・ダウンロード・同一ファイル2回読込・別ジョブ再開・対象実順位の元場描画を検査する。`--replay-only <checkpoint.json>`は既存保存結果の表示検査だけを行う。外部HTTPを拒否し、srcの不変性を確認する。

版1だけを説明していた画面文言を修正し、同軸寸法はm、尺度・変位係数は無次元と明記した。FEM・比較移送・許容差は変更していない。新規外部資料・依存・legacy参照はない。

## 途中証拠（2026-09-21）

同軸worker経路はPASS。両形状まとめの出力は`out/h09-d-jobs-20260921`で、穴付き経路は実行中。

同軸ブラウザーの`out/h09-d-browser-coaxial-retry-20260921/report.json`は中止・同一checkpoint再読込・別ジョブ再開まで成功したが、検証器がJavaScript配列の順位取得にPythonの`index`を使って停止した。`indexOf`へ修正し、既存結果を新ブラウザーで再生した`out/h09-d-browser-coaxial-replay-20260921/report.json`はPASS、終了0。結果の全RF値一致、実順位、N/A、描画を確認し、`native-field.png`を目視した。初回`out/h09-d-browser-coaxial-20260921`のページ初期化待機不足も失敗として保持する。これらを一括操作の単独PASSとは呼ばない。

穴付きブラウザー、サーバー再起動後の実ブラウザー復元、H09受入条件別の最終監査は未完了。
