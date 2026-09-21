# 材料E/H比較の所有保存・worker・CLI

最新進捗：[独立所有履歴](MATERIAL_HPHI_HISTORY.md)と[材料調整CLI/worker](MATERIAL_HPHI_TUNING_OPERATIONS.md)の基本操作検査まで成功。回復/最終細分の所有操作統合とGUIは残る。以下の初期段階の記録は当時の検査範囲を示す。

2026-09-22。H16-cの二状態比較を所有保存と操作へ接続した。独立追跡履歴、調整worker/CLI、回復を含む履歴・調整操作とGUIは残る。

`execute_material_hphi_tracking(previous,current,request,directory)`は専用材料nativeまたは検証済みHphiジョブ二つと、完全な`MaterialHphiTrackingRequest`を受け取る。各元Project/nativeを検証してから、未使用出力のprevious/currentに自己完結したimport済みジョブとしてコピーする。元の表示単位を含むProject bytes、native bytes、コピー元descriptorを保持する。

出力作成前に元Caseと三つの材料比較宣言を照合する。全領域/界面・同領域比較空間の細かさ・次数・DOF・計算済みguard・モード/点/界面予算を検査する。真空/曲線Caseを材料nativeの代用として受け入れない。

workerは完全なqueued入力と単独claimを要求し、元E/Hと有限スペクトルから対応を計算する。入力/実装hashの前後一致を検査し、tracking-results、manifest、job状態を保存する。`read_material_hphi_tracking`は元コピーの物理検証、全要求、E/H・スペクトル再生を行い、単に再hashされた偽の結果も拒否する。

`JobManager.start_material_hphi_tracking`は専用workerを起動し、既存の中止・再起動・状態再検証へ接続する。種類の判定はkindだけでなく専用要求/結果formatも見る。kind偽装で別の検証経路へ降格させない。元コピーを材料Hphi Projectとして再importでき、旧コピー元が移動しても比較結果を物理再生できる。

公開CLIは`execute-material-hphi-tracking PREVIOUS CURRENT REQUEST --out DIRECTORY`と`replay-material-hphi-tracking DIRECTORY`。実行完了と数値PASSを区別し、guardが未確認なら結果のUNVERIFIEDとnullの個別IDを保持して表示する。

## 検査記録

`out/h16-material-tracking-jobs-20260922/before.log`でAPI未実装のred。`initial.log`は新3件、140.995秒PASS/終了0。

- managed/native混在入力、元全bytes不変、Projectの表示単位とコピー保持、元ソース移動後の再生、所有sideの再import、結果を改変しmanifest hashを再計算しても拒否。
- queued要求変更、worker再入、linked native、不適切な比較DOF/点予算、真空sourceの誤入力を拒否し、失敗前の出力を完了として公開しない。
- 実workerの中止、別workerの完了、管理器再起動後の状態検証、job/manifest kind偽装拒否。

`cli.log`では材料CLIが曲線要求クラス名を参照するImportErrorを再現した。実行中のworkerの実装hash検査を終えてから、材料CLIブロックの参照二箇所を専用クラスへ修正した。新CLI検査は実行/再生の結果一致とUNVERIFIED保持を確認する。関連は既存Hphiジョブの実CLI/単位/二native型と、kind降格・再hashされたProject/RF改変拒否。

`cli-fixed-related.log`は修正後の新CLI1件＋関連2件、45.962秒PASS/終了0。新4件は分割実行証拠。全handleと実workerが終端し、実装固定を解除した。CLI修正前の保存/worker成功と修正後の公開CLI成功を混同しない。

## 来歴と範囲

既存自作のジョブ所有コピー・snapshot・worker処理構造を、専用材料比較とpreflightへ接続した。新外部資料・依存・legacy参照なし。jobs/CLIには専用kind/コマンドの分岐を追加し、元FEM core/seed TMは変更していない。検査は新経路と隣接ルーティングに限定し、全suiteや履歴/調整/GUI全受入を主張しない。
