# RF設計制約の評価基盤 — D03の部分実装

`superfish_ng.rf_design`は一つの形状の保存済み場とモード追跡履歴から、
目的関数一つと複数のRF制約を評価する。[曲線2変数探索](RF_OPTIMIZATION.md)へ接続済み。最適性の証明は行わない。
初期形状と最終候補にそれぞれ独立した細分履歴を作り、このAPIを適用するための基盤である。

```python
from superfish_ng.rf_design import save_rf_design, read_rf_design

criteria = {
    "schema_version": 1,
    "objective": {"quantity": "r_over_q_accelerator_ohm", "direction": "maximize"},
    "constraints": [
        {"quantity": "frequency_hz", "lower": 1.0e9, "upper": 1.1e9},
        {"quantity": "epk_over_eacc", "upper": 3.0},
        {"quantity": "bpk_over_eacc_mt_per_mv_per_m", "upper": 5.0},
    ],
}
# history: 既存の保存追跡履歴。数値は使用者が指定する設計条件の例。
report = save_rf_design(history, "fundamental", criteria, "new-design.json")
verified = read_rf_design("new-design.json")
```

版1の必須項目はschema_version/objective/constraints。目的関数の方向は
minimize/maximize、制約はquantityとlower/upperの少なくとも一方。
非負・有限の境界値を含む閉区間とし、未対応量・重複制約・未知項目・bool・
暗黙の単位換算は拒否する。同じ量の上下限は一つの制約にまとめる。

| quantity | 単位 |
|---|---|
| frequency_hz | Hz |
| r_over_q_accelerator_ohm | Ω、加速器定義 |
| r_over_q_circuit_ohm | Ω、回路定義 |
| geometry_factor_ohm | Ω |
| epk_over_eacc | 無次元 |
| bpk_over_eacc_mt_per_mv_per_m | mT/(MV/m) |

場の再読込・個別モード対応・同じ元メッシュと二次幾何・厳密に増える細分段数を
既存の[surface_convergence](SURFACE_CONVERGENCE.md)で再検証する。
その最後の2回の周波数/RQ/G/両ピーク比の停止条件、滑らかさ診断を全て要求する。
設計条件を緩くしても既存の細分許容差は変わらない。局所履歴や直線P1/P2など、
この既存評価器が受け付けない経路への対応は今後の課題。

各設計量は最後の3メッシュの離散区間の包絡で評価する。回路R/Qは定義どおり
加速器R/Qの半分を外向き丸めで求める。元の保存RF・正規化は変更しない。
周波数・積分RFの一点区間は離散計算値であり、その物理誤差をゼロとは主張しない。

- 包絡全体が制約内ならMET。全体が外ならVIOLATED。境界と重なればUNRESOLVED。
- 元の細分/形状診断が未達、または必要な区間が欠けていれば全体はUNVERIFIED。
- 全制約METかつ既存診断TARGETS_METの場合だけCRITERIA_MET。
- CRITERIA_METだけがeligible_valueを持つ。最大化では包絡の下端、最小化では上端。
  その他はnullなので、未達/未確認の試行へ有利な値を与えない。

この包絡は観測された3メッシュの範囲であり、真の物理量の包含保証ではない。
二次境界と解析境界の差の受入、絶対物理誤差、一般形状の正則性は証明しない。
保存文書は履歴・場から再構築して全項目を照合し、採用値や受入結果の改変を拒否する。
書込は新規ファイルだけ。評価APIを使う曲線2変数探索のCLI・全試行記録・予算/停止/再開・初期/最終の
実細分を接続。探索のJobManagerは接続済み。単体評価のCLI/GUIと探索のGUIは未接続。D03親課題は進行中で未受入。

## 検証

独立不変量は区間包含、両R/Qの定義比、Maxwell相似則、球形TMの解析RF。
広い区間の有利な片端だけによる受入、未収束結果の採用、保存判定の改変を拒否する検査を置く。
`scripts/validate_rf_design.py --out out/<new-name>`は両尺度・異なるエネルギー正規化の
球形実FEMを新規実行する。解析値の±5%を設計条件として先に指定し、既存のより厳しい
細分停止と独立解析検査も要求する。周波数を意図的に範囲外とした入力は採用値nullを要求する。
この例題名や解析式を製品の評価分岐には使用しない。

## 探索への接続

[RF_OPTIMIZATION.md](RF_OPTIMIZATION.md)で、同じ曲線Projectを元にした半径/軸方向の複数設計変数と
明示範囲を持つ有限予算の探索へ接続する。各候補の形状間対応は相対アフィン写像で
導出し、順位を固定IDと取り違えない。各候補で本評価を使う場合も、初期形状と
最終候補の実細分結果・条件・全試行・失敗を記録する。未確認候補は採用しない。
制約違反から実行可能領域へ移る探索方針、探索停止と細分未収束の別状態、
全FEM呼出しを含む予算、途中保存と再検証を実装した。一般変数・形状の対応は残る。
単一の重み付き和で異なる単位の制約を混ぜたり、解析解でFEMを置換したりしない。

## 今回の実行証拠 — 2026-09-09

基準3b80839。開始時の既存表面収束5件は21.806秒でPASS。追加検査の初回は
5件中2ERROR（quantityに配列を与えた際のTypeError）。数量名の型を明示検査して
actionableなValueErrorへ修正し、5件21.539秒でPASS。初回ログも保持した。

独立実行 `out/rf-design-independent-20260909` は終了0。球形の両尺度・各3水準
36/144/576要素、正規化1/4 Jの実FEM。既存の独立球形解析の最終相対差は
f最大2.483e-5、RQ 6.489e-6、G 8.807e-7、Epk/Eacc 2.657e-4、Bpk/Eacc 3.847e-5。
6量全ての設計制約・保存再検証と、意図した周波数制約違反での採用値nullを確認。
包絡のMaxwell相似差最大4.930e-14。実行中417対象ソースは不変。
新規CLI/GUI/ブラウザーの検証は行っていない。

最終標準 `out/validation-rf-design-20260909` は終了0。729件中727合格・2skip、
unittest 612.057秒。seed9モード19量の周波数差0、RF相対差最大8.882e-16。
標準/独立/その内部の球形FEM/終了後の417対象hashが一致。
`seed_regression.json`と照合driverを同ディレクトリに保存した。
全関連実行終了、ソース固定解除。親集計は8受入・8進行中・16他未受入・1候補、計33。
D03と全体計画は未完了。
