# TE Projectとローカルジョブ

後続追補（2026-09-09）：[鏡映TEの元半領域収束比較](TE_REFLECTED_CONVERGENCE_PLAN.md)を同じ元物理/同じ対称条件に限定して接続した。以下の当時の未対応記録より、この追補を優先する。鏡映部分スペクトルの追跡は未対応のまま。

2026-09-09追補: [TE対称面鏡映](TE_REFLECTION_PLAN.md)を接続。TEのEφは磁気対称面で偶、電気対称面で奇、Hrは逆符号、Hzは同符号。元振幅を維持しU/PEC損失は2倍、f/Q0/Gは不変。専用native版4で元半領域から再構成・再検証し、API/CLI/Project/Job/GUIで部分スペクトルと明示する。鏡映結果の追跡/収束比較は未対応。標準790件（788合格、2skip）と既存TM/TE数値回帰まで限定受入済み。

2026-09-09追補: [通常TE GUI](GUI_TE.md)の場表示・プローブ・偏波選択を接続。Chrome10項目と保存場/独立球形解析の照合が合格、最終標準766件・既存TM/TE回帰も合格。以下の初期実装時のGUI保留記録とは区別する。

2026-09-09、基準d2d53de。O02の追加物理統合。
直線P1/P2・曲線P2の明示TE Caseを通常Project/JobManagerへ接続する。
GUIのTE入力選択・TE場表示、Study/追跡/調整/最適化、場の鏡映構築は後続工程。

## 契約

ProjectのTE Caseは従来のSI・ピークphasor・Eφ/r未知数・加速量N/Aを保持する。
TEでreflect_fullを指定すると、明示した全領域の入力を求めるエラーを返す。
通常の外部mesh_dataはProject版2で保持する。run-projectはProject JSONに加え、既存のCase JSONも受理する。

```sh
superfish-ng run-project examples/te/pillbox.json --out out/te-job-new
superfish-ng replay-te out/te-job-new/solution
```

通常workerは同じsolve/save_runを使い、入力・実装の変更がないことを確認してジョブを完了公開する。
read_jobはTE宣言/TE保存を検出したとき、TE専用完了markerと全必要ファイルを外側manifestにも要求し、
read_te_runによる場・境界・規格化・RF再検証を行う。Projectと保存Case、明示mesh_dataと保存元メッシュの一致も要求する。
ハッシュだけを書き換えた不正な組合せを受理しない。TMのread_solutionはTEを拒否するままで、uへの別名は導入しない。
ジョブのcompleteは計算・保存の完了であり、独立物理検証や収束合格を意味しない。numerical_validationはnot_checkedのまま。

JobManager.import_resultは直接TE nativeと管理済みTEジョブを再検証してコピーする。
必要な直線版2/曲線版3ファイルを保持し、te_complete.jsonを最後に公開する。
コピー前後の元ファイル・管理済みProject/manifest/job状態の変更を検出し、不完全な取込はfailedとして残す。
取込はorigin=importedで、新規FEMと表示しない。
直接nativeからは元メッシュを持つProject版2を生成するため、Caseの通常生成設定と異なるメッシュでも再実行時に失われない。
管理済み結果からは検証済みの元Projectを保持する。

TE Study・周波数調整・RF最適化はそれぞれ入口で未接続の旨を返す。
既存GUIは読込時の明示モデルを保持するが、TE場描画やTE専用操作をまだ受入していない。
今回GUI/ブラウザー操作の新規検証は行っていない。

## 受入条件と初回検証

- P1/P2/曲線P2の通常Project/API/nativeの係数・RF量一致。
- 実worker中止後の再実行、管理器の再起動、管理済み曲線結果の取込。
- 直接nativeの外部元メッシュ保持と再実行、管理済み取込後のProject一致。
- 外側manifestから曲線geometryを隠す変更、Project Caseや元メッシュの不一致、全hashを更新した不正係数を拒否。
- 取込途中の元ファイル変更時に完了markerを公開しない。
- 通常CLIの円筒6モード/球形3モード×2尺度を独立f/場/G/エネルギー・相似則で確認し、CLI/API一致、直接/管理済み取込、再起動後再検証を行う。
- 最終標準、既存TM seed9モード19量、旧TE直線/曲線の保存再読込、検証時/終了後ソース一致。

