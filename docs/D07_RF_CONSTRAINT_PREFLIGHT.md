# D07：RF制約収束の読取準備

2026-10-07。N03の節目全validate実行中に行った読取調査。
D07はPLANNED、実装/数値受入は未実施。先行D06はDONE、N03全受入を待つ。
現在の検証源1200を変更しない。原カードの条件/対象を追加仕様で上書きしない。

## 現在の接続と欠落

曲線要求1〜3は `rf_optimization._projects` が探索0/1/2と最終1/2/3を別に求解し、
`_assemble` が元保存場の個別ID履歴を再構築して `assess_rf_design` へ渡す。
`rf_design._evaluate_design` は三水準の全包絡と量別制約を評価し、
境界をまたぐ制約をUNRESOLVED、精度未達をUNVERIFIED/eligible_value=nullにする。
`rf_optimization_search.decision` は最終別系列のCRITERIA_METだけをSEARCH_COMPLETEにする。
旧成功/失敗・独立球解析/保存再生の証拠は [既存RF探索](RF_OPTIMIZATION.md) にある。

直線D06の `straight_rf_candidate_search` は実三水準と元Project/比較領域/個別IDを保存するが、
すべてassessment=null、rf_assessments=0、終端はFINAL_UNVERIFIED。
strict要求版1はcriteriaを拒否する。未評価の値を採用へ渡さないための意図した制限である。
`surface_convergence.assess_surface_convergence` はCurvedSolution/curved_same_domainと
同一source meshを要求し、直線のpiecewise_remesh履歴を流用できない。
`affine_surface_convergence` は所有adaptive checkpoint専用で、D06の候補履歴を受け付けない。

したがって不足は、元直線候補の固定物理幾何を確認した量別三水準評価と、
その評価を別の明示要求/完全再生/最終別系列へ接続する部分である。
曲線の既存三水準やN03の全域比較を直線候補の受入済み評価と呼ばない。

## 次の一つの実装範囲

まず直線TMの保存三水準から、対象の実個別ID、完全Case/元幾何、
SI・peak規格化と全PEC壁の元RF/離散peak包絡を確認する評価leafを追加する。
元curve評価器やFEM核を直線用に書き換えない。保存場の読込・離散包絡の既存APIを利用する。
P1/P2、軸、端壁、全境界componentを省略せず、実メッシュ差と幾何差を分ける。
再入角では有限物理peak受入を作らず、未対応/未確認を理由とnullで保つ。
このleafだけの受入を探索・所有保存・CLI/GUIやD07全条件の受入に昇格しない。

最低限の独立不変量は円筒TM010のBessel周波数/元Hφ・Ez、全壁loss、
両R/Qのfactor2と固定Uの尺度則。解析をFEMの代わりに返さない。
三水準の物理誤差減少と二変化を別に確認し、残差を離散化誤差と扱わない。
元D06保存nativeを再利用できる場合は元byte/法則/Caseを照合し、数値を上書きしない。

続く接続では旧D06要求版1とnullの意味を維持し、評価を求める新要求で
mode_id/criteria/単位付きconstraint_scales/改善量を明示する。
初期/探索/最終の全判定・包絡・失敗/未確認理由を完全再生し、
目的改善だけで成功へ進まない。予算は初期・失敗・予約最終を含める。
「最終独立系列」は同じ規約の別FEM系列であり、独立現代solverの意味と区別する。

## 受入を確認する順序

1. 元D06でRF採用が未実装であることと、新leafを呼ぶ入口がないことを先に確認する。
2. 新leafの独立円筒物理と、上下界が制約をまたぐ反例・欠測/ID未確認・鋭角を検査する。
3. 全包絡が満たす条件、粗細で採否/順位が変わる例、予約最終/計算上限の例を確認する。
4. 既存曲線版1〜3の元保存再生と数値gateが不変であることを、直接消費検査で確認する。
5. 元カードの探索/独立最終系列/保存/失敗条件をすべて照合してからD07を閉じる。

読取対象は `straight_rf_candidate_search.py`、`rf_optimization.py`、`rf_design.py`、
`rf_optimization_search.py`、`surface_convergence.py`、`affine_surface_convergence.py` と
対応する既存tests/仕様書。今回の新unit/FEM/seed/fullは0（N03全検証は別実行中）。
N03終了後に `docs/TESTING.md` から新leafと直接消費の個別検査を選ぶ。
