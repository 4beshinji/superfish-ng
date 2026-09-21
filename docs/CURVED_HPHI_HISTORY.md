# 所有曲線Hφ履歴と過去anchor ID回復

2026-09-22。H13-d継続。曲線専用の順序付き履歴、所有保存、worker作成/延長と明示回復、追跡/履歴CLIを追加。GUIと曲線調整回復の所有操作受入は後続。H13-d/親H13/全goalは未完了。

## 契約

`CurvedHphiTrackingHistoryRequest`は厳密版1（通常履歴）/版2（明示回復配置）を持つ。所有pairの全native五ファイルが隣接してbyte一致すること、追跡帯数、個別IDまたはID集合の継承、全祖先の再生、max_stepsを検査する。最後の対応がUNVERIFIEDなら延長不可。PASSでも未解決の集合を個別IDへ置き換えない。

`CurvedHphiIdentityRecoveryRequest`は過去snapshot番号と完全二次領域のanchor比較要求を持つ。写像は比較要求に一度だけ宣言する。履歴はその番号を所有nativeへ結び、anchorの過去個別ID順序が明示要求と一致することを検証する。未確認anchor・未来anchor・既に個別解決済みの継承への回復は拒否する。継承E/HがUNVERIFIEDならanchor比較で迂回できない。anchorの個別候補は継承各ID集合と完全一致する場合だけ回復成功となり、成功時だけ後続へ個別IDを渡す。

回復eventには継承/anchor双方の再計算結果、各集合の整合、anchor/currentの元native hashを保存する。順序付き履歴の保存は全pair・要求・履歴結果を所有し、新規出力への延長で全祖先を再検証・コピーする。公開再生は元pathに依存しない。manifest、状態、全所有hashを照合し、workerは実行前後の実装/入力hashを確認する。

これらは保存された離散snapshotの対応であり、縮退を通る連続物理branchの一意性・連続誤差上限は主張しない。未確認状態を小さな代数残差や周波数順位で上書きしない。

## 検証

標準環境は`OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-uv-cache uv run --no-sync --python .venv/bin/python python -m unittest -v ...`。証拠はignored `out/h13-curved-history-20260922/`。

- `before.log`：専用回復モジュール未実装によるimport失敗、終了1。
- `after.log`：新履歴2件PASS、1187.356秒、終了0。実二次shear同軸の順位交換、保守的ID集合、過去anchor回復、後続worker延長、全祖先byte保持、元pair移動、管理器再起動、偽回復結果拒否、strict/future/wrong-ID/guard停止。
- `continuity.log`：追加1件PASS、169.327秒、終了0。通常版のID集合保持/max_steps停止と隣接native不一致拒否。
- `regression.log`：旧`test_hphi_tracking_history`全4件と旧回復履歴のstrict/failed-recoveryケース1件、計5件PASS、371.954秒、終了0。

fixtureは合成二次shearで、直線同軸TEMのcos場を明示写像で移送した近似物理対照との質量内積>.999を独立確認する。二次境界で直線式を厳密固有解とは扱わない。既存solver、曲線追跡核、RF/正規化、許容差に変更なし。全suite/seed/GUI検証は本段階に含まない。

## 来歴

既存自作の直線履歴・所有copy/worker・集合整合判定を曲線pairと元E/H比較へ接続した。新外部資料・依存・legacy参照なし。写像や場を直線近似へ置き換えていない。

## CLI接続

専用の`execute-curved-hphi-tracking`/`replay-curved-hphi-tracking`、`execute-curved-hphi-history`/`extend-curved-hphi-history`/`replay-curved-hphi-history`を追加。要求は専用版だけを受け入れ、既存直線コマンドの契約を維持する。JSON結果を返す検証コマンドは計算完了0・不正要求/拒否2とし、物理PASS/UNVERIFIEDと延長可否は結果で確認する。

`test_curved_hphi_history_cli`を準備し、`out/h13-curved-history-cli-20260922/before.log`で未登録コマンドによる失敗（終了1）を再現済み。長時間履歴検証の全handle終端確認後にCLIを接続した。数値・保存処理は不変。実CLI2件は`after.log`でPASS、85.902秒、終了0。旧非一様追跡CLIの保存/移動後再生1件は`compatibility.log`でPASS、24.491秒、終了0。新履歴3件＋新CLI2件、関連履歴5件＋旧CLI1件の分割証拠を確認し、全handle終端。CLI接続後は数値・所有保存実装が不変の成功証拠を再利用した。


```sh
uv run --no-sync python -m superfish_ng execute-curved-hphi-tracking PREVIOUS CURRENT tracking.json --out out/new-pair
uv run --no-sync python -m superfish_ng replay-curved-hphi-tracking out/new-pair
uv run --no-sync python -m superfish_ng execute-curved-hphi-history history.json --steps out/new-pair --out out/new-history
uv run --no-sync python -m superfish_ng extend-curved-hphi-history out/new-history NEXT_PAIR --out out/new-extended
uv run --no-sync python -m superfish_ng replay-curved-hphi-history out/new-extended
```

各出力pathは未使用であること。履歴延長は既存の回復配置を保存し、全祖先を新出力で所有する。新しい回復配置を追加する場合は全配置を持つ明示版2要求から新しい履歴を作る。
