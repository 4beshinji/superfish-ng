# Hφ形状調整のworker・GUI受入（H09-d、受入済み）

要求版2の同軸寸法と穴付き非一様変形について、実workerの中止・所有コピーからの再開・管理器再起動、実ブラウザー操作、元native/RFの一致を検査する。本工程と条件別監査を完了し、H09-a〜dを満たした。次はH10の個別ID回復。

## 検証器

- `scripts/validate_hphi_shape_tuning_jobs.py --out out/<new-name>`：両形状を実workerへ投入し、最初の永続checkpointで中止する。GUI APIから再検証・別ジョブ再開し、元ジョブを移動して管理器を作り直す。要求・履歴prefix・各試行の5 nativeファイル（場・メッシュ・RF・manifestを含む）のbyte一致を検査する。
- `scripts/verify_gui_hphi_shape_tuning.mjs --url <local-hphi-url> --out out/<new-name> --request <request.json> --workspace <server-workspace>`：既存のChrome DevTools検証方式を使う。実マウス操作で開始・中止・保存地点選択・ダウンロード・同一ファイル2回読込・別ジョブ再開・対象実順位の元場描画を検査する。`--replay-only <checkpoint.json>`は既存保存結果の表示検査だけを行う。外部HTTPを拒否し、srcの不変性を確認する。

版1だけを説明していた画面文言を修正し、同軸寸法はm、尺度・変位係数は無次元と明記した。FEM・比較移送・許容差は変更していない。新規外部資料・依存・legacy参照はない。

## 実行結果（2026-09-21）

同軸・穴付きworker経路は両方PASS、終了0。出力は`out/h09-d-jobs-20260921/report.json`。両形状の中止・別ジョブ再開・元ジョブ移動・管理器再起動・各2試行の全nativeファイル一致を確認した。

同軸ブラウザーの`out/h09-d-browser-coaxial-retry-20260921/report.json`は中止・同一checkpoint再読込・別ジョブ再開まで成功したが、検証器がJavaScript配列の順位取得にPythonの`index`を使って停止した。`indexOf`へ修正し、既存結果を新ブラウザーで再生した`out/h09-d-browser-coaxial-replay-20260921/report.json`はPASS、終了0。結果の全RF値一致、実順位、N/A、描画を確認し、`native-field.png`を目視した。初回`out/h09-d-browser-coaxial-20260921`のページ初期化待機不足も失敗として保持する。これらを一括操作の単独PASSとは呼ばない。

穴付きブラウザーも`out/h09-d-browser-holed-20260921/report.json`で開始・中止・同一ファイル2回読込・別ジョブ再開まで成功した。実行開始時点に残っていた同じ`index`誤記で表示検証が停止したため、修正済み検証器で保存結果を再生した。

元GUIサーバーはCtrl-Cで正常終了（終了0）し、同じworkspaceから別プロセスを起動した。新ブラウザー各1回の`out/h09-d-restarted-coaxial-20260921/report.json`、`out/h09-d-restarted-holed-20260921/report.json`は共にPASS・終了0。実順位1/4の元場、全RF値、N/A、画像描画を確認した。両画像を目視確認し、再起動後のサーバーも正常終了した。新ブラウザー再生で新FEM候補は投入していない。

最終照合`out/h09-d-audit-20260921/acceptance.json`はPASS。各再開trialの5 nativeファイルとGUI取込後の5ファイルはbyte完全一致で、実行開始時のsrc hashも現行と一致する。全検証handleの終端は同ディレクトリの`process-evidence.json`に記録した。先行した操作列の失敗と後続の再生PASSを併記し、一括操作の単独PASSには読み替えない。

## H09条件別の監査

| 元の受入条件 | 証拠と現在の範囲 |
|---|---|
| 同軸寸法探索・穴付き非一様変形 | H09-cの同軸3寸法実探索と`validate_hphi_shape_tuning.py`の穴付き4実FEM。独立TEMの周波数・q質量重なりを別検査 |
| ID確認後にのみ周波数評価 | `test_hphi_shape_tuning`のguard反例はUNVERIFIEDでfrequency=null。H09-bの縮退対照は集合を保持し、個別IDを捏造しない |
| 正逆比較 | H09-aの両側全被覆・H09-bの逆Gram/同軸逆追跡。追加穴付き逆追跡もPASS |
| 番号置換・同形状の別分割 | H09-aの番号置換・境界分割・独立FEM。追加穴付き同物理形状の異なる対角線/境界分割/頂点番号でも追跡IDが一致 |
| 保存再開で元要求再現 | H09-cのCLI所有再開、要求法則改変拒否。両形状worker・GUIの元要求/所有prefixと再起動後復元が一致 |
| worker/GUI・サーバー復元 | 両形状の実中止/再開、管理器再起動、元サーバー終了後の新プロセス・新ブラウザー復元がPASS |

追加検査は`test_hphi_mapped_tracking.HphiMappedTrackingTests.test_piecewise_hole_motion_with_independent_numbering_and_id_set` 1件、19.113秒、終了0。既存の穴移動検査に逆方向と同形状の独立表現を追加した。数値実装・許容差は変更していないため、H09-a/b/cの不変な部分の成功証拠を再利用する。全suite・seed validator・Hosted CIを今回実行したとは主張しない。

以前H07でsandbox制限によりskipされた`test_gui_hphi.HphiGuiTests.test_real_http_assets_authentication_and_strict_actions`も、ローカルbindが許可された環境で実行し、1件・0.616秒・終了0。HTTP配信、認証なし403、未知項目400を確認した。
