# 元直線TM形状法則と調整

2026-10-07、D02コア限定受入。D02全条件・親D02/P01・全goalは未完。

## 契約

通常 scalar TM tune の版9に、D01で固定した
straight_piecewise_shape_law/version 1を接続する。対象は真空・閉PEC・軸接続m=0 TMの
profile、stepped_profile、単一直線contour、geometry_order=1。
TE、組立、鏡映、明示solver meshは事前拒否する。TE対応はD03。

shape_lawは完全な元reference_comparison_mesh、各元Case境界頂点を一対一で所有する
case_boundary_vertices、SI長さ式のbindingsを持つ。全座標を元参照からまとめて更新し、
毎回Caseと比較meshの全領域・壁tags・軸originを検証する。
段差の元垂直辺/非垂直辺の役割を保持する。順次変形やsolver meshの代用を行わない。

controlsは既存piecewise_remeshテンプレートで、入力comparison_meshesを許可しない。
両試行の元値から実比較meshを再構築し、全Project属性と元検索/宣言細分の一致を要求する。
最終細分は既存Study.mesh_convergenceを使う。保存読取/再開/全再生は既存所有形式。
版6の明示ID回復wrapperでも、内側版9を同じ検証へ渡す。

## 独立受入と未達

独立Bessel TM010円筒で、f、元Hφ/Ez/Er、全PEC壁loss、両R/Q、
1 J peak-phasor normalizationを別検査した。最終細分で各誤差が減少した。
元実段差では周波数逆尺度、元E/Hの長さ尺度の-3/2乗、
体積三乗、G不変、Q平方根、両R/Q不変と完全保存再生を検査した。

元粗段差の粗細差83,248.404 Hzは、元二つの10,000 Hz条件を超えて
REFINEMENT_FAILEDのまま保持する。角局所細分の別系列
(nr=32/nz=48, corner_radius_m=.0078125, corner_max_edge_m=.00048828125、
最終64/96/edge半分)は差6,239.675 Hzで元条件を満たした。
元折返し輪郭は元1 Hz細分条件未達を正しく保持し、成功受入とは扱わない。
無効中間形状は次のFEM前に拒否し、旧checkpoint/native全byteを保持。
実曖昧IDは周波数null、最終細分なし、UNVERIFIEDで停止した。

## 検査と来歴

raw: out/d02-straight-tuning-20261007/。
metadata-final.log 6件0.257秒、cylinder-reconstructed-test.log 1件2.931秒、
remaining-physical-tests.logの無効形状1件成功と、
repaired-and-refined-tests.log 4件17.142秒を合わせ、新規12個別検査。
直接消費はdirect-consumers.logの成功36、supplement-direct-consumers.logの成功2、
corrected-missing-consumers.logの成功2で計40個別検査。全52個別成功の元ID/logは
bounded-audit-pre-docs.json。失敗を含むコマンドの終了1を終了0へ改記しない。

元検査のNumPy scalar、保存namespace行列不足、pilot Case参照、範囲外cluster設定、
誤ったunittest selectorのERRORを保全した。検査用読取は元basis行列を再構築し
残差を確認するが、固有値を再求解せず元場も変更しない。
成功済み旧検査のASTを保持し、不足・失敗分だけ修正/補完した。
全1182 Python源を数値開始/終端で固定。旧製品変更はtuningの
_request/_geometry_project/pair_controlsと回復wrapperのvalidate_requestのみ。
科学核/RF積分/旧閾値は不変。全handle実終端、新full/seed/legacy0。
新依存・外部資料・GPU・hosted CIを使用していない。

未完は版9GUI入力復元/構築、API/CLI/実GUIの元要求・最終場・両R/Q一致、
一般輪郭成功系列、D02全原条件監査。既存GUI旧版の検査を新版実操作へ数えない。
