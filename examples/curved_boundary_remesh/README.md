# 元P2境界を保つ再メッシュ生成版2の仕様例

[仕様と受入条件](../../docs/CURVED_BOUNDARY_REMESH_SPEC.md)。
2026-10-13の[03生成API受入](../../docs/CURVED_BOUNDARY_REMESH_CORE.md)で公開版2を接続した。
正常二例の生成と拒否二例の予算違反を確認済み。
[04完全保存再生/CLI](../../docs/CURVED_BOUNDARY_REMESH_SAVED.md)と
[05 GUI/worker](../../docs/CURVED_BOUNDARY_REMESH_GUI.md)も受入済み。専用6 FEMは06で受入する。

| Project | 設定 | 期待 |
|---|---|---|
| rectangle-project.json | rectangle-settings.json | 元4境界辺から32辺、128要素。SIの合成円筒断面 |
| nonaffine-project.json | nonaffine-settings.json | 元最終24境界辺から28辺、84要素。合成半楕円断面 |
| nonaffine-project.json | reject-root-coarsening.json | 元初期10区間を9辺以下にする要求を拒否。元区間併合は未対応 |
| nonaffine-project.json | reject-size-budget.json | 元区間は収まるがサイズ要求の追加分割が上限10辺と競合して拒否 |

最終要素数は固定試作の証拠であり最適性の保証ではない。
境界分割は元P2の制限写像。解析楕円への再投影を行わない。
旧版1は従来の初期弦メッシュへのサイズ制限を維持する。
この入力はKEK/LANL測定構造ではない。元fixtureをJSON化した独立合成例である。
