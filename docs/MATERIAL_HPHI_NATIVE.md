# 材料Hφの専用保存・再生・CLI

2026-09-13 JST。[計画](MATERIAL_HPHI_NATIVE_PLAN.md)の固定候補672sourceを主678sourceへ統合し、本書の専用保存/CLI範囲で限定受入。
専用Caseの全材料分割・元メッシュ・P1/P2係数・最低正スペクトル・領域RFを再構築するnative版1を追加した。
case/mesh/fields/resultsと最後にmanifestの5ファイルを公開し、元データを再検証した後に完成とする。
材料係数、界面所有、領域エネルギー、位相・壁金属・両R/Qの規約も再生する。

`solve-material-hphi`、`replay-material-hphi`、`probe-material-hphi`が専用入口。
プローブは元セル・領域/材料ID・epsilon_r/mu_rと全18成分のE/H/Bを保存する。
材料中のB=mu0 mu_r Hを保持し、共有辺では最小元セル番号の片側を使う。元native5ファイルのhashを付す。
既存出力の上書き、native内へのプローブ保存、リンク・欠落、検証中変更を拒否する。

`capabilities.material_hphi_rf`へ専用入口と現在の制約を追加した。
真空Hφの4形式やcanonical Modelの受理範囲は不変。材料Project/GUI/Study/追跡は未対応と明記する。

追加4unitは正半径/軸・P1/P2・PEC穴・真空軸部分区間を保存再生し、材料・界面・所有セル・配列型・場・RF・位相の改変を拒否した。
改変後にhashを作り直しても拒否する。公開直前の入力変更とmanifest前の中断も検証した。
既存能力表の3unitもPASS。

独立操作照合は、RFを別検証済みの24材料Caseを用い、48native保存・78CLIを実行した。
API/CLIの全5ファイルとプローブJSONが一致。材料を含む元E/H/Bソースが前段の固定候補から不変であることもhashで確認した。
元native240ファイルと独立参照25ファイルは不変。CLIの能力表と実コマンドhelpも照合した。
これは保存・操作の検証であり、物理精度の証拠は[MATERIAL_HPHI_RF.md](MATERIAL_HPHI_RF.md)を参照する。

標準1122件は`out/validation-material-hphi-native-candidate-20260913`へ終了0。主ツリー統合・4unit/24例78CLIもPASS。
証拠は`out/material-hphi-native-development-20260913`、`out/material-hphi-native-independent-20260913`。
新規外部資料・依存・旧版実行なし。材料GUI、損失/分散、旧版照合、P04と全計画は未完。

標準は2205.237秒、1119合格・任意NGSolve参照2件/HTTP環境1件skip、ResourceWarningなし。
主4unitは4.105秒、主独立照合は56.966秒。候補672sourceと不変egg-info 6件を加えた主678sourceを照合。
既存の周波数/RFしきい値とベンチマークは不変。統合証拠は標準出力内seed_regression.json。
