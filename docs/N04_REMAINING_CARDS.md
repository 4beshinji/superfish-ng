# 親N04残件4の具体的な仕様工程

2026-10-08 JST、[N08受入監査](N08_ACCEPTANCE.md)で既存残件を再照合した。
新しい物理やユーザー範囲の追加ではなく、[N04の既存残件4](N04_ACCEPTANCE.md)を分割する。
原123カードを保持し、追加3仕様カードと選択移送/境界生成それぞれの必須五後続カードをTSVに登録する。
選択移送01〜06と境界生成01〜03はDONE。境界生成04〜06とRF仕様01はPLANNED。全136は85/2/49。
仕様カードは着手可能。未確定の入力/数値ゲートを持つ実装カードをreadyとしない。
仕様の受入後、[L05の具体カード化手順](development-plan/08-external.md#条件付き要件から追加カードを作る手順)
に沿って必要な入力/計算/保存/操作/独立受入を接続し、親N04の依存へ追加する。

## ADD-N04-selection-charts-01

**親N04、先行N08、種別仕様、状態DONE**。
[版2七項目/保存/全被覆/対称/実装五工程の固定仕様](CURVED_SELECTION_CHARTS_SPEC.md)を2026-10-08受入。
六例/既存幾何の読取検証に続き、[strict入力02](CURVED_SELECTION_CHARTS_INPUT.md)もDONE。
[03計算API](CURVED_SELECTION_CHARTS_CORE.md)もDONE。GUI・専用FEMは05/06。
[04完全再生/CLI](CURVED_SELECTION_CHARTS_SAVED.md)・[05 GUI](CURVED_SELECTION_CHARTS_GUI.md)・
[06独立受入](CURVED_SELECTION_CHARTS_ACCEPTANCE.md)もDONE。次はADD-N04-boundary-remesh-01。
異なる初期接続・頂点数・境界分割を持つ二Project間の選択領域移送を仕様化する。
仕様01受入時点の `curved_selection_transfer.transfer_curved_cell_selection` / `_validate_request` /
`replay_curved_selection_transfer` は版1で、初期一対一対応を必須とした。
既存 `curved_reference_partition` の版5明示参照座標・境界折線と
`planar_tracking_overlap` の有理数交差を再利用できるか、実入力/拒否例で評価する。

納品は `docs/CURVED_SELECTION_CHARTS_SPEC.md`、厳密な正常/拒否要求例、実装・利用先の子カード。
共通参照三角形の旧選択領域Sと新要素Tについて、`intersects`はarea(S∩T)>0、
`contained`はarea(S∩T)=area(T)と定義し、全旧選択の被覆総和を有理数で厳密に照合する。
異なる物理領域を座標の近さで推測せず、利用者の全参照宣言・P2物理写像を保持する。
同じ宣言の変更/改竄、重複/未知キー、不正型、向き/被覆/タグ不一致、求積/組数予算、
元版1とGUI選択の互換、保存再生と途中応答拒否を仕様で固定する。
独立矩形の面積・Green回転体積・Hφ=r幾何質量、非アフィンP2/尺度/逆方向と
新選択markedを使う実FEM/RFを分け、精度ゲートと新求解数を実行前に定める。
仕様段階の確認は入力・独立幾何・差分で十分で、仕様だけのための全FEM/fullは不要。
版5比較があることだけを新選択移送の実装受入に使わない。

## ADD-N04-boundary-remesh-01

**親N04、先行N08、種別仕様、状態DONE**。
[版2仕様](CURVED_BOUNDARY_REMESH_SPEC.md)を2026-10-13受入。元P2制限の表現probe/正常拒否例を確認し、必須02〜06をTSVへ接続した。[02 strict入力](CURVED_BOUNDARY_REMESH_INPUT.md)もDONE。[03生成API](CURVED_BOUNDARY_REMESH_CORE.md)もDONE。次は04の完全保存再生/CLI。
二次境界の分割数を変更できる再メッシュ生成の範囲と表現を固定する。
現行 `curved_remesh_generation.generate_curved_remesh_plan` / `_boundary_case` /
`_size_marks` は元二次境界を固定し、境界サイズと競合すると拒否する。
既存 `curved_project_remesh` の新履歴・全二次境界一致検査と、
`curved_refinement` / `curved_marked_refinement` の元P2制限写像を入口とする。

納品は `docs/CURVED_BOUNDARY_REMESH_SPEC.md`、元境界を細分する正常例と不可能な粗化/サイズ拒否例、
実装・保存/CLI/Study GUI・独立受入の子カード。
元P2パラメトリック辺x(t)の区間制限x(a+(b-a)s)を保持する分割と、
解析曲線へ再投影して幾何誤差が変わる処理を仕様上で分離する。
外部メッシュ/Caseがこの制限写像を保持できるか実装入口から確認し、必要な専用表現を決める。
表現できない操作を成功扱いしない。元幾何/材料/対称tag、軸接続・正Jacobian、
全境界の所有/向き、要素/辺長/面積/角度予算とunknown/重複/改変の拒否を固定する。
独立Green面積/体積・Hφ=r質量、元P2境界の全区間一致、尺度則、親子Galerkin保存、
実円筒解析f/RFと非アフィン曲線の全場保存再生を別ゲートで計画する。
元幾何を保たない方法を採用する場合はN03の幾何/FEM誤差分離と独立比較を先行条件へ追加する。
仕様の通常判断は自走し、旧資産・新依存・外部サービスを必要条件にしない。

## ADD-N04-rf-goal-01

**親N04、先行N08、種別仕様、状態PLANNED**。
残件2に残したRF重み付き版5の一般ケース対照を、有限な実行・独立精度/費用条件へ展開する。
N05/N06の残差版3/4対照は版5の確認branch/全event費用を検査したものではない。
`curved_rf_adaptive_refinement.validate_request` / `next_plan` と
`curved_rf_goal_indicator.curved_rf_goal_indicator`、元版5保存/GUI、
`adaptive_efficiency_timing` を入口とする。
納品は `docs/CURVED_RF_GOAL_EFFICIENCY_SPEC.md` と固定要求/独立参照・後続検証カード。
N03/N05の球・丸めと既存回転楕円体から正常/未達の対照を選び、元全ID・全壁・両R/Q/G・
表面peak両端・全E/H/物理軸場を保持する。元版5の親branch、棄却確認event、表面方針、
全event求解/検証/保存費用を片側だけ除外せず、方式/反復/目標/予算を実行前に固定する。
既存の球/楕円の適応非優位とR/Q単独でsurface未達だった結果を残す。
独立参照が欠ける量はUNVERIFIED、成功しない停止も費用を保存する。
仕様はゲート・入力・実装関数・拒否例を全て埋めてから受入し、優位がなければ実測された
非優位を結果として受入する。普遍的収束/効率や誤差上界の証明を要求に加えない。

三カードとその必須実装/独立受入が終わるまで、親N04はIN_PROGRESS。
原一般形状/効率はN03/N05/N06/N07の条件別実測へ対応済みで、普遍的優位や
連続問題の数学的誤差証明を新たな完走条件として発明しない。
