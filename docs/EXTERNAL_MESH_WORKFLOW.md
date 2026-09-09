# 外部メッシュ単体のGUI読込と固定形状Study

2026-09-09、O02-meshの既存Project第2版を操作へ接続。限定受入。
元の[Projectメッシュ契約](PROJECT_MESH.md)を維持し、別ソルバーは作らない。

## 読込と解除

GUIの「元メッシュJSONを読み込む」は、現在のCaseに対応するSI・rz・0始まりの
タグ付き三角形JSONを読む。サーバーでduplicate keyを含むJSON文法、Case/Projectと
mesh_from_dictの幾何・番号・接続・タグを検証してから、フォームを更新する。
失敗時は入力と元メッシュを保持する。メッシュだけでは形状/物理モデルを推定しない。
成功後はProject第2版として保存・計算し、メッシュ生成設定で置き換えない。
GUIの既存要求上限4 MiBは維持し、現在のProjectとメッシュを含む要求全体に適用する。
Pythonは `project_mesh_operations.replace_project_mesh(document, mesh_document)`、
HTTPはreplace-mesh操作を使う。mesh_documentがnullの操作だけを解除とする。

「明示メッシュを外して自動生成へ戻す」はProject第1版へ戻す。
形状編集で以前のメッシュが合わなくなった場合にも、新しいメッシュへの置換/解除はできる。
置換対象の古いメッシュを新しい入力として再利用しないためであり、その他のCase/Project
項目や新メッシュのstrict検査は維持する。JSONファイル内のnullは解除操作と解釈せず拒否する。

局所marked履歴がある場合は、元メッシュの番号を含む完全一致を要求する。
生成メッシュへ戻す場合も比較する。異なる場合は履歴の明示解除を要求し、以前のセル番号を
別のセルへ黙って適用しない。一様履歴だけの場合はセル指定の再解釈はない。
曲線二次写像の可逆性などの実行時検査は従来のsolveで実施する。

## 直線外部メッシュのStudy

`fixed_geometry_convergence` をgeometry_order=1の明示メッシュにも拡張する。
parameterは `additional_uniform_refinements`、valuesは増加する非負整数。
0は入力そのもの、1は全三角形を4分割、2は16分割する。P1/P2場に対応。
既存の共有辺分割器を全辺へ適用し、元頂点の番号/座標、境界タグと多角形を保持する。
元Caseの生成器から新しいメッシュを作らず、要求した最大段数まで逐次分割する。

三角形上限はcontour_mesh.max_triangles、未指定なら250000。
入力三角形数×4^段数が上限を超える場合は、巨大な配列を作る前に拒否する。
近傍の丸めや退化で有効な分割を構成できなければ、従来のmesh_from_dictが拒否する。
新たな角度閾値を暗黙に課すものではなく、元の直線領域の一様分割である。

通常のStudy保存/CLI/GUI・場比較・RF比較を使う。報告は固定多角形と記録し、
曲線二次形状の固定とは区別する。geometry_order=2の従来の固定Studyは経路/文書を維持する。
この操作を一般の物理誤差上界、RF収束保証、別形状間の追跡と呼ばない。

## 受入証拠

直前22d51afの標準720件を確認。開始時にStudy/Project関連11件が5.213秒で合格。
旧Studyモジュールへ新しいP1/P2不変量試験を適用すると、直線固定Study未対応で拒否された。
追加4検査は最初にelement_geometryの戻り値を取り違え1ERROR、次に点配列を面積として扱い
失敗。det/2へ修正し、4件0.376秒PASS。製品の幾何や許容差を変えて隠したものではない。

独立 `out/external-mesh-study-independent-accepted-20260909` は終了0。
P1/P2×尺度1/2の各0→1→2段（24→96→384要素）を実Studyで計算、Ritz低下を確認。
最終円筒解析f差はP1最大2.963e-5、P2最大6.788e-8、f/両RQ/G相似差最大3.709e-14。
CLIとPython Studyの全3段のmode結果辞書が完全一致し、管理器再起動後の検証もPASS。
初回独立は保存P1解に質量行列がないのにquantitiesを再実行して失敗した。
実FEMが書いたRF結果を読む検証器へ修正し、初回出力も保持した。

実Chrome68081は `out/browser-external-mesh-20260909` の26項目PASS、外部要求0、終了0。
読込/解除・duplicate key拒否時の保持、明示メッシュ保存/実FEM、適応への引継ぎ、
直線固定Study入力/実計算/表示と従来の調整操作を確認。新規画像の目視検査なし。
GUI54203/PID448617はSIGINT停止、終了0。
同じGUI入力のCLI/Python計算とmode結果・元meshの完全一致、GUI/Python Studyの2段の
完全一致と管理器再起動は `out/external-mesh-interface-20260909` でPASS、終了0。

標準 `out/validation-external-mesh-20260909` は終了0、724件中722合格・2skip、579.489秒。seed9モード19量のf差0/RF最大8.882e-16。標準/独立/経路比較/終了後414対象hashとChrome対象hashが一致した。全検証終了・ソース固定解除。O02の高次/追加物理の全統合や全体計画は未完了。
新規外部資料・依存・legacy参照はない。
