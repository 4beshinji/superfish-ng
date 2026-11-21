# Hφ調整の明示個別ID回復（H10-c、受入済み）

検索試行と最終細分で、継承部分空間がPASSでも個別IDが未確認の場合に限り、明示した過去の確認済み試行から回復を試みる。比較親の`parent_trial_index`と回復の`anchor_trial_index`を別々に記録する。回復前のraw対応は変更せず、成功したanchor比較の個別対応だけから対象周波数を評価する。

## 要求と停止条件

`superfish_ng_hphi_tune`要求版3は版1/2の全フィールドに`identity_recovery`を追加する。元の幾何法則は一様尺度・同軸寸法・明示直線頂点変位を引き継ぎ、曲線/未対応物理を追加しない。[要求例](../examples/hphi_tune_identity_recovery.json)を参照。

- `anchor_selection=latest_resolved_trial`は、実行済みかつ全個別IDが確認された最後の試行を選ぶ。
- `anchor_selection=fixed_trial`は、明示した0始まりの`anchor_trial_index`を選ぶ。回復時点より前の確認済み試行でなければ停止する。
- `controls`には完全なHφ対応制御を要求する。余分なフィールド、欠落、比較予算超過は拒否する。

元の対応がguard等でUNVERIFIEDの場合はanchor比較を呼ばない。anchor比較も実E/H場から再計算し、全個別IDの確認と継承群ごとの集合一致を回復核と同じ判定で要求する。縮退・集合外・未解決anchorは周波数/目標誤差を未評価のまま停止する。連続分枝の一意性は主張しない。

一様尺度は既存の尺度付き周波数比較規約を保つ。非一様形状では、anchorと現在試行の元の未細分Projectから宣言写像を作り、最終細分されたFEMにも対応させる。保存再生は所有nativeから全先行試行を再計算するため、入力reportのID宣言を信用しない。要求版1/2の出力に回復eventは加えない。

## 独立物理対照

半径0.0625/0.125 mの同軸を用い、独立Bessel根から径方向モードとTEMの交差長を決める。短い空洞と長い空洞では実順位が交換する。継承の相対cluster gapを保守的な0.04、明示回復を既定0.001に設定する。これは継承をより広く群化する宣言であり、既存の許容差を緩和していない。

交差長の0.99倍における検索試行と最終細分の両方で、raw対応のIDは未確認のまま、独立anchorが個別TEMを回復する。解析周波数`c/(2L)`への相対誤差3e-4以内と、解析q場`cos(pi*z/L)`との質量overlap 0.999超を個別に検査する。固定anchorと最新確認anchorの両方を検査する。

対照として正確な交差長では、回復のcluster gapを0としても有限要素スペクトル区間が重なり、個別IDは回復しない。guard失敗・未来anchor・比較予算超過も確認する。

## 検証記録

実行環境は既存`.venv`、`OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-uv-cache uv run --no-sync --python .venv/bin/python python -m unittest -v ...`。

`test_hphi_tuning_identity_recovery.HphiTuneRecoveryTests`の新6件を3+2+1の分割で実施し、239.873秒、23.860秒、6.163秒でPASS、すべて終了0。版3未対応の変更前失敗1件（26.492秒、終了1）を含め、`out/h10-tune-recovery-20260921`に記録した。保存/workerと既存調整の回帰、実ブラウザー受入は進行中であり、この時点ではH10-c/親H10を完了扱いしない。

新規外部資料・依存・legacy参照はない。H09の形状対応とH10-aの集合一致判定を再利用する。新たなsolver近似や周波数補正を追加せず、seed TMの定式化を変更しない。全suite/seed/Hosted CIの実行証拠にはしない。

所有保存の新1件`test_hphi_tuning_identity_recovery_saved`は591.732秒PASS、終了0。CLIの検索3試行から実workerで最終細分へ再開し、prefix・要求・元native/RFを保持した。元出力移動後のsolverなしCLI再生、anchor event/要求policy改変の拒否、全24所有ファイルのbyte一致を検査した。`out/h10-tune-owned-20260921/accepted.json`に結果を保持する。

GUIは検査用JobManagerがworkspaceを所有中の起動を拒否した（終了2）。保存検査終了後の起動は成功。最初のChrome実行は検証器がページ初期化前に変数を参照して終了1となった。`typeof`による待機を追加し、新規出力先`out/h10-tune-browser-20260921-replay`で実行中。初回失敗は`out/h10-tune-browser-20260921/report.json`に保持する。製品コードの変更や数値再実行はしていない。

既存の`test_hphi_tuning test_hphi_shape_tuning test_hphi_tuning_saved test_hphi_shape_tuning_saved test_hphi_tuning_jobs test_gui_hphi_tuning`計25件は713.852秒PASS、終了0（`regression.log`）。CLI拒否検査内の意図したerror出力をテスト失敗と数えない。新7件と既存25件は別実行の証拠。

## 親H10の条件別監査

| 元の受入条件 | 証拠 |
|---|---|
| 宣言した過去個別場と継承集合 | H10-aのstrict要求・両比較再計算、H10-bの所有snapshot/当時のID順照合、H10-cの過去試行限定policy |
| 独立順位交換と縮退対照 | H10-aのBessel/TEM両周波数・解析q場・縮退部分空間、H10-cの解析TEM検索/細分と真の縮退停止 |
| 全個別対応と集合一致 | H10-aの全群一致・集合境界/集合外拒否を共通判定として履歴と調整が使用 |
| 部分空間未確認やguard不足を迂回しない | H10-aの両側guard、H10-bの停止後延長拒否、H10-cのguardでanchor未呼出と周波数未評価 |
| 成功IDだけを後続へ継承 | H10-bの回復後pairへの実継承、H10-cの検索回復から最終細分への継承。raw対応は保持 |
| 検索/最終細分とanchorの分離 | H10-cの親0/2とanchor1/2、固定anchor0の対照。所有再生のevent改変拒否 |
| 保存・操作と元RF保持 | H10-bのCLI/worker/Chromeと所有48ファイル、H10-cのCLI/worker/Chromeと所有24ファイル（下記） |

曲線・材料・連続分枝保証はこのH10受入範囲に含めない。次の原計画カードはH11（曲線Hφの比較領域）。

## 操作受入と最終照合

`scripts/verify_gui_hphi_tune_recovery.mjs`の再実行はChrome4項目PASS、終了0。検索/最終細分のraw群と回復ID、比較親とanchorの別表示、版3要求のdownload、同じ所有checkpointの2回再読込、回復TEMの実順位2と元native/RF一致を確認した。`out/h10-tune-browser-20260921-replay/report.json`と`native-field.png`を保持し、画像を目視した。外部HTTPは0。新規FEM候補は生成していない。

最終`acceptance.json`で全350実装hashと24所有ファイルhashの不変を確認した。数値検査開始後のsrc変更はない。全検証handleとGUIサーバーは終了0。途中のブラウザー状態読取は、最後に既に終了したChromeへ接続を試みて終了13となったが、受入検証本体は先に終了0しており、数値/製品の失敗ではない。

新7unit（6+保存1）と既存25unit、Chrome4項目の分割証拠によりH10-cと親H10を受入。H10-a/bの受入済み証拠は変更していない。全計画goalは継続する。