開始時は直前標準755件中753合格/2skipと現在440対象hash一致を確認した。
TE Project往復の最初の実行は従来の全TE拒否でFAIL（/tmp/te-project-red-20260909.log）。
新規7検査の初回は、改変テストが上書き禁止Project.saveを使ったため1ERROR。
改変を直接記述するテストへ修正し、7件1.766秒でPASS。元メッシュ不一致の追加確認後も7件1.736秒でPASS。
既存TE12件2.130秒、通常jobs7件0.913秒もPASS。物理精度許容差は変えていない。

最終受入は以下に記録する。P01/O02の親課題全体と全計画の完了ではない。

## 完了検証中の変更検出

初回独立18269は8実FEM/8取込/再起動・4ケース独立解析でPASS、443対象hash一致。
ただしその後の反例で、TE native再検証が戻ってからジョブ判定が終わるまでにCSVを変更すると、
外側manifestの古い照合だけでcompleteを返すことが分かった。
`out/te-jobs-verification-race-20260909` に実行driverとAssertionErrorを保持する。
未確定版標準53643は確認済みの自分のvalidate/unittestだけを停止（143）し、interruption.jsonを保持した。

te_jobsの完了検証の終点でも全必要ファイルのhash/リンク/存在と外側manifestの一致を再確認する。
native CSVと外側manifestを検証中に変える追加検査を含む8件が1.901秒でPASS。
コピー時の前後検査も維持する。初回独立の物理結果と修正後のジョブ完全性は区別し、
修正版の標準・独立CLI検証を新しい出力先で再実行した。

## 修正版の独立受入

修正版80174終了0、`out/te-jobs-verified-independent-20260909`。
通常run-project CLI4ケースと直接API4ケースの8回の実FEMで係数・周波数・RFが一致した。
円筒6モード/球形3モード×2尺度の独立解析もPASS。

| 最大相対差 | 円筒 | 球形 |
|---|---:|---:|
| 周波数 | 3.509e-7 | 2.500e-5 |
| 場成分 | 1.492e-3 | 1.506e-3 |
| G | 2.505e-3 | 2.824e-3 |
| 電気/磁気エネルギー比 | 7.572e-14 | 1.222e-14 |

Maxwell f/G/Q0相似差最大8.194e-14。直接/管理済みの8取込のProject・元mesh・係数が元CLIと一致。
主driverの再起動後statusは既定verify=Falseであり、状態表示の継続の確認である。
これと混同せず、追加driver `out/validation-te-jobs-verified-20260909/verify_restart.py` を実行し、
再起動した管理器で全8件に明示verify=Trueを指定してProject/保存場/完了manifestを完全再検証した。
追加66118終了0、restart_verified.json/restart.logを独立outへ保持する。
修正版独立・追加再起動検証・現在443対象hashが一致した。標準検証と最終比較もPASS。

## 最終標準・保存回帰

標準763件中761合格・2skip（unittest1158.285秒、command1158.633秒）。独立8実FEM・8取込と再起動後の明示verify=True全8件がPASS。TM seed9モード19量の周波数差0、RF最大8.882e-16、旧直線/曲線TE保存7件のRF差0。標準・独立・再起動検証・終了後443対象hash一致。

`out/validation-te-jobs-verified-20260909` にvalidation.json、tests.log、command.log、verify_completion.py、seed_regression.json、comparison.logを保持する。標準78312は終了0。最終比較のreportはpassed=trueで末尾の全結果を出力済み。全検証終了後にソース固定を解除した。GUIの製品接続・TE追跡は後続工程。
