# D06第一工程：直線TMの多変数候補

2026-10-07：後続の[実native座標探索・D06原条件監査](STRAIGHT_RF_CANDIDATE_SEARCH.md)を受入し、
D06はDONE。以下のIN_PROGRESS記載は第一工程の履歴。RF採用評価はD07で継続する。

2026-10-07、D02の元全境界法則を多変数の候補生成へ接続した。
D06は **IN_PROGRESS**。探索器・実候補の個別ID追跡・所有solve checkpointへの
接続と原条件の全監査は次工程。RF制約の収束評価はD07として残す。
元123カードと互換32要件の範囲を維持する。

## APIと範囲

`rf_optimization_geometry` から次のAPIを利用できる。
入力例は `examples/optimization/straight_candidate_plan.json`。

```python
import json
from pathlib import Path
from superfish_ng.rf_optimization_geometry import (
    prepare_straight_rf_candidates, replay_straight_rf_candidates,
)

request = json.loads(Path('examples/optimization/straight_candidate_plan.json').read_text())
first = prepare_straight_rf_candidates(request, [[1., 1.]])
result = prepare_straight_rf_candidates(request, [[1.1, .9]], checkpoint=first)
assert replay_straight_rf_candidates(result) == result
```

これは幾何候補のAPI。既存 `optimize-rf` 要求版1〜3の能力・保存規約を変更しない。
未対応の直線RF目的/制約を実行入口で受け付けないというD05規約を保持する。
候補要求版1は既存optimization要求版1とは異なる `document_type` を持つ。
候補台帳をRF探索checkpointと偽装できない。

| 要求項目 | 契約 |
|---|---|
| schema_version / document_type | 整数1 / `straight_rf_candidate_request` |
| project | 真空・軸接続TM・閉PEC・非鏡映の未組立元Project。直線profile/段差/単一輪郭。明示solver meshなし |
| variables | 宣言順の非空list。各変数はname/unit/lower/upperだけ。名前一意、SI `m` / `1`、有限増加bounds。全変数が座標式に出現 |
| shape_law | D02の `straight_piecewise_shape_law` 版1。全元Case境界owner、全元比較三角形、名前付きSI式 |
| controls | `piecewise_remesh` の元厳密閾値。比較meshは候補から導出するため入力不可 |
| max_candidates | 正の整数。無効候補を含む台帳の試行上限 |

`straight_candidate_project(request, values)` は実Projectと比較meshを返す。
全座標を元Projectから評価してまとめて更新し、元軸・全境界タグ・段差の共通z・
全比較三角形の向き/被覆を再検証する。候補間の累積変形や変数順に応じた逐次変形をしない。
SI式は既存scalar evaluator、境界owner検査は既存直線tuneと共有する。
既存単変数呼出しの式・規格化・数値計算を変更しない。

## 台帳・失敗・再開

`prepare_straight_rf_candidates` は元要求と値から毎回全候補を再構築する。
再開時も元prefixを再生し、要求の完全一致と全派生値を確認してから追加する。
元checkpoint/inputのオブジェクトは変更しない。値の変更、Project/meshの改変、
assessmentやmode IDの書換えは完全再生で拒否される。

正常候補は `GEOMETRY_VERIFIED`、不正な実形状や範囲外値は `INVALID_GEOMETRY`。
不正候補には理由を保存し、Project/比較meshをnullにする。
上限超過は候補の構築前に拒否する。成功・失敗の両方を試行数へ計上する。
非有限JSON、壊れた要求・未宣言変数・次元不一致は要求段階で拒否する。

全候補の `assessment` と `mode_id` はnull、FEM/RF評価数は0。
GEOMETRY_VERIFIEDは場ID・収束・制約満足・目的改善の証拠ではない。
台帳は有限の明示候補集合だけを扱い、変数区間全体の形状有効性も保証しない。
将来の候補求解/個別ID/失敗solve予算は、別途元nativeへ結合する必要がある。

## 検証と来歴

raw: `out/d06-straight-candidates-20261007/acceptance.json`。
源の実メソッドへ照合した **33個別unit** を分割受入した。新full/seed/legacyは0。

- 新6：3元形状の独立非等方面積 `sr*sz` / 回転体積 `sr**2*sz`、全元境界、
  変数/owner/binding/候補順・分割再開の実形状一致、完全JSON再生・改変拒否、
  dimensioned cross term、正常bounds内の無効中間候補、構築前予算、strict能力。
- 実段差2 FEM：元Hφ/Er/Ez・周波数・G/Q・両R/QのMaxwell尺度則。
  元場相対差最大 **4.498e-14**。離散誤差が小さいという主張には使わない。
- 直接利用25：元直線TM metadata6、TE metadata5、曲線幾何6、固定履歴5、
  探索の未確認不採用/単位/strict/poll3。
- 共有単変数の物理2：元TM Bessel f/H/E/全壁loss/両R/Qと、
  TEの4セクター Bessel f/Eφ/Hr/Hz/全壁loss/N/A。元許容差と細分誤差減少を保持。

`baseline.log` は独立polygon検査を先に実行し、新API不在のImportErrorで終了1。
実装後 `invariant.log` は1件0.036秒、`new-tests.log` は残5件0.334秒、
`direct-consumers.log` は25件9.712秒、全て終了0。
`default-law-physical.log` はTM検査合格の後、誤記したTEメソッド名によるloader ERRORで終了1。
元logを保持し、正しいTE検査だけを `te-default-law-physical.log` で追加実行した
（1件15.094秒、終了0）。全体一括PASSとは記さない。

旧RF幾何の全関数ASTは不変。探索器/checkpoint/六量評価/表面収束の5ファイルはbyte不変。
1188 Python源snapshotは新6検査後・単変数物理検査前に取得し、その後の不変を確認。
全handleは終端。例の2候補もmetadataだけで生成/再生し、新FEM0。
新しい外部資料・依存・legacy参照は追加していない。元D01/D02の境界法則、
公開Maxwell尺度則と既存独立polygon式を再利用した。
