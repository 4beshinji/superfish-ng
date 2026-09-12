# Hφ部分空間対応のGUI

[計画](GUI_HPHI_TRACKING_PLAN.md)の実装を固定634sourceから主ツリーへ統合し、以下の範囲で限定受入。
Hφページで、completeな保存場二つと完全な追跡要求を選び、専用workerを実行・取消する。
元の前後Projectから、比較メッシュやIDを暗黙に作らない。

追跡要求のファイル読込/保存、JSON編集、帯域数・個別ID/ID集合・全controlsの編集を接続した。
結果には実行状態、E/H対応のPASS/UNVERIFIED、個別IDの確定状態を別々に表示する。
前後の順位、ID集合、E/Hそれぞれの最小主内積、個別モードの係数位相、有限比較区間と射影誤差、guard等の未検証理由を確認できる。
多次元群には個別IDや基底ごとの位相を割り当てず、未検証の対応も候補として区別する。

結果と要求を保存し、`/hphi.html?tracking=JOB_ID` または計算履歴から復元する。
所有した前後の場を通常Hφジョブへ取り込み、元のProject・係数・native5ファイル・PNG・全18成分SIプローブを利用できる。
「保存した前後の場で再比較」は、元パスがなくても所有コピーを使って新しいジョブを実行する。
元の場を選べなくなった場合は選択欄を空に戻し、古い別の選択を表示し続けない。
同時に細分差表を「増加の検査／許容内」とし、許容幅 `max(前の差×1e-8, 1e-12)` を明記した。数値判定式は不変。

## 検証

GUI API追加2unitは51.171秒でPASS。
独立した保存6例のGUI再生、両側12取込、18再起動ジョブ、6CLIとの全文書/元Project/native一致は261.928秒でPASS。
軸あり/なし・二穴、同軸P1/軸P2縮退、UNVERIFIED、明示加速区間と異なる規格化を含む。
初回の検証起動で子CLIへ候補PYTHONPATHを渡し忘れ、未統合の主CLIを呼んだため停止した。製品・検証sourceは変更せず、候補を指定して新しい出力先で完走した。

実Chromeの新規14項目、サーバー再起動後8項目がPASS。個別ID、実順位逆転する縮退群、厳しい条件とguardのUNVERIFIED、実行中の取消、要求/結果保存、元場表示と全保存、履歴/URL復元を含む。
既存の細分差15項目・軸接続Hφ12項目・正半径Hφ8項目・TM/TE/平面5項目も順にPASSした。
外部HTTPリクエストは0、実行中の製品sourceは不変。個別対応と縮退群の画面を目視し、表の横はみ出しがないことを確認した。

元の二つの保存先を移動後も所有した場で新規worker再比較を実行し、元の結果と全文書一致した。
保存照合は45.822秒でPASS。33ジョブ（29complete/4cancelled）を全再検証し、移動した元保存先を含む226のnativeファイルのhashを保持した。
元native5ファイルのダウンロード、PNG/全成分CSVのブラウザー・再起動後・CLIのbyte一致、Project/メタデータ一致、5CLIを確認した。
検証後の全ブラウザーとローカルサーバーは終了済み。

証拠はout/hphi-tracking-gui-independent-complete-20260912、out/hphi-tracking-gui-browser-20260912、out/hphi-tracking-restored-browser-20260912、out/hphi-tracking-old-*-browser-20260912、out/hphi-tracking-gui-artifacts-20260912。
固定source・内部作業archiveはout/hphi-tracking-gui-development-20260912。標準も終了した。
既存の自作GUI/API/保存を拡張し、新規外部資料・依存・旧版参照なし。
履歴連鎖と形状写像は別工程。連続問題の同一性や誤差上界・表面ピーク精度の保証は追加しない。

標準1073件（1070合格・3skip）は2098.608秒、ResourceWarningなしでPASS。
skipは任意NGSolve参照2件とsandboxの既存HTTP待受1件。ローカルGUIは別の実Chromeで上記の操作を確認した。
主2unitは39.069秒、主33ジョブ/5CLIの保存照合は45.452秒でPASS。
固定候補634sourceと主640source（不変egg-info 6件）の一致を確認した。旧seed9モード19量はf差0、最大相対差8.882e-16。
ベンチマーク/数値しきい値は不変。標準/統合証拠はout/validation-hphi-tracking-gui-candidate-20260912/seed_regression.json。
