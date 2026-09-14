# TE鏡映場の非アフィン曲線比較

2026-09-15 JST、開始HEAD `d262572`。D02の鏡映場比較をpiecewise_remesh版2/3/4/5へ接続する。
受入条件は元半領域の宣言からの全領域写像、正の体積測度、実際の両側Eφの評価、
対称セクター内の順位保持、独立した鏡映不変量、保存再生・改変拒否である。

## 写像の契約

鏡映済みTE場のcomparison_meshesは、元半領域の弦メッシュと履歴・参照座標を宣言する。
その参照三角形上の写像を元側と鏡映側へ延長し、保存された全領域の実場を両側でサンプリングする。
z_min対称では元側を半領域長だけ移動し、z_max対称では元側の位置を保つ。
鏡映のJacobianは絶対値を体積積分に用い、負の重みは導入しない。
半領域の係数から比較値を代用せず、固有値や周波数で場を選び直さない。

全二次境界は、比較空間を既存の幾何鏡映で全領域へ延長した後、native全領域境界と照合する。
全域のedge検査、体積、比較要素数、サンプル数を記録する。
`reflection_mapping`は宣言領域と評価領域の違いを明示し、版3の番号対応は
`source_numbering_correspondence`、版4/5の参照分割は`source_common_reference_partition`に記録する。
これらのsourceメタデータを全領域の要素数と混同しない。

全域のサンプル予算を先に2等分し、鏡映分も含めて262144点以内を要求する。
同じ対称セクター・同じ直接/鏡映区分だけを比較し、混在とTM鏡映は引き続き拒否する。
直接半領域と既存閉PECの出力形式は保持する。
非アフィンProject変形、tune/Studyの対称経路、専用GUI受入は本工程に含めず残件とする。

## 検証

生記録は`out/te-reflected-piecewise-20260915/`。
新3テストは旧一律拒否で18 errors、3.893秒となることを再現した。
最初の実装後3件28.259秒PASS。参照メタデータのsource区分と予算検査を追加した最終3件は28.810秒PASS。

両端位置と電気/磁気対称の4条件の実FEM場を、各比較版で比較する。
同じセクターの半領域と全領域の重なり一致、全体積・要素数・サンプル数2倍を確認する。
電気対称場の鏡映側だけ符号を変える検査用の非固有場では、元半領域係数を変えずに
全領域重なりがゼロとなりUNVERIFIEDになることを要求する。
これにより、半領域だけを読んで全領域を比較したとする誤実装を検出する。
両側分の予算拒否と、楕円弧を持つnative保存の版2〜5再生・改変拒否も確認した。

関連34件65.809秒PASS。

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=tests:src .venv/bin/python -m unittest \
 test_te_symmetry_piecewise_tracking test_te_curved_tracking \
 test_curved_piecewise_remesh_tracking test_curved_reference_partition \
 test_curved_comparison_overlay test_te_reflection
```

専用native検証では前工程の楕円弧4半領域解（2形状×原寸/倍寸）を再利用し、
既存の幾何・係数鏡映で4全領域結果を保存する。新しい固有値計算は0回である。
鏡映時には全領域FEM行列を組み立てて既存の残差・規格化検査を行うが、別の固有値解法で解いたとは数えない。
版2〜5の8保存比較がPASSし、全再生一致、元半領域の重なりと全体積2倍を確認した。
周波数不変、U/壁損失2倍、G/Q0不変を別判定し、相対差最大1.333e-15。
前工程のMaxwell尺度則・独立積分の証拠は再利用する。
元36ファイル・新しい鏡映40ファイルのhashを保持した。

離散化誤差、サンプル次数収束、連続した物理枝、全スペクトルの順位をこの結果から保証しない。
FEM定式化/固有値解法は変更せず、full/seed validator・hosted CIは今回未実行。
新規外部資料・旧コード・旧バイナリは利用していない。

CLIの鏡映版5再生もREPLAYED PASS、追加固有値計算0。
[集約結果](../benchmarks/tuning/te-reflected-piecewise-20260915.json)を保存した。全handle終端。
次はこの写像基盤を非アフィン対称Project変形とtune/Studyへ接続する。全計画goalは継続中。
