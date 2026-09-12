# Hφ追跡の所有履歴

[計画](HPHI_TRACKING_HISTORY_PLAN.md)の固定候補639sourceを主ツリーへ統合し、以下の範囲で限定受入。
完全なHφ追跡ジョブを順番に並べ、保存場・帯域・ID集合の連続性を検証して所有保存する。
同一真空領域の有限FEM結果の離散的な連鎖であり、標本間の連続した物理変形を証明しない。

`HphiTrackingHistoryRequest(step_count, max_steps=100)` は段階数と上限をstrictに指定する。
各段階の元FEM・E/H対応・比較区間を全て再生する。
前段currentと次段previousのnative5ファイルがbyte単位で等しく、帯域数と個別IDまたはID集合の完全分割がつながる必要がある。
各段階のProjectは保持する。表示単位や取込ジョブの記録が異なっても、元nativeが同一なら保存場の連続性は変わらない。

PASSの多次元群はID集合のまま継続できる。元の個別IDを失った群に、周波数分裂だけで個別IDを再付与することは許さない。
最終段階がUNVERIFIEDの場合は、その理由と全祖先を証拠として保存し、以後の延長を拒否する。
段階上限でも延長を停止するが、最後に検証されたIDを消さない。実行complete、数値対応、個別ID完了、延長可否を別々に記録する。

保存形式は `hphi_tracking_history` 専用ジョブで、history.json/sources.json/history-results.json、job/manifestと番号付きstep-0000以降を持つ。
全段階の追跡要求・元Project・native・対応結果を所有コピーする。延長は新しい保存先を作り、元履歴を変更しない。
元パスがなくても所有コピーから全再生できる。hashを更新したID/祖先の改変やkindの偽装、リンク、実行中の入力/実装変更を検出する。

```sh
python -m superfish_ng execute-hphi-history REQUEST.json --steps PAIR_1 PAIR_2 --out NEW_HISTORY
python -m superfish_ng extend-hphi-history SAVED_HISTORY NEXT_PAIR --out NEW_HISTORY
python -m superfish_ng replay-hphi-history SAVED_HISTORY
```

PythonのJobManagerには `start_hphi_history` と `extend_hphi_history` を追加した。
Hφ GUIでは、completeな追跡結果を明示順序で追加し、段階数/上限を保存して実行する。
履歴の各段階でE/Hの対応・ID集合・係数位相・未検証理由を表示し、完全な段階要求/結果の保存と前後の元場の取込を行う。
全履歴の結果保存、次の比較による延長、`/hphi.html?history=JOB_ID` と計算履歴からの復元を接続した。

## 検証状況

固定639sourceで追加9unitが421.101秒でPASS。
正逆の元場連続性、ID集合を個別IDで置換する履歴の拒否、UNVERIFIED/上限での停止、祖先変更、再hashした改変、コピー/worker開始時の入力変更、取消/再起動、GUIの段階選択と元Project/native取込を確認した。
初回8unitは、試験中にGUI接続の編集を行ったため実装hashの変更を検知し、1件ERRORで終了した（258.420秒）。初回ログを保持し、製品の条件を変更せず固定後の9unitで再検証した。

実Chromeの新規16項目と旧追跡14項目がPASS。個別対応・縮退/順位逆転のID集合、連続しない保存場の延長拒否、上限/未検証の停止、各段階の元場/要求/結果の保存、実行中止とURL復元を確認した。表の横はみ出しがないことと、縮退群/停止理由の画面を目視した。

独立検証の初回は8種の正逆チェーン・規格化/表示単位・CLI検査の後に、元ディレクトリを移動した状態で管理器を閉じようとして停止した。検証器の管理器停止を移動前へ移しただけで、製品/testsは不変。初回出力out/hphi-tracking-history-independent-20260912を保持し、out/hphi-tracking-history-independent-complete-20260912で再実行し、1111.930秒でPASS。8種の2段階チェーン、21履歴worker・11追跡worker・2元Project worker、39再起動・5CLIと元8追跡保存の不変を確認した。周波数が等しくても規格化の異なる元場の接続を拒否し、同じnativeの表示単位m/mmは両Projectを保持して接続できた。

旧TM/TE/平面5項目と再起動後の実Chrome8項目もPASS。元追跡と親履歴を移動した後、所有コピーだけから3段階へ延長し、元場を取り込めた。全28保存ジョブ（26 complete・2 cancelled）、再起動前286 nativeファイルと6履歴の不変を142.123秒で照合した。5CLIとの全結果JSON一致、元native5ファイル・PNG・CSVのbyte一致とプローブメタデータ一致も確認した。標準回帰と本体統合も終了した。
証拠はout/hphi-tracking-history-development-20260912。新規外部資料・依存・旧版参照なし。
既存の自作平面履歴の保存・連鎖処理をHφへ適用し、隣接スペクトル照合をHφのnative5ファイルへ限定した。両Projectと取込記録は各段階の完全再生で別に保持・検証する。

標準1082件（1079合格・3skip）は2211.843秒、ResourceWarningなしでPASS。
skipは任意NGSolve参照2件とsandboxの既存HTTP待受1件。ローカルGUIの実操作は上記の実Chromeで確認した。
主9unitは377.836秒、主28保存ジョブ/5CLIの照合は139.450秒でPASS。
候補639sourceと主645source（不変egg-info 6件）の一致を確認した。
旧seed9モード19量はf差0、最大相対差8.882e-16。ベンチマークと数値しきい値は不変。
標準/統合証拠はout/validation-hphi-tracking-history-candidate-20260912/seed_regression.json。
