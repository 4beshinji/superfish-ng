# P02-a — 元平面場による明示ID回復

2026-09-22、開始点 `5aa0ebe`。専用APIの回復核を受入。
P02をa（核）/b（所有履歴）/c（調整）/d（GUI監査）に分割し、原90カードを維持、TSVは115行。
**親P02はIN_PROGRESS**。所有履歴/調整/worker/GUIの接続は子b〜dで完了させる。

実装前に実FEMで幅.18→.20→.22 m、高さ.20 mのTE矩形列を確認した。
正方形からの継承比較はPASSでも個別IDは[null,null]、縮退前からの直接比較は['x','y']となった。
`out/p02-planar-recovery-20260922/baseline.json`に両状態と固有周波数/独立解析値を保持する。
これは既存の集合保持の誤りではなく、明示回復APIがなかった状態の確認である。

## 要求と判定

[PlanarIdentityRecoveryRequest](../src/superfish_ng/planar_identity_recovery.py)は
format `superfish_ng_planar_identity_recovery_request`、recovery_version 1、
非負anchor_snapshot_index、完全なPlanarTrackingRequestを保存する。
anchor比較には解決済みの個別IDを明示し、集合による置換は拒否する。
既存平面追跡版1〜8の写像/controlsを保持する。

`recover_planar_modes(anchor, previous, current, inherited_request, request, current_snapshot_index=...)`
は継承比較とanchor比較を両方とも元FEMから計算する。
継承部分空間がUNVERIFIEDならanchor比較を実行せず停止する。
既に個別IDが完全な継承状態には回復を適用しない。
両比較の現側帯域数を一致させ、anchor比較が全個別IDを解決し、かつ
全ての候補IDが各継承集合と厳密に一致した場合だけPASSとする。

判定には既存の物理非依存 `assess_identity_recovery` を再利用する。
数値比較は平面専用の元E/xy面積/U′[J/m]、上側guardと有限細分診断を通り、
軸対称の体積測度や材料HφのE/H比較を代用しない。
周波数順位をIDとせず、回復後のIDで参照する周波数辞書 `recovered_frequencies_hz` をPASS時だけ作る。
失敗時は辞書をnullに保ち、継承比較・候補比較・集合判定を別々の証拠として残す。

この核の位置検査はanchor<currentまで。
**所有履歴が位置を実際の過去の解決済みnativeへ束縛する検査はP02-bの責務**であり、
任意の呼出元が与えた位置だけから履歴連続性を認証したとは扱わない。
回復は明示した過去場への再同定で、縮退点を通る連続的な物理枝の証明ではない。

## 独立検査

[test_planar_identity_recovery](../tests/test_planar_identity_recovery.py)の4件を分割PASS。
実P2 FEMの幅.18/.20/.22/.23 m、高さ.20 m、6×6分割・3モードを使う。
TEの独立遮断周波数c/(2w), c/(2h)を相対1e-4で照合し、元電場の
xモードEy∝sin(πx/w)、yモードEx∝sin(πy/h)との規格化相関>.999を確認した。

- 縮退前の['y','x']が順位交換後['x','y']へ回復し、幅.23 mへの後続比較も同じIDを継承。元係数/周波数の全配列は不変。
- 現側が真の正方形縮退ならUNVERIFIED。継承集合と異なるanchor IDもUNVERIFIEDで、回復周波数はnull、元集合を保持。
- 継承側guard未確認ではanchor比較を呼ばない。anchor側guard未確認でも回復ID/周波数を採用しない。
- strict要求往復、bool/余分な項目、解決済みIDのないanchor、同時刻/未来anchor、異なる現側帯域を拒否。

ログは `out/p02-planar-recovery-20260922/`。
`kernel-tests.log`初回4件5.372秒は3PASS/1FAIL。FAILはcurrent_snapshot_index=0の
先行する整数下限検査に対して、テストが後段のanchor位置エラー文を期待したため。
製品は変更せず、ゼロ位置の拒否とanchor=currentの拒否を別々に確認するよう修正した。
`strict-fixed.log`でその1件を再検査してPASS。初回失敗は保持している。

実行prefixは `OPENBLAS_NUM_THREADS=1 PYTHONPATH=.:src:tests UV_CACHE_DIR=/tmp/superfish-uv-cache uv run --no-sync --python .venv/bin/python python -m unittest -v`。
新規APIとテストだけで、既存solver/追跡/保存のソースは無変更。全suite/seed validatorは実行していない。
既存の集合評価器と平面FEM/場比較を再利用。新しい外部資料、依存、旧版実行はない。
次はP02-bの回復付き所有履歴・CLI/workerで、完全な祖先とID継承を束縛する。
