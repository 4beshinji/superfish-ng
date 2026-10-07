# 元直線TM形状法則と調整

2026-10-07更新：D02原カードは [条件別監査](STRAIGHT_TM_TUNING_ACCEPTANCE.md) でDONE。以下の限定受入は実装段階の履歴。一般輪郭の数値未達と親D02/P01/全goalの未完を維持する。

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

コア受入時の未完項目のうちGUI/入口一致は下記で受入。一般輪郭成功系列とD02全原条件監査が残る。


## GUIと入口一致

2026-10-07、コア9b6e091後の限定受入。
実Chrome/153の元段差2試行PAUSEDで、変更方法linearへの誤復元を先に再現した。
専用「直線境界の局所変形」入力に全法則を復元し、元Projectと追跡判定も戻す。
形状法則のraw JSONを保持し、重複キーをサーバーのstrict parserで求解前に拒否する。

scripts/verify_gui_straight_tuning.mjsは既存browser-session.mjsを使用し、
外部要求を遮断、元source hash、実クリック/入力、保存download、改竄拒否、
元要求完全再構築、実再開、両gate、元個別順位の最終場表示を確認する。
必須 --url/--out/--request、任意 --checkpoint で元PAUSEDを再利用する。
raw: out/d02-straight-gui-20261007/。baseline.log終了1、corrected.log終了0、7項目PASS。
1275源は開始/終端で不変、ブラウザーslotとサーバーは全終端した。

同じ原要求を独立API execute_tuneとCLI tuneで実行し、両方4試行TUNED・終了0。
元最終mesh/Case、Hφ/Er/Ez、f/U/Ue/Um/Pwall/Q/G/両R/Qの相対差はGUIと0
（確認閾値1e-10）。表示用importのfields.npz/case/results/modes/axis/VTKも元byte一致。
api-cli-receipt.jsonとleaf-audit.jsonに原結果/差/範囲を保存。
初回比較runnerが誤ってtune.jsonを読んだ終了1を保全し、
正しいcheckpoint-004.jsonの原結果を読取/全再生するだけで終了0に修正。
修正比較内の新eig求解0。文書のための再求解・full/seed/legacyは行わない。
Python製品・元検査は9b6e091から不変。全D02/一般輪郭成功の受入とは区別する。
