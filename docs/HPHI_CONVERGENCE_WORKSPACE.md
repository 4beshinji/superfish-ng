# Hφ細分差診断の実行・保存・GUI

[接続計画](HPHI_CONVERGENCE_WORKSPACE_PLAN.md)の固定候補620sourceを主ツリーへ統合し、以下の範囲で限定受入。
数値契約は[細分差診断](HPHI_CONVERGENCE.md)と同じ。完全定義のProject列から各水準を実FEMで計算する。

`JobManager.start_hphi_convergence(request)` は専用 `kind=hphi_convergence` のローカルworkerを起動する。
全水準を所有 `point-000i` ジョブとして保存し、元Project・native5ファイル・要求・全診断をmanifestへ結び付ける。
投入時の要求hash、worker claim、計算中の要求/実装の変化を検査する。再生は全点の元係数・最低正スペクトル・RF・診断を再検証する。
要求やkindを改変してhashを作り直した保存、リンクや未完の水準を受け入れない。

CLI `replay-hphi-convergence RUN` は専用APIの単独保存とJobManagerの保存形式を区別し、どちらも完全再生する。
Hφページでは要求の開く/保存、strict JSON編集、周波数順位と8しきい値の編集、実行/取消、結果保存とURLからの復元ができる。
メッシュや外周/穴を暗黙に生成・修正しない。各水準の全Project、SIの軸区間・beta・位相原点を保持する。

画面は実行・保存完了 `complete` と、最後3水準の差の `PASS/UNVERIFIED` を分けて表示する。
f/E/H、各RF量、全壁線分、宣言された複素Vaccについて、最後2組の差・しきい値・増加の検査・判定を確認できる。
guard不足や対応不明の理由を示し、表面ピーク精度保証と縮退モードの部分空間追跡は未実施と明示する。
元水準を通常Hφジョブへ取り込むと、元係数の場のPNG・全18成分SI CSV・nativeをそのまま確認できる。
既存の独立Studyや通常TM/TE/平面追跡候補へ、この種別を混ぜない。

## 検証

最終追加2unitは30.396秒でPASS。初回UI挿入時のJavaScript構文エラーは修正し、両JSの構文検査と実Chromeで確認した。
独立7worker/21FEM水準、単独同軸3FEM、21元水準取込、30再起動ジョブ（2取消）、7CLIは260.864秒でPASS。
軸あり/なし・0/1/2穴と閉同軸を含み、単独保存の同じ要求と結果全文書が一致した。穴付きの粗い列はUNVERIFIEDを保持する。

実Chromeは新規14操作・再起動後6操作、旧軸接続Hφ12・旧正半径Hφ8・旧TM/TE/平面5操作がPASS。
要求/全Project/しきい値/軸区間の保存復元、PASS/厳しい条件のUNVERIFIED/guard理由、P1二穴の場、加速未宣言、実取消、履歴復元を確認した。
同じworkspaceへブラウザーを順次実行し、外部通信はなかった。初回Chromeの検証器DOM式の引用符エラーも出力を保持し、製品source不変で直して再実行した。
復元・診断・二穴の場の画面を目視した。

最終保存照合は26再起動ジョブ（23完了/3取消）、再起動前の180nativeファイル不変、元native5ファイルのダウンロード一致がPASS。
ブラウザー・CLI・再起動後のPNGと全成分CSVはbyte一致し、プローブmetadataも一致した。4CLIを含め25.335秒。
全ブラウザーと両GUIサーバーは終了済み。標準回帰も終了した。

証拠はout/hphi-convergence-workspace-independent-20260912、out/hphi-convergence-browser-complete-20260912、
out/hphi-convergence-restored-browser-20260912、out/hphi-convergence-old-{axis,positive,tm-te}-browser-20260912、
out/hphi-convergence-workspace-artifacts-20260912。固定sourceと内部作業archiveはout/hphi-convergence-workspace-development-20260912。
新規外部資料・依存・旧版参照なし。曲線内導体・部分空間追跡・旧版照合等と親課題・全計画は未完。

標準1057件（1054合格・3skip）は1683.000秒、ResourceWarningなしでPASS。
skipは任意NGSolve参照2件とsandboxの既存HTTP待受1件。HTTP/操作は別の許可された実Chrome実行で確認した。
統合後2unitは30.119秒、26保存ジョブ/4CLI・元native/PNG/CSVの照合は25.087秒でPASS。
候補620sourceと主626source（不変egg-info 6件）が一致した。旧seed9モード19量はf差0、最大相対差8.882e-16。
ベンチマーク・既存しきい値は不変。標準/統合証拠はout/validation-hphi-convergence-workspace-candidate-20260912/seed_regression.json。
