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

## H09条件別の監査

| 元の受入条件 | 証拠と現在の範囲 |
|---|---|
| 同軸寸法探索・穴付き非一様変形 | H09-cの同軸3寸法実探索と`validate_hphi_shape_tuning.py`の穴付き4実FEM。独立TEMの周波数・q質量重なりを別検査 |
| ID確認後にのみ周波数評価 | `test_hphi_shape_tuning`のguard反例はUNVERIFIEDでfrequency=null。H09-bの縮退対照は集合を保持し、個別IDを捏造しない |
| 正逆比較 | H09-aの両側全被覆・H09-bの逆Gram/同軸逆追跡。追加穴付き逆追跡もPASS |
| 番号置換・同形状の別分割 | H09-aの番号置換・境界分割・独立FEM。追加穴付き同物理形状の異なる対角線/境界分割/頂点番号でも追跡IDが一致 |
| 保存再開で元要求再現 | H09-cのCLI所有再開、要求法則改変拒否。同軸worker/GUIは確認済み、穴付きworker/GUIの最終回収は残る |
| worker/GUI・サーバー復元 | 本工程の途中証拠。全受入までは未完了 |

追加検査は`test_hphi_mapped_tracking.HphiMappedTrackingTests.test_piecewise_hole_motion_with_independent_numbering_and_id_set` 1件、19.113秒、終了0。既存の穴移動検査に逆方向と同形状の独立表現を追加した。数値実装・許容差は変更していないため、H09-a/b/cの不変な部分の成功証拠を再利用する。全suite・seed validator・Hosted CIを今回実行したとは主張しない。
