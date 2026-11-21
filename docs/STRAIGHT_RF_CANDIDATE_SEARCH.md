# D06：元直線TM候補の座標探索・実FEM・保存再開

2026-10-07、D06の原実装条件を受入した。元123カードと互換32要件を維持する。
先行[多変数候補台帳](STRAIGHT_RF_CANDIDATES.md)に、実nativeの候補探索・
三水準個別ID・所有checkpointを接続した。既存曲線版1〜3は元保存成果物から完全再生した。

**RF採用評価はD07で継続する。** D06は候補生成/追跡のカードであり、
RF制約収束・目的改善や親D03/全goalの完了を意味しない。
未実装の評価を受け付けない[D05能力規約](RF_OPTIMIZATION_SCOPE.md)を保持する。

## 入口と規約

例は `examples/optimization/straight_native_candidates.json`。
`rf_optimization_geometry` のAPIから実行・再開・完全再生できる。
出力には必ず未使用のパスを指定する。

```python
import json
from pathlib import Path
from superfish_ng.rf_optimization_geometry import (
    execute_straight_rf_candidate_search,
    replay_straight_rf_candidate_search,
)

request = json.loads(Path('examples/optimization/straight_native_candidates.json').read_text())
first = execute_straight_rf_candidate_search(request, 'out/candidates-first-new', max_new_trials=2)
final = execute_straight_rf_candidate_search(request, 'out/candidates-resumed-new', checkpoint=first)
assert replay_straight_rf_candidate_search(final) == final
```

| 要求項目 | 規約 |
|---|---|
| schema_version / document_type | 整数1 / `straight_rf_candidate_search_request`。既存optimization要求とは別の明示型 |
| candidate_request | 先行候補要求版1の完全な元Project・全境界owner・名前付きSI式・比較領域・controls・候補上限 |
| poll_variables | 元変数と同じ宣言順、name/initial/step/tolerance。初期値はbounds内、有限正step/tolerance、tolerance <= step |
| max_trials | 整数2以上、元max_candidates以下。初期・最終・失敗候補を含む試行予算 |
| initial_ids | 元周波数順位ごとの一意な非空ID。後続は実場の対応によって継承する |
| refinement_scale | 整数2以上。searchは元mesh尺度1/s/s²、finalはs/s²/s³で三水準を独立に求解する |

既存の有界多変数座標pollを呼び、元Projectから毎回実形状を再構築する。
全座標は名前付き式でまとめて更新する。初期接続/固定履歴付き曲線経路は変更しない。
直線候補間・同形状三水準間の比較は、元全境界から導出した二つの比較meshを使う。
比較前に実Projectが元法則と宣言した細分のいずれかへ完全一致することを要求する。
Case/RF規格化・軸・全境界タグを部分比較へ置き換えない。

この段階の全 `assessment` はnull、`rf_assessments=0`。criteriaや目的量は要求に存在せず、
追加するとFEM前のstrict解析で拒否される。偽の非null assessmentをpollへ渡すことも拒否する。
採用可能なRF評価がないため初期centerは移動しない。全poll終了は **FINAL_UNVERIFIED**。
IDENTITY_VERIFIEDは三水準の標本個別対応だけで、RF/peak精度や連続枝を保証しない。
将来のD07評価器が同じ元候補を使い、適格評価が成立してから採用を判定する。

## 保存と停止

各水準は既存native Job/元FEMで求解し、保存場・元Project・全manifestを検証する。
候補間または細分間で個別IDが未確認なら **UNVERIFIED** として即時停止し、
次の細分/候補を求解しない。周波数順位の入替えは実場によって追跡する。

各完了候補と未確認停止には排他的checkpointを保存する。
PAUSEDだけを別の新規出力へ再開できる。再開/公開replayは全元要求・全native・
各三水準・対応・決定・SHAを再構築し、元checkpoint/祖先を変更しない。
独立スペクトル・元H/E/RFと二つのR/Qの定義を保持する。

