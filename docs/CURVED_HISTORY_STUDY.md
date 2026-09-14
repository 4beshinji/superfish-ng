# 局所履歴を保持した固定形状Study

2026-09-14追補：固定履歴を持つ非アフィンな曲線形状掃引は[曲線法則Study版3](CURVED_HARMONIC_STUDY.md)へ接続した。本書の固定領域細分比較/版1とは区別する。

2026-09-14追補：固定形状のStudy版1は維持し、別の[宣言アフィンStudy版2](CURVED_AFFINE_STUDY.md)を追加した。元メッシュと履歴を保持する形状掃引・保存追跡/逐次・適応再開に対応する。以下の固定領域の収束比較とは区別する。

2026-09-09。`fixed_geometry_convergence`に
`parameter: "additional_uniform_refinements"`を追加する。
`project.case.mesh.curved_refinement_steps`がある場合だけ使用でき、
`values: [0, 1, 2]`は既存履歴の末尾へ追加する一様細分段数を意味する。
0は履歴付きの元Caseそのもの。各点は元Caseから独立に構築するため、
前点の追加段数を次点へ累積しない。

既存の `/case/mesh/curved_refinement_levels` は履歴なしCaseの絶対段数を意味し、
従来の意味を変更しない。履歴ありCaseでのmesh/geometry convergenceやsweepは、
要素番号を別の初期メッシュへ流用する危険を避けるため引き続き拒否する。
未知パラメーター、負数・非整数・非増加系列を拒否。
一様段数から明らかに要素予算を超える入力は履歴配列を確保する前に拒否し、
実メッシュ生成でも従来どおり実要素数・品質・予算を検査する。

Study版1のkind/parameter契約を拡張した。旧実装は新パラメーターを拒否する。
API・CLI/JobManagerは既存Study経路を使う。
GUIは現在のCaseに履歴があれば「保存履歴の後に追加する一様細分段数」を表示し、
保存文書へ同じ明示パラメーターを出力する。

このStudyの比較は既存の周波数/RF/場の照合であり、一般モード追跡や
物理表面ピークの収束保証を追加しない。適応停止・個別ID追跡・ピーク区間は
[適応版4](CURVED_ADAPTIVE_REFINEMENT.md)と[親子追跡](NESTED_CURVED_TRACKING.md)を使う。

## 受入条件と証拠

`tests/test_curved_history_study.py`で保存往復・変更後メッシュへの流用拒否、
実FEM/native保存で元メッシュ一致と要素数4倍を確認する。
独立物理不変量は二次写像上の `2π∫r det(J)` の不変と
入れ子部分空間のRitz周波数単調性。積分は写像の多項式次数を満たす規則を使う。
追加2検査は1.939秒でPASS。

修正前は両検査が履歴付きStudyの一律拒否で失敗した
(`out/curved-history-study-evidence-20260909/curved-history-study-red-contract.log`)。
最初の検査スクリプト実行は積分関数のimport先誤記で計算前に失敗し、
`fem`の既存関数へ修正した (`out/curved-history-study-evidence-20260909/curved-history-study-red.log`)。

GUI `out/browser-curved-history-study-20260909` の23項目がPASS。
対象ソース変更なし、外部HTTP要求なし。実Studyの保存結果でも
180→720要素、元メッシュhash一致、元局所履歴の後への一様段階追加を確認した。
同じ保存StudyをCLIでも実行した (`out/cli-curved-history-study-20260909`)。
GUI/CLIのstudy-results文書は完全一致。2水準の周波数差1.265e-6と軸場差
0.001515は条件内だが、両R/Q差0.034583とTTF差0.016522がRF条件0.01を超えるため、
数値判定FAIL、CLI終了1を維持した。これは収束未達を正しく示す受入例であり、
Study実装の合格を物理収束の合格へ読み替えない。
標準回帰 `out/validation-curved-history-study-20260909` はPASS。
658件中656合格・2 skip、404.889秒。seed周波数差ゼロ、RF最大相対差8.882e-16。
全対象ソースの最終hashとブラウザー検証ソースの一致を確認した。
数値公式・許容差・新規依存・外部参照の変更なし。
