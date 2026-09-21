# Hφの明示個別ID回復（H10）

H10-aの数値回復核を受入済み。[所有履歴event・後続継承（H10-b）](HPHI_RECOVERED_HISTORY.md)は受入済み。調整の検索/最終細分（H10-c）は未接続で、親課題は未完了。

## 回復核の契約

`hphi_identity_recovery.HphiIdentityRecoveryRequest`は0始まりの`anchor_snapshot_index`、完全な`HphiTrackingRequest`、`same_vacuum`またはH08の完全な明示幾何写像を保存する。anchor側は個別ID宣言が必須で、ID集合を個別名へ読み替えない。未知キー・bool index・不正version・推測mappingを拒否する。

`recover_hphi_modes(anchor, previous, current, inherited_request, request, current_snapshot_index=..., inherited_mapping=...)`は両対応を元FEM場から再計算する。呼出側の作成した対応reportを受入証拠には使わない。

1. anchor indexは現在snapshotより前でなければならない。比較対象の現在band数を継承比較と一致させる。
2. previous→currentのE/H部分空間対応を再計算する。UNVERIFIEDならanchor比較を実行せず停止する。すでに全個別IDが確認済みなら、不要な回復要求を拒否する。
3. anchor→currentを独立の比較要求・写像で再計算する。元領域の有限スペクトル診断、上側guard、E/Hの両一致を維持する。
4. 全個別IDが確認でき、かつ各継承集合の候補ID集合が厳密一致した場合だけPASSとして個別IDを返す。失敗時は継承集合を保持する。既知のsingletonを表示用に保持してもstatusはUNVERIFIEDであり、後続継承の許可ではない。

返すeventは継承比較・anchor比較・集合別検査を区別する。継承対応が失敗した場合、anchor比較と集合検査はnull。これは離散snapshot間の場の再同定で、縮退を通る連続分枝の一意な履歴証明ではない。

この核単独ではindexと実際の過去の所有snapshotとの結び付けを証明しない。それは[H10-bの履歴所有側](HPHI_RECOVERED_HISTORY.md)が検証する。現在の専用履歴版1は暗黙の集合→個別ID変更を引き続き拒否する。専用履歴のCLI/worker/GUIは所有再生からこの核を呼ぶ。調整への接続はH10-cで行う。真空直線の軸接続u/正半径qに限定し、曲線・材料の回復を受入済みとは呼ばない。

## 独立物理対照

内半径1/16 m、外半径1/8 mの同軸空洞について、既存`validate_coaxial.radial_roots`のBessel境界条件の最初の径方向根をkとする。

- TEM：f=c/(2L)、q=cos(πz/L)。
- 径方向モード：f=ck/(2π)、q=r[Y₀(ka)J₁(kr)−J₀(ka)Y₁(kr)]。
- L=π/kで縮退し、その1.15倍/0.85倍では両モードの実順位が交換する。

各場は実FEMで計算する。解析周波数との相対差1e-4、q質量重なりと縮退部分空間の最小特異値0.999を別に検査する。縮退からの通常追跡はPASSでも個別IDがnullのままで、過去の非縮退anchorからだけ正しい交換を回復する。縮退anchor、anchor/継承側のguard混入、集合外ID、集合境界をまたぐIDは回復失敗の対照とする。係数と元周波数は不変。

新たな外部資料・依存・legacy参照はない。既存の同軸解析関数とH09の明示写像・E/H比較を使用した。数値solver、比較の既定値、許容差を変更していない。

## 検証記録（2026-09-21）

`out/h10-core-20260921`にrawを保持する。変更前は解析順位交換・既存追跡のID集合保持を確認した後、未実装の回復APIのimportで失敗した（`before.log`、9.743秒、終了1）。既存物理計算の誤答を修正したという意味ではない。

初期4件は88.029秒PASS（`after.log`）、解析場/集合境界/anchor guardの追加3件は21.197秒PASS（`additional.log`）、いずれも終了0。軸接続/正半径の同領域独立メッシュ1件は53.048秒PASS（`same-vacuum.log`）、終了0。新規計8件の分割証拠。既存履歴の暗黙ID付替え拒否1件も123.646秒PASS（`history-regression.log`）、終了0。全検証handle終端。

実行方法は`OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-uv-cache uv run --no-sync --python .venv/bin/python python -m unittest -v <case>`。新規module `test_hphi_identity_recovery`、既存対象 `test_hphi_tracking_history.HphiTrackingHistoryTests.test_native_spectrum_and_identity_continuity`。分割実行を全suite検証と呼ばない。seed TM・GUI・Hosted CIの検証は本変更の証拠に含めない。
