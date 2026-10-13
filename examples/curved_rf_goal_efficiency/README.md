# RF重み付き版5の固定対照入力

[仕様](../../docs/CURVED_RF_GOAL_EFFICIENCY_SPEC.md)の計算前入力。
`plan.json`は三形状×二尺度×三方式×二反復の36行を固定する。
六要求は公開版5の厳密入力で、初期meshを明示している。
方式ごとに`surface_refinement_policy`を明示変更し、一様対照は専用workerで扱う。
元のCase/ID/全壁/規格化/精度を変更して同じ比較行と呼ばない。

尺度aの規格化はa² J（1/4 J）。球/丸めは元N05計画、長球は既存RF表面方針例に由来する。
`refusals.json`は後続実装の拒否契約であり、全例の実装済みを示すものではない。
`reference_sources.json`は現存する参照準備の入口と旧未達reportのSHAを固定する。
参照データ自体はignored `out/`の研究成果物で、配布ファイルへ同梱しない。
仕様時の実検査は六入力の初期幾何と現行六拒否例のみ。新FEM0、物理精度/費用は未実行。
独立参照・新worker・36行実行・保存GUIの受入はADD-N04-rf-goal-02〜06。
