# 複数設計変数による曲線寸法のRF探索 — D03版3

2026-09-14。元の曲線形状を単位付き変数の多変数多項式で変更し、
実FEMの周波数/RF/ピーク比を用いて制約付き座標探索を行う。
探索順序・予算・制約違反量の比較・最終別3水準の判定は[既存の探索](RF_OPTIMIZATION.md)を使う。
元Project・固定履歴の扱いは[要求版2](RF_OPTIMIZATION_HISTORY.md)を継承する。

受入条件は、独立な幾何積分と単位/物理相似、複数変数と交差項、
実際に両変数を動かす候補評価、3水準と最終別3水準、実試行の比較写像と個別ID、
失敗に有利な目的関数値を与えないこと、全native保存からの再生・改変拒否、CLI/worker/GUIでの利用である。
一般的な連続最適性や物理誤差上界を保証せず、D03親課題全体・全計画は継続する。

## 入力

`schema_version: 3`を使う。criteria/constraint_scales/objective_improvement/max_trials/initial_ids/mode_idは従来と同じ。
版1/2のフィールド、正の2倍率、保存文書・判断の意味は維持する。

| 項目 | 契約 |
|---|---|
| project | direct、非組立・非鏡映、軸接続の真空閉PEC/axis TM、native曲線P2。markedは全固定で明示元メッシュが必要 |
| variables | 1個以上の変数の配列。配列順に正方向・負方向を探索する |
| 変数のname / unit | 一意で空でない名前。unitは`m`または`1` |
| lower / upper / initial | 有限な昇順範囲と範囲内の初期値。版3は0や負の値も許す |
| step / tolerance | 正の有限値でtolerance<=step。各変数の単位で指定 |
| geometry_terms | 既存の曲線数値項目pathから単項式配列への辞書 |
| minimum_corner_angle_deg | 有限で0より大きく60未満。変形後の二次写像の頂点接線角の下限 |
| rf_coordinates | `fixed`または`axis_fraction`を明示 |
| controls | `piecewise_remesh`と既存の追跡条件。比較メッシュは入力せず、実試行から導出する |

pathは[曲線形状Study](CURVED_HARMONIC_STUDY.md)と同じ既存numeric leafに限定する。
start/end/centerの座標、半軸、角度、始終パラメーターを連動できる。
曲線の種類・数・順序・双曲線の枝、境界タグ、弦分割・材料・ソルバー設定を変更できない。
既存の軸区間[0,L]を保つ。軸の始点ごと平行移動する形状はこのnative契約に含まれない。

各pathの値は次の和である。

`sum(coefficient * product(x[i] ** powers[i]))`

各項は`coefficient`と`powers`だけを持つ。係数は有限数、powersはvariablesと同じ長さの非負整数配列。
同じpath内で指数配列を重複させず、各変数を少なくとも一つの非零非定数項で使用する。
Boolean、NaN/Inf、未知path・未知フィールド、指数の負数/非整数、有限範囲を超える項・和は拒否する。
和は`math.fsum`で評価する。項の途中で非有限になった場合も、相殺による救済をしない。

係数の単位は「対象項目の単位 / 各変数の単位のべき積」。例えば変数が`[radius(m),bias(1)]`なら、
次は`radius*(1+0.1*bias²)`を半径[m]に割り当てる。

```json
{"/curves/1/semiaxes_m/1": [
  {"coefficient": 1, "powers": [1, 0]},
  {"coefficient": 0.1, "powers": [1, 2]}
]}
```

全法則を元Projectへ同時に適用し、調和変位で内部節点を移動する。
各候補で正のJacobian・境界・品質/予算・固定分割を再検査する。
初期値の法則構造を要求解析時に検査し、実候補の形状/写像検査に失敗すれば失敗文書と先行保存を保持する。
範囲の全隅や内部の全形状を事前に有効と認定する仕組みではない。

## 比較と細分

形状の異なる試行では、各実試行の元弦メッシュに元Projectの固定履歴を適用して比較メッシュを作る。
これは[非アフィンtune](CURVED_HARMONIC_TUNING.md)と同じ二次写像による対応である。
試行の最初の水準が最終確認で1段細かくても、比較用履歴は元のものを使い、
両native場をそれぞれの実FEM空間から評価する。

