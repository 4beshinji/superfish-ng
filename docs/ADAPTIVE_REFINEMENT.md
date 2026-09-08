# N04 追跡付き直線要素の適応細分

2026-09-08。`adaptive_refinement.py` は、残差指標→対象選択→適合細分→実FEM再計算を
繰り返す。対象は既存の真空・軸接続m=0 TM、直線P1/P2。固定した同一多角形領域を使い、
各水準で全個別モードIDを追跡する。二次曲線幾何の局所細分は未対応として拒否する。

## 入力と実行

`examples/adaptive_refinement/pillbox.json` は小規模P2円筒の動作例。
例の相対基準は周波数0.01、R/QとGは各0.1で、物理精度の標準値ではない。
独立検証では別途周波数1e-4、R/QとG各0.005を指定する。

```bash
python -m superfish_ng adaptive-refine examples/adaptive_refinement/pillbox.json --out out/adaptive-new --max-new-levels 1
python -m superfish_ng resume-adaptive-refinement out/adaptive-new/checkpoint-001.json --out out/adaptive-resume
python -m superfish_ng replay-adaptive-refinement out/adaptive-resume/checkpoint-003.json
```

全水準を連続実行する場合は`--max-new-levels`を省略する。各出力先は新規ディレクトリを使う。
上のファイル名は例の3水準停止に対応し、他の要求では実際に保存された最終チェックポイントを指定する。
Python入口は `execute_adaptive_refinement(request, directory, max_new_levels=None, checkpoint=None)`、
`read_adaptive_refinement(path)`、`replay_adaptive_refinement(document)`。

要求はschema_version=1で、以下の全フィールドを明示する。未知フィールドは拒否する。

| フィールド | 契約 |
|---|---|
| case | 既存Caseの全入力。反復中は物理・幾何・正規化・モード数を固定 |
| initial_mesh | nullならCaseから生成。指定する場合は既存タグ付きメッシュJSON |
| initial_ids / mode_id | 初回周波数順位ごとの重複しないID一覧と対象ID |
| controls | 既存追跡controls。mappingはsame_domain。他の写像を暗黙に選ばない |
| bulk_fraction | 二乗残差指標の選択割合 `(0,1]` |
| max_levels | 初回を含む水準上限。整数3以上 |
| max_triangles / minimum_angle_deg | 要素上限と最小角。Case側の制約が厳しければそちらを使う |
| relative_tolerances | frequency_hz、r_over_q_accelerator_ohm、geometry_factor_ohmの正の相対基準 |

選択と細分は[残差指標](RESIDUAL_INDICATOR.md)・[適合細分](MARKED_REFINEMENT.md)を再利用する。
各水準のメッシュは元の初期メッシュと直前の対象モードの残差から決まる。
同一領域追跡では境界全体の位置・被覆・タグを両方向に照合し、共有節点番号には依存しない。
今回、同じ電気/磁気対称面タグを保持した比較にも対応した。異なるタグの比較は引き続き拒否する。
全個別IDが解決できない場合は対象の量を判定へ使わず停止する。順位をIDと取り違えない。

## 停止と判定

最低3水準の直近2区間で、各量の `abs(current/previous - 1)` を個別に計算する。
二つの区間の三つの量がすべて指定基準以下の場合のみTARGETS_MET。
同じ末尾の値だけで前の区間の未達を消さない。正でない値・非有限比は未確認とする。
指標が小さいこと自体を合格条件にはしない。

| 状態 | 意味 |
|---|---|
| PAUSED | 追加水準を実行できる。新しい出力先へ再開可能 |
| TARGETS_MET | 指定したf/RQ/Gの直近2区間の細分差を達成 |
| UNVERIFIED | 全個別モードIDを解決できなかった |
| QUANTITY_UNVERIFIED | 判定に必要な正の有限量/比を確認できなかった |
| LEVEL_LIMIT | 水準上限までに達成しなかった |
| REFINEMENT_LIMIT | 次の細分が要素上限または最小角を満たさない |
| TRACKING_BUDGET | 次の比較が既存の262144標本上限を超える |
| ZERO_INDICATOR | 選択可能な正の指標がない。これだけで達成とはしない |

