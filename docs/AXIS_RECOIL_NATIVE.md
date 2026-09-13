# S03: 軸接続の反跳材料の保存・再構築・CLI

2026-09-13 JST。固定773sourceを主779sourceへ統合し、専用API範囲で限定受入。

[限定計画](AXIS_RECOIL_NATIVE_PLAN.md)の専用5ファイルとsolve/replay/probe-axis-recoilを実装した。全材料テンソル/残留B/向き・軸接触・phiモデル、幾何/穴・所有/界面・面積/3次元体積、電流/残留/境界の三荷重と全DOF、a=Aphi/rを保持する。同じ実FEMの再求解で元6場・J単位の構成ポテンシャル・磁束/周回/反力と規約を照合する。

manifestを最後に公開し、既存出力・symlink・不完全保存・再hash後の物理的虚偽も拒否する。元セルの片側H=nu(B−Brem)、軸上Aphi=Br=Hr=0、有限Bzと材料正則性を保持する。固定a反力[A m²]を電流[A]へ変換しない。能力表は有限軸接続領域の専用API/CLIを示し、GUI/Project/Studyは未対応とする。

追加4unitは8.608秒でPASS。P1/P2の一様残留場/向き付きパッチ/二層、穴2個の一定電流、零場の8保存を用いた。テンソル・残留B・向き・phi透磁率/軸接触・三荷重・DOF/dtype・係数・全構成ポテンシャル・元H反力/磁束/規約・manifestの改変、公開中断を検査した。プローブのHを返却されたmuテンソルとB−Bremから別に復元して照合した。

旧能力表3unit・3CLIスモーク、独立24例48native/80CLIがPASS。API/CLIの5ファイルと全プローブJSONは一致し、元240native/98参照ファイルは不変。標準1238件もPASS。独立証拠はout/axis-recoil-native-independent-refined-20260913/report.json、標準はout/validation-axis-recoil-native-candidate-20260913。固定候補は編集しない。新規依存・外部資料・旧版実行なし。軸非接続・対象版モデル確認、S03/全計画は未完。

独立CLI検証の初回は、参照ファイルのcaseキーと解析診断を含む外側のオブジェクトをCaseとして渡したため、厳密パーサーが拒否した。元候補とログを残し、参照Caseを新しい試験用入力へ取り出す検証アダプターだけを直した別候補で再検証しPASS。製品・unit・解析参照・許容値は全件同一。標準は元の固定773sourceで実行し、改訂候補との唯一の差分と全hashをreference-envelope-decision.jsonに保持する。改訂候補で全標準を再実行したとは扱わない。

独立24例は126.276秒でPASS。改訂773sourceと標準の元773sourceの差分は参照Caseの取り出しを行う検証スクリプト1件のみ。

独立24例は126.276秒でPASS。標準2439.571秒、1235合格・任意NGSolve参照2件/HTTP環境1件skip、ResourceWarningなし。主4unitは8.381秒でPASS。独立の固定773sourceと主779source（不変egg-info 6件）は完全一致。独立例を主で全再実行したとは扱わない。旧ベンチマーク・許容差不変。統合証拠は標準出力内seed_regression.json。
標準は参照アダプター改訂前の固定773source。製品・unit・解析参照・許容値は全件一致し、検証スクリプトの参照Case取り出しだけが異なる。元/改訂の全hashと唯一の差分をseed_regression.jsonとreference-envelope-decision.jsonで保持し、改訂候補で全標準を再実行したとは扱わない。