各試行内の3水準は同じ二次領域で、`curved_same_domain`の個別追跡と既存RF設計評価を使う。
元履歴の後へ、探索では0/1/2回、最終確認では1/2/3回の全域細分を追加する。
履歴なしでは元の一様細分段数から同じ差の3水準を作る。
全周波数順位の個別対応を要求し、未確認・未収束候補を有利な評価へ変更しない。
最終確認を含む最大FEM呼出し数は従来どおり`3*max_trials`。

外側のcheckpointは版1のまま。版3要求、全試行値と親、比較メッシュ、固定履歴、
各水準のnative解とRF評価、予算・採用判断を完全再生する。
版3だけscope文字列を多変数表記にし、版1/2の文書再生を保持する。

## 利用

合成の半楕円対を用いた[入力例](../examples/optimization/curved_geometry_rf.json)では、
半径[m]と左右の非対称度[1]を変える。実測空洞ではない。
GUIで「複数変数から曲線寸法を変更（調和変位）」を選び、変数と項のJSONを編集できる。
定数項のひな形は現在の曲線から作る。各変数を非定数項へ結び付けてから開始する。
入力準備中に形状や設定を変更した場合は古い応答を反映しない。
変数・項を元JSON文字列でサーバーへ渡し、重複キーを黙って上書きしない。
保存読込では全変数の名前/単位/順序/範囲、項、RF方針、角度を復元し、結果の列にも各単位を表示する。

```sh
OPENBLAS_NUM_THREADS=1 .venv/bin/python -m superfish_ng optimize-rf examples/optimization/curved_geometry_rf.json --out out/geometry-rf-first --max-new-trials 1
OPENBLAS_NUM_THREADS=1 .venv/bin/python -m superfish_ng resume-rf-optimization out/geometry-rf-first/checkpoint-001.json --out out/geometry-rf-rest
OPENBLAS_NUM_THREADS=1 .venv/bin/python -m superfish_ng replay-rf-optimization out/geometry-rf-rest/checkpoint-004.json
```

必ず新しい出力先を指定する。実workerの中止・保存地点選択・再開・各試行/水準の場表示は従来の操作を使う。

## 検証と来歴

新独立2件は変更前に版3/法則不在で失敗し、実装後4.139秒で合格した。
Green境界積分による面積/回転体積、非アフィン変形と固定履歴、混合項と単位換算を確認した。
追加の3変数試験は、半径・非対称度・軸長の混合項で軸方向座標とGreen積分/RF座標が独立な倍率則に従うことを0.818秒で確認した。
初回の平行移動試験は既存の軸区間[0,L]に違反し、正しく拒否された。製品の原点条件は緩和せず、試験を許可された軸長変化へ修正した。