PAUSEDとTARGETS_METはCLI終了値0、その他の判定は1。PAUSEDは完了ではない。
失敗したsolve/保存/検証は例外とfailure-NNN.jsonを残し、その水準を採用しない。
前のチェックポイントを使って新しい出力先へ再開できる。終端判定からの再開は拒否する。

TARGETS_METは指定した離散結果の変化量の判定であり、真の固有値/RF誤差上界ではない。
`physical_error_bound=null`、`surface_status=UNASSESSED`を常に保存する。
表面ピーク・幾何近似・全モード探索・連続的なモード枝の保証はこの判定に含まない。
ユーザー指定の大きい許容値でも、その範囲以上の精度認定にはしない。

## 保存と再検証

各水準をnativeのlevel-NNN/へ保存し、直後にcheckpoint-NNN.jsonを新規作成する。
チェックポイントは要求、保存先、原ファイルhash、選択要素、品質/DOF、追跡対応、
残差指標、対象の全RF量、各細分差と停止状態を持つ。
再検証では初期メッシュから選択・全細分・全追跡・停止条件を再構築し、文書全体を照合する。
再開時も既存水準を再検証するが、固有値のsolveを再実行するのは新しい水準だけ。
途中での元結果/実装変更を検知した場合は新しいチェックポイントを採用しない。

`affine_saved.read_verified_affine_solution(directory)` は既存読込の構造/hash検査に加え、
K/Mを再組立てし、磁気対称面拘束・正規化/直交性・全固有対残差・全RF量を検査する。
行列再組立ては固有値solveではない。固有対/正規化の検査閾値1e-7、RF再構築の
rtol=1e-10/atol=1e-12は既存曲線保存検査と同じ。離散化誤差の許容値とは別に扱う。
通常の`read_solution`の返却型や旧保存契約は変更していない。

## 検証と残件

7検査でP1/P2円筒の解析周波数に対する変分上界と細分改善、全個別ID、二つの区間の
RF個別判定、保存後の場/固有値/RF改変拒否、再開時の新しいsolve数、失敗記録、
要素/標本予算・追跡未確認、対称面、厳密入力、CLI作成/再開/再検証/非合格終了を確認する。

`python scripts/validate_adaptive_refinement.py --out out/adaptive-validation-new` は
円筒/合成折返し輪郭×P1/P2×尺度1/2で、適応（円筒P1は最大7水準、他は3水準）と一様3水準を独立に計算する。
解析円筒周波数、Ritz単調性、f/RQ/G相似、同じ尺度間選択、保存後完全再構築を検査する。
追跡は追加の積分次数4でも同じ個別IDになることを確認。全RF・DOFと時間を保存する。
適応の時間は保存/再検証を含む全workflow、一様の時間は細分/solve部分であり直接の速度比にしない。

GUI/JobManagerの操作・停止再開、曲線局所細分、表面量に対する停止と物理精度評価、
一般形状での誤差対DOF/時間の効率受入は残る。N04全体の完了ではない。

初回の独立円筒P1は3水準でR/Qが基準未達だったため、基準は変えず水準予算を7へ増やした。
5水準で細分差を達成したが、解析R/Qとの差は約1.96%残る。0.5%の細分差基準を
真のRF誤差0.5%以内と読み替えることはできない。Gの解析誤差にも単調減少の原理はなく、
初期約1.043e-5に対し5水準目約1.058e-5となった。独立比較はこれらも保持する。

独立検証`out/n04-adaptive-refinement-final-20260908`は円筒P1のRF改善条件がFAIL。
API/CLIの7検査合格や円筒P2の達成を、P1の物理RF受入へ代用しない。
許容差もRF改善条件も緩和せず、この出力を次のRFに対応する選択/独立確認の改善基準に残す。
