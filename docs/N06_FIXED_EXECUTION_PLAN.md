# N06：同じ初期入力と独立12実行の固定

2026-10-07、N06の実行前入力だけを限定受入。N06はIN_PROGRESS。
[N05仕様](N05_ADAPTIVE_EFFICIENCY_PLAN.md)の三ケース・二方式・二反復を固定する。
主N03全検証中の1405対象ファイルには変更を加えず、別ツリーで実装/検査した。

`adaptive_efficiency_plan.build_adaptive_efficiency_plan` は円筒/球の元例題要求と、
N03の丸め二ローブ幾何2・FEM0の完全Case/元source meshをSHAで固定する。
丸めの二入力は `examples/adaptive_efficiency/` へ保存元と同じbyteで追加した。
元Case SHA `2b426b617de7f1c36a9f63f340817abf81322781b0a8882299372ccaa3d9ac90`、
元mesh SHA `959c056225acbeb7dcc860a4260f1d0fbe00caabc9413331197e903b63319fe7`。
これは既存の合成入力であり、実機の測定・legacy資産・独立解の転用ではない。
この入力追加でignored outがないcheckoutでも同じ初期meshを使用できる。
独立場の大容量NPZ/solver保存は製品へ追加せず、参照検査では別途必要とする。

全四入力は通常ファイル/非symlink/完全SHAを読み取り前後で検査する。
未知キー・対応物理/meshは既存strict reader/適応request validatorで確認する。
原Case/P2場・モード数・元controls・初期source meshは不変。
円筒は明示版3の離散ピーク上下界も要求し、元0.95の追跡条件を維持する。
球は元版4/0.95/一モードを保つ。丸めは版4/三ID target・guard-2・guard-3/0.98。
球の元範囲を新丸めのguard証拠へ流用しない。

変更するのはN05で先に決めた要求値だけ：8水準、250000要素（Caseの小さい上限を優先）、
bulk0.5、元より緩くしない最小角5度、全域確認二回、f1e-4、R/Q・G0.005、peak0.01、
曲線求積24と1e-6。曲線Caseの元基底次数12は変更しない。
外側の共通比較条件には回路R/Q0.005と元E/H全域0.005、軸Ez0.01も保持する。
既存adaptive requestに未対応の量を付け足さず、これらは後続の独立参照判定で確認する。

実行順は各ケースで反復1一様→適応、反復2適応→一様、計12行。
各行は同じCase/sourceの独立copyと3600秒/32 GiBを持ち、初回の新FEMを両方式に要求する。
方式ごとの成果物を別反復へ再利用しない。計画の状態はPLANNED、実行行はNOT_RUN、
new_fem_solves=0、physical_acceptance_status=NOT_RUN、physical_error_bound=null。
全方式の数値を実行済み/確認済みにはしない。

## 検査と来歴

未実装moduleのImportErrorをbaselineとして保全。
新5個別unitは1.396秒・終了0/PASS。
元円筒/球の全Case/source/controls不変、丸め保存元の二SHA/完全初期入力・P2/12次、
二反復の順序/予算/独立copy（後続変更が別行へ漏れない）、
全四入力の1byte変更と欠落/symlinkがvalidator/FEM前に拒否されることを確認した。
ignored outや参照solverに依存しない。古い数値unitを再実行していない。

`uv run --no-sync python -m unittest -v test_adaptive_efficiency_plan` をtempの
明示PYTHONPATHで実行した。元1200源/既受入計測器・停止器の四源は不変。
temp1206 Python源と二新入力を固定し、main全1405対象源の不変を確認する。
主の生成egg-info六点はtempに存在せず、temp全対象は1407点。
共通元1399点は全byte一致。最初の監査の1413点という仮定はその六点を
考慮していなかったため失敗した。元logを保全して監査だけを修正し、数値/検査は再実行しない。
rawは `out/n06-cost-recording-20261007/input-plan-*.log`、`fixed-execution-plan.json`、
`input-plan-acceptance.json`。新FEM/seed/full/GUI/12benchmarkは0。

主統合はN03全検証終端後。均等/局所細分の実worker、全段階の費用、元全域E/Hと
RF/peakの量別精度・二回全域確認、三ケース各二反復の実成果物は後続である。
この段階でN06・親N04・全goalを閉じない。
