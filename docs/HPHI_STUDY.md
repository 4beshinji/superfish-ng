# 正半径Hφの独立Study

2026-09-12、[Study計画](HPHI_STUDY_PLAN.md)に従い主ツリーへ統合・限定受入した。
固定候補589sourceの全回帰と、主595source（従来の不変egg-info 6件を含む）の対応を確認した。

## 定義と保存

`superfish_ng_hphi_study` study_version 1、kind=sweepを専用HphiProjectへ接続する。
値は有限の正数を2点以上指定する。対応パラメータは一様尺度、同軸円筒の内半径/外半径/長さ、
全3D蓄積エネルギー[J]、壁導電率[S/m]。一般断面へ円筒寸法を適用しない。
尺度変換は外周・全穴・全節点の同じ原点尺度とし、接続・番号・P1/P2を保持してstrict幾何を再検査する。
丸めによって共線性や正Jacobianを保てない場合は、実行前に拒否する。
全派生Projectを出力確保前に検査し、任意JSONパスや未知版・追跡指定を受理しない。

各点を実FEMで解き、全native・Project・点ジョブを所有して保存する。
親manifestは全点とsummaryを束縛し、完全再生した各点のRFとsummaryを一致させる。
点欠落・余分な点、kind降格、再hash後の入力/RF改変・取込点への置換を拒否する。
各順位は独立スペクトルの順位で、mode_tracking=not_performed、numerical_validation=not_checkedを明示する。
閉じた真空・既存の位相規約・全3D U[J]/P[W]・両R/QのN/A契約を保持する。

queued入力hash、排他的worker claim、実装/入力変更拒否、失敗/中止、未完了状態の再起動復旧は既存Jobの契約を使う。
完了済みの出力へ再実行せず、新しいジョブを作る。各点は元係数を保持した所有コピーとして通常Hφジョブへ取り込める。

```sh
python -m superfish_ng execute-hphi-study examples/coaxial/shorted_study.json --out new-coaxial-study
python -m superfish_ng execute-hphi-study examples/hphi_mesh/holes_study.json --out new-holes-study
python -m superfish_ng replay-hphi-study saved-study
```

Pythonでは `HphiStudy(HphiProject(...), 'uniform_scale', [1, 2])` と `JobManager.start_hphi_study` を使う。
`manager.close()` は未完了workerを中止するため、完了まで管理器を保持する。

## GUI

Hφ画面の独立掃引から、完全定義のファイル保存/読込、実worker開始/中止、結果保存、各点の元場取込・描画を行う。
表は順位・f・U[J]・P[W]・Q0・Gと両R/QのN/Aを表示する。Studyを追跡やメッシュ精度判定と表示しない。
通常履歴から `hphi.html?study=...` へ開き、サーバー再起動後も定義と各点を復元する。
Studyを既存の軸接続追跡候補へ混ぜない。API応答/点取込の前後で全Study snapshotを照合する。

## 検証履歴

物理不変量の先行テストは未実装moduleで失敗することを確認した。
実装後の初回物理テストは、円筒の低位fields_at APIにB列もあると誤認した検証器が空配列で失敗。
このAPIの全E/Hへ直し、B=mu0 Hの表示/CSV契約は既存検証で保持した。FEM式や閾値は変更していない。
物理3unitは3.166秒、操作8unitは9.208秒で合格。
GUI追加後の初回12unitは、検証器が一時ディレクトリを削除した後に管理器を閉じたためcleanupが失敗した。
ExitStackで管理器を先に閉じるよう修正し、最終12unitは15.804秒で合格した。
GUIの最初の機械的挿入位置はnode --checkで検出して修正し、実ブラウザーは修正後のソースで実行した。

独立 `scripts/validate_hphi_study.py` は18worker・36FEM点・18 CLI再生・18点取込・再起動36ジョブでPASS。
両幾何・両次数の尺度/規格化/導電率則は最大相対差4.860e-14。全18系列は113.797秒。
円筒の内外半径/長さ変更は、TEMの独立解析f/E/H/G/Q/P・全壁積分と既存の次数別ゲートで確認した。
最大の記録誤差8.178e-3は各量の最大をまとめた診断であり、すべての量にその一つの閾値を適用してはいない。
小メッシュの相似則確認を新しい離散化精度の受入にしない。

実Chromeの新Study9操作、再起動後の復元/点表示/再実行3操作、既存Hφ8操作、既存TM/TE・平面5操作がPASS。
ブラウザーの定義/結果をCLI/nativeと照合し、再起動前の元30ファイルを保持した。
最終の14完了・2取消ジョブ、以前のnative 30ファイル不変、2 CLI再生とブラウザー保存全文の一致をout/hphi-study-browser-verification-20260912へ記録した。全ブラウザーとサーバーは終了済み。
全体回帰はout/validation-hphi-study-candidate-20260912で完了し、下記の範囲で主ツリーへ受け入れた。

証拠はout/hphi-gui-development-20260912/study-*.log、out/hphi-study-independent-first-20260912、
out/hphi-study-development-20260912、out/hphi-study-browser-first-20260912、out/hphi-study-browser-restored-20260912、
out/hphi-study-existing-hphi-browser-20260912、out/hphi-study-existing-tm-te-browser-20260912。
新規外部資料・依存・旧版参照なし。自作PlanarStudyの所有/保存操作を明示Hφ形式へ接続した。
Hφの収束・追跡・調整・最適化、軸接続の穴付き領域・曲線内導体、親P03/O02と全計画は継続する。

## 最終受入記録

標準1026件（1023合格・3skip）は1772.387秒、ResourceWarningなしでPASS。
skipは任意NGSolve参照2件とsandboxのローカルHTTP待受1件。実HTTPは許可されたGUI検査と固定候補の実Chromeで別途確認した。
主12unitを11.585秒で再実行し、同梱2例題の4実CLI・保存Project/全点native再生・公開read_jobが合格した。
既存seed9モード19量はf差0、最大相対差8.882e-16。ベンチマークは更新していない。
主統合前後で589検証sourceと不変egg-info 6件を照合。証拠はout/validation-hphi-study-candidate-20260912/seed_regression.jsonとout/hphi-study-main-examples-20260912。
内部作業用アーカイブはout/hphi-study-development-20260912/frozen-candidate-source.tar.gzとarchive.json。
