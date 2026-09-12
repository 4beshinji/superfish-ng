# 軸接続HφのProject・表示・独立Study

`AXIS_HPHI_WORKSPACE_PLAN.md`の操作工程。候補 `/tmp/superfish-axis-workspace-20260912` を主ツリーへ統合し、以下の範囲で限定受入。
専用FEM/nativeの前提は[AXIS_HPHI_RF.md](AXIS_HPHI_RF.md)を参照する。

## Projectと保存ジョブ

既存のHphiProject version 1が、閉同軸円筒・正半径明示メッシュに加え、専用AxisHphiCaseを明示選択する。
旧二形式を軸接続として読み替えない。Caseを含むProjectのstrict検査、投入時hash、worker claim、完了manifest、
元係数を保持するnative/管理済み取込・中止・再起動を共通経路で実行する。
実行のcompleteと、数値精度のnot_checkedを区別する。

    python -m superfish_ng execute-hphi-project examples/axis_hphi/holes_project.json --out NEW_JOB
    python -m superfish_ng execute-hphi-study examples/axis_hphi/holes_study.json --out NEW_STUDY
    python -m superfish_ng replay-hphi-study NEW_STUDY

例題は小規模な操作用の合成形状で、解析検証の最終細分水準や実測空洞を表すものではない。

## GUIと表示

Hφページで軸接続Projectを開き、P1/P2、モード数、エネルギー・導電率を編集できる。
軸接続Caseでは「軸上の加速経路」を明示的に有効化し、開始z・終了z・位相原点z・betaを保存する。
無効なら加速量はN/A。有効なら、複素Vaccの実部/虚部、Eaccとaccelerator/circuitの二定義のR/Qを表示する。
経路の長さは表示単位m/mmに連動し、保存・APIの物理量は常にSI。位相原点も経路とともに復元する。
既存の正半径Caseでは軸上加速経路を作れない。

元のP1/P2から符号付きHφ/Er/Ezを描画し、穴の内部を塗らない。軸はゼロ面積・ゼロ損失の区間として示す。
保存図・全18成分のSIプローブCSVには元native全5ファイルのhashと位相・規格化を付ける。
軸上Hφ/Erはゼロで、Ezは元の正則場から評価する。表示標本は連続表面ピークの保証ではない。

## 独立Study

一様尺度、全3Dエネルギー、壁導電率を掃引できる。同軸円筒専用の寸法パラメータで明示メッシュを変更する要求は拒否する。
一様尺度は全輪郭・節点と、宣言済み軸区間・位相原点を同じ倍率で写す。betaは保つ。
区間だけを元の座標に置き去りにせず、nullの経路も勝手に追加しない。
全点をFEMで解き、各点のProject/nativeと結果一覧を所有・完全再生する。
GUIの各点に両R/Qを表示し、その点の保存結果を元の係数のまま取り込める。
独立順位は追跡IDではなく、この操作では収束・追跡を判定しない。

## 現時点の検証

追加4unitは7.477秒、Hφ関連51unitは39.910秒で合格（ローカルHTTP待受の環境skip 1件）。
独立の実Project worker 4件・Study worker 12件・28 FEM点・48ジョブの再起動再生・8 CLIが50.348秒でPASS。
一様尺度・規格化・導電率に対するf/E/H/全RF・複素Vaccの相似誤差最大は1.337e-12。
この操作検査の粗いメッシュから離散化精度を受け入れず、601sourceの専用RF検証へ照合する。

実Chromeの新しい12操作がPASS。初回は10操作後、大きいメッシュの投入を15秒だけ待った検証器がタイムアウトした。
ジョブは実際に作成・計算されており、表示されていた例外文は以前の拒否テストの非表示エラー欄から読んだものだった。
待機上限を90秒にし、実際の取消まで確認した。製品sourceは変更していない。初回記録は削除せず保持する。
図とGUI画面を目視し、穴を除く元要素表示、軸経路・複素Vacc・両R/Q、StudyのSI尺度を確認した。
既存正半径Hφの8操作もPASS。初回の管理済み取込は検証器が前工程のworkspaceを参照したため失敗し、パスだけ直して再実行した。
TM/TE/平面の5操作・再起動後の6操作もPASS。最初のTM検証は同時投入した別Hφ行を検証器が選んだため失敗し、単独で再実行した。
25完了・2取消の27ジョブと、再起動前140nativeファイルの不変性、4 CLI・ブラウザーCSV/PNG byte一致・metadata一致を確認した。
保存照合の初回は検証器が未対応のJobManager context managerを使って失敗し、ExitStackでcloseする形へ直した。製品sourceは不変。
全ブラウザー・GUIサーバーと標準回帰は終了。

候補は605sourceで固定し、内部作業用アーカイブをout/axis-workspace-development-20260912へ保存した。
独立証拠はout/axis-workspace-independent-20260912、新ブラウザーはout/axis-workspace-browser-complete-20260912。
新規外部資料・依存・旧版参照はない。親P03/O02と全計画は未完。

## 最終受入記録

標準1042件（1039合格・3skip）が1635.683秒、ResourceWarningなしでPASS。
skipは任意NGSolve参照2件とsandboxの既存ローカルHTTP待受1件。別の許可実行では実HTTP/Chromeを検証した。
主4unitは5.834秒、同梱Project/Study・完全再生・プローブ/描画の5実CLIは4.827秒でPASS。
固定605sourceと主611source（不変egg-info 6件）の同一性を確認。旧seed9モード19量はf差0、最大相対差8.882e-16。
閾値・ベンチマークは変更していない。証拠はout/validation-axis-workspace-candidate-20260912/seed_regression.json、out/axis-workspace-main-examples-20260912。
操作の完了・相似則から一般の離散化精度や追跡を宣言しない。