無効候補とsolver失敗は終端failureに元attempt・候補試行数・FEM呼出し数・上限・理由・
null assessmentを保存する。幾何拒否でFEMが0回でも候補試行として数える。
途中native・未完了三水準を正常checkpointとして出版しない。
解決済みprefixを改変したり、symlinkを入力に含めたり、途中で実装源が変わると拒否する。
以前の正常checkpointからのforkは、別出力の別実行として再検証する。

## 原条件の対応と検証

raw: `out/d06-straight-native-search-20261007/acceptance.json`。
先行33＋新8の **41個別unit** を元log・源の実メソッド・源hashへ結合した分割受入。
新full/seed/legacy実行0。FEM/規格化/六量/RF・peak許容差の核は変更していない。

| D06原条件 | 現存する証拠 |
|---|---|
| 確認済み直線/曲線法則を多変数候補へ接続 | 3直線形状で両変数の6実poll・各18 FEM。曲線版1/2/3の元法則/固定履歴/完全保存再生 |
| 元Project/固定履歴、変数/順序/再開によらない実形状 | 先行の全境界・独立面積/体積・変数/owner/binding/候補順の完全一致。新3形状の分割再開・全Case/RF照合 |
| 無効形状・未確認IDに有利な目的値を与えない | 無効中間候補の追加FEM0、実2モード曖昧対応で2 FEM後停止、criteria/偽assessment拒否、全assessment null |
| 失敗候補と予算を記録 | 元失敗の試行数・FEM試行数、三水準/最終の予算、元checkpoint/祖先のbyte保持 |
| 既存曲線版1〜3再生 | 2＋4＋4の10元試行/30 native水準を完全一致で再生、追加FEM0、実終了0 |

新nativeでは独立円筒Besselのf/Hφ/Ez/全PEC壁loss/両R/Qを別検査し、
元f 1e-4、H .001、E .01、loss/RQ .005を保持した。三水準の誤差減少も成立。
Erの解析ゼロ対照は、源が一致する先行単変数の独立Bessel検査で受入している。
別の実円筒順位交換ではIDが `[mode-1, mode-3, mode-2]` となり、
最終の元形状へ戻ると元ID順を保持した。解析は検査だけに用いた。

初回 `native-tests.log` は6検査58.556秒、4検査合格・2検査ERROR（3形状subcaseを含む4 ERROR）。
検査側の保存mass再構築不足とcontour controls不足を保全して修正し、成功済み4検査は再実行しない。
`repaired-and-crossing.log` は修正2検査合格、新順位交換検査の端点1 ulp不一致で終了1（3件60.690秒）。
厳密境界検査は維持し、両元端点を同じ表現座標から構成した
`crossing-coordinate-repaired.log` の1件35.470秒で不足分を受入した。
独立面積/体積の先行invariantは新API不在を先に再現後、1件0.043秒PASS。

代表保存成果物は `api-resumed/checkpoint-006.json`。
例要求を実APIで2候補から再開し、両変数の6候補/18 FEM、完全要求・native再生・
祖先byte一致を確認した。最終FINAL_UNVERIFIEDとRF評価0を保持している。
新CLI/GUIのRF採用運用はこの成果物で完了扱いせず、後続カードへ分ける。

1190 Python源の数値開始snapshotから変わったのは検査1ファイルだけ。
修正前源を別保存し、成功済み検査ASTの不変を確認した。
全製品源は数値/旧曲線replay中を通じて固定、修正後snapshot以降は全源不変。
旧7モジュールの全関数AST不変、旧探索/評価/checkpointの源byte不変。
全実行handleは終端。新依存・外部資料・legacy参照は追加していない。

次はN01/N02/N03の精度条件と独立比較を進め、依存が成立してからD07の
RF収束/制約区間/独立最終採用を接続する。D06 DONEは全開発計画の完了ではない。
