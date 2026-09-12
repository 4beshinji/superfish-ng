# Hφ部分空間対応の保存・worker・CLI

[計画](HPHI_TRACKING_JOBS_PLAN.md)の実装を固定632sourceから主ツリーへ統合し、以下の範囲で限定受入。
[同領域追跡](HPHI_SAME_DOMAIN_TRACKING.md)へ、専用 `hphi_tracking` ジョブとコマンドを接続する。

```sh
python -m superfish_ng execute-hphi-tracking PREVIOUS CURRENT REQUEST.json --out NEW_DIRECTORY
python -m superfish_ng replay-hphi-tracking SAVED_DIRECTORY
```

PREVIOUS/CURRENTは完全なHφ nativeまたはcompleteな管理済みHφ単発ジョブ。
Pythonでは `JobManager.start_hphi_tracking(previous, current, request)` で専用workerを開始し、通常の状態確認・取消を使う。
要求には両比較メッシュを完全に宣言する。入力検証、元FEM再検証、同一領域・guard・比較空間の条件と予算を確認してから出力を割り当てる。

保存先にはtracking.json、sources.json、tracking-results.json、job.json、manifest.jsonとworker claimを記録する。
previous/currentの各側はProject・job・manifest・solution内のnative5ファイルを持つ、完全な取込Hφジョブとして所有する。
管理済み元Projectの表示単位・規格化・加速経路をbyte単位で保持する。直接nativeの取込では既定表示単位mmのProjectを作る。
取込は元の固有場の保存で、新しいFEM固有解の生成とは記録しない。

投入時、コピー前後、worker実行前後の要求・元入力・実装hashを照合する。
再生は所有コピーだけを使い、元の保存先へアクセスしない。
両元FEMの最低正スペクトル・RF・元場、射影・有限比較区間、E/H対応と全IDを再計算し、保存文書全体と一致することを要求する。
hashだけを更新した結果/ID/kind/要求の改変、リンク、欠落を拒否する。

completeは実行と保存の完了を示す。数値対応のPASS/UNVERIFIED、個別ID完了とは別である。
縮退群はID集合のまま保存し、未達では現在の個別IDを未確定に保つ。
元パスの移動後の再生、所有した前後の場の通常Hφジョブへの取込と再比較を利用できる。
GUI、履歴連鎖と形状写像は別工程。連続問題の誤差上界や表面ピーク精度の保証は追加しない。

## 検証

追加3unitは47.991秒でPASS。元パス移動後の再生、Project/native保持、再起動、取消、再hashした改変・リンク・予算違反を確認した。
独立操作は323.274秒でPASS。10追跡worker、6元Project worker、所有した両側の16取込、34再起動ジョブ、10CLIを含む。
再起動後は32complete/2cancelled、取消前のqueued/runningをそれぞれ観測した。
軸あり/なし・0/1/2穴、閉同軸P1と軸接続P2の縮退群、厳しい主内積条件のUNVERIFIEDを確認した。
明示軸区間/beta/位相原点とU=.5/2 Jを持つ前後Projectでは、元場と物理Gramの規格化則も一致した。
最初の8例は先に固定した独立追跡結果と全文書一致し、元80nativeファイルは不変。

独立検証の初回は、8比較の全文書一致の後に検証器のabs(list)で停止した。
検証器の配列化だけを修正して新しい出力先で完走し、製品sourceやしきい値は変更していない。
初回out/hphi-tracking-jobs-independent-20260912と、合格したout/hphi-tracking-jobs-independent-complete-20260912をともに保持する。
固定source・内部作業archiveはout/hphi-tracking-jobs-development-20260912。
既存の自作保存形式とworker管理を拡張し、新規外部資料・依存・旧版参照は追加していない。

標準1071件（1068合格・3skip）は2188.351秒、ResourceWarningなしでPASS。
skipは任意NGSolve参照2件とsandboxの既存HTTP待受1件。主3unitは42.537秒、主3CLIは19.945秒でPASS。
固定候補632sourceと主638source（不変egg-info 6件）の一致を確認した。旧seed9モード19量はf差0、最大相対差8.882e-16。
ベンチマーク/しきい値は不変。標準/統合証拠はout/validation-hphi-tracking-jobs-candidate-20260912/seed_regression.json。
