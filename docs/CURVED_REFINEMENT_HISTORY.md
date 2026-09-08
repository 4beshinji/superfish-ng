# N04 曲線局所細分のCase履歴とnative再構築

2026-09-09追記: [適応計算版4](CURVED_ADAPTIVE_REFINEMENT.md)で滑らかな閉PEC曲線の五量停止・高次積分比較・保存再開をAPI/CLI/JobManagerへ接続した。以下の未接続記述は当時の履歴。GUI・一般精度/効率は残る。

2026-09-08、直前基準84a49e4。
[局所適合細分API](CURVED_MARKED_REFINEMENT.md)を通常のCase/FEM計算・native保存/再読込へ接続した。
親の二次幾何を順番に制限する。解析曲線への再投影、解析解による固有値の置換は行わない。

## 入力と順序

schema_version=3、mesh.geometry_order=2、solver.element_order=2のCaseで、meshへ次の履歴を指定する。

```json
"curved_refinement_steps": [
  {"kind": "marked", "marked_cells": [0], "minimum_corner_angle_deg": 5.0},
  {"kind": "uniform"},
  {"kind": "marked", "marked_cells": [1], "minimum_corner_angle_deg": 5.0}
]
```

marked_cellsは、その操作の直前のメッシュの0始まり要素番号。最初は保存する元弦メッシュから
構成した二次要素を指す。重複・負数・bool・空配列・範囲外を拒否する。
必要な隣接要素も適合性を保つため細分する。各marked操作に有限の0度超60度未満の
minimum_corner_angle_degを必須指定する。uniform操作はkind以外を受け付けない。
各段階でCaseのcontour_mesh.max_triangles（未指定時250000）を適用し、失敗時は操作番号を返す。
頂点接線角の制限は要素内全域の条件数や物理誤差の保証ではない。

履歴は非空配列。細分しない場合はキーを省略する。従来のcurved_refinement_levelsは維持し、
正のlevelsと新履歴の併用は拒否する。混在する細分は履歴内のuniformで順序を明示する。
Python APIではcurved_refinement_stepsにCurvedRefinementStepのtupleを渡す。
元メッシュや幾何を変更すると番号の意味も変わるため、履歴をそのまま別メッシュへ流用しない。
Studyは履歴付きCaseを明示的に拒否する。履歴対応の収束Studyは今後の課題。

通常CLIでCaseを解く。

```sh
OPENBLAS_NUM_THREADS=1 .venv/bin/python -m superfish_ng solve case.json --out out/new-curved-run
```

## 保存・検証・鏡映

Case、元弦メッシュ、履歴、計算後の二次幾何配列と固有ベクトルをnative形式で保存する。
field_spaceとgeometry_approximationにも履歴を記録する。read_solutionは履歴を順に適用し、
幾何配列の完全一致、拘束、K/Mによる固有対残差・規格化・直交性、RF量を再検証する。
固有値を解き直さない。完了manifestを更新しても不整合な履歴は通らない。
従来の履歴なし/全域levels保存の読み方は変えない。

鏡映は局所細分後の半領域を反映する。半領域の履歴はreflection.source_caseに保存する。
全領域Caseではこの履歴を空にし、半領域の要素番号を全領域へ適用しない。
再読込は明示した半領域Case・元メッシュを再構築してから鏡映する。
全領域Caseだけから同じ離散場を再現できるという意味ではない。

## 受入検証と限界

着手前628件中626合格・2 skip（382.837秒）。追加4検査PASS（6.296秒）。
混在履歴の手動操作との幾何完全一致、旧全域細分との一致、strict入力・予算拒否、
native再読込とmanifest更新後の履歴改変拒否、磁気対称半領域の鏡映保存を検証した。

scripts/validate_curved_refinement_steps.pyを実行し、初回
out/curved-native-initial-20260908はPASS。円筒/楕円/双曲線×尺度1/2で、
72/369/224要素のnative局所細分を実際に計算・保存・再検証した。円筒尺度1はCLI経由。
別の密行列FEM解法との差は先頭2周波数で最大3.162e-13、基本モードの五量で最大2.387e-12。
元APIで手動構成した幾何配列と全件完全一致。再検証は固有値ソルバー呼出しを禁止して実行。
円筒解析差はf=8.658e-7、RQ=2.150e-4、G=7.497e-7、Epk/Eacc=2.953e-4、Bpk/Eacc=2.261e-4。
Maxwell相似則の最大相対差5.685e-14、自由DOF固有対残差は最大2.846e-14。
残差を離散化誤差の上界とは扱わない。合成例であり実測空洞ではない。

最終標準検証 out/validation-curved-native-20260908 は632件中630合格・2 skip（394.048秒）、PASS。
benchmarks/validationの全9モード・19量で周波数差ゼロ、RF/エネルギー差最大8.882e-16。
標準・独立検証の記録hashは最終ソースに一致し、独立検証中のソース変更なし。

後続で[曲線残差指標](CURVED_RESIDUAL_INDICATOR.md)を追加した。
GUIでの要素選択・履歴編集、履歴対応Study、曲線の追跡付き適応停止、
一般形状の精度/効率・幾何近似誤差・物理誤差上界は残る。新規依存・外部資料の再使用なし。