最初の専用系列は12FEMを完了したが、初期・探索候補はNOT_CONVERGED、最終の追加細分だけCRITERIA_METだった。
粗細の周波数差8.590e-5は許容1e-4内でも、R/Q差2.618%は0.5%を超え、Bpk/Eacc差1.629%は1%を超えた。
探索器は候補のeligible_valueをNoneとして採用せず、元の座標を保持した。検証器の「初期値が採用可能」という仮定がTypeErrorで失敗した。
これを改善成功と解釈しない。independent/base.jsonと全12FEM・失敗を保持する。
受入用の入力例は既存marked→uniform→markedの固定履歴を使用し、同じ変数範囲・形状法則・許容差で初期精度を増した。
最初の各候補の3水準と最後のさらに細かい3水準は、いずれも新しいFEMを実行する。
選択unitは29件937.813秒、28合格と上記の軸原点に違反する試験1件のERRORだった。
その1件を修正した0.818秒の合格と合わせ、最終29件は分割した検証根拠とする。
実6FEMの中断/再開/最終比較と改変拒否、無効候補のFEM前失敗、版1/2、GUI/JobManager、
保存のprefix再利用・開始競合、共有curve leafのStudy/tuneを含む。単一の全件PASS実行とはしない。
Chrome新版24項目・旧版13項目がPASS。実workerの中止/所有保存からの再開、保存改変拒否、
別3水準、表面評価の固定履歴再生、元場の読込/描画、変数別単位と列を確認した。
新版は精度を増す前の固定1段の入力をbrowser-new/request.jsonに保存し、初期UNVERIFIEDと最終CRITERIA_METを区別した。
現在の固定3段の入力例と同一の試行を回したという主張ではない。両完了系列は各6FEM、中止別分岐の部分計算は別である。
追加browser-inputの11項目で3変数/混合項の完全往復、normalize/prepareの待機中の編集による古い応答拒否、
ひな形の保持、版3から版2への切替とRF座標方針を確認した。追加FEM/workerは0。
全3browserで外部HTTP0、324製品SHA一致/実行中不変。新旧の入力/結果画像を目視した。
GUI全8jobのcomplete/cancelledを確認し、専用PID1665974の完全argvを照合してSIGINT、handle49593は終了0。
粗いCLI初期/最終と新版GUI初期/最終の既保存6水準は、各10native配列と全RF mode数値が完全一致した。
各Case hashはそれぞれの原JSONを正準符号化して個別検査した。cli-gui-numeric-parity.jsonに保存し、新FEMは0。
専用 `validate_rf_optimization_geometry.py` は6206.019秒、36新FEMでPASS（handle68843、終了0）。
基準・半径の無次元化・全寸法2倍の3系列で、それぞれ両変数を動かし、全4試行がCRITERIA_MET。
基準の値は `[.08,.01] → [.0808,.01] → [.0808,.02] → [.0808,.02]`。
目的値の上側包絡は1614723199.2864945 Hzから、最終1599730640.1691456 Hzへ下がった。
予算停止TRIAL_LIMITと最終制約充足を区別する。大域最適解の主張ではない。
探索各3水準は146/584/2336要素、最終別3水準は584/2336/9344要素。
各系列で元履歴の保持、Green面積/体積、全native再生、改変比較履歴の拒否を確認した。
単位/Maxwell尺度則の最大相対差はRF五量と評価区間1.530e-13、各要素2点のHφ/Er/Ezは1.132e-13。
幾何相似の面積/体積の比は記録された数値で一致し、検査閾値2e-12内だった。
数値は[保存benchmark](../benchmarks/optimization/curved-geometry-20260914.json)、
全終端・分割unit・ブラウザー・出力hashの索引は同out内`acceptance.json`。
専用実行中の1059ソース系ファイルは不変。終了後の差は、別途合格した試験データ1件と
rf_optimization.pyのmodule docstringだけで、それ以外のAST一致を確認した。
全suite/seed/Hosted CI/新Wine比較は今回実行していない。
証拠の親ディレクトリは`out/rf-optimization-geometry-20260914/`。

既存の幾何leaf検査を共通化し、調和変位・固定二次制限・座標探索・RF評価を再利用した。
新しい外部数学資料・依存・旧資産の参照はない。
任意関数/式評価器、境界分割変更、他物理・半領域の探索、連続最適性/一般性能の受入は含めない。

## 元計画との照合と次の判定

[元のD03行](COMPATIBILITY_PLAN.md)は、複数制約/目的関数/実行上限/未収束時の判定、
RQとピーク比を含む実探索と全試行記録、初期/最終の独立細分比較・制約充足・失敗解の不採用を要求する。
版3は、既存のこれらの経路へ単位付きの一般曲線寸法を接続したもの。
任意の非多項式関数、他物理、一般性能保証、大域最適性は、元D03行の明示受入項目ではない。
BACKLOGの追加拡張候補を無条件に親D03の完了条件へ増やさず、元要件と分けて判断する。

| 元要件 | 今回と既存の根拠 | 次の判断 |
|---|---|---|
| .S 複数制約・目的・予算・未収束 | RF_DESIGN_CRITERIA/RF_OPTIMIZATION、版3の厳密入力と既存判定の再使用 | 既存の規約/実行上限を維持 |
| .I RQ/ピーク比・全試行 | 旧版の実探索、今回の非アフィン両変数、全native/個別ID/比較写像/保存再開 | 例題名による製品分岐なし |
| .V 初期/最終の独立細分・制約・失敗 | 旧球形解析/単位不変、今回の各独立3水準、無効形状のFEM前拒否と粗い候補の不採用 | 専用36FEMと単位/相似・全native再生がPASS。依存の受入を別途確認 |
| 依存D02/N03/R01 | R01受入済み。D02とN03は限定実装/検証があり親受入は未完 | 両親を原要件へ照合してからD03親の受入を判断 |

この変更単独で親依存の未受入を完了へ置き換えない。次工程では追加機能を増やす前に、
D01/D02とN03の元.S/.I/.Vと保存済み証拠を照合し、具体的な欠落だけを実装課題にする。
