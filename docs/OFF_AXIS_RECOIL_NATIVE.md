# S03: 軸非接続の反跳材料の保存・再構築・CLI

2026-09-13 JST。固定786sourceを主792sourceへ統合し、専用API範囲で限定受入。

[限定計画](OFF_AXIS_RECOIL_NATIVE_PLAN.md)の専用5ファイル保存とsolve/replay/probe-off-axis-recoilを追加した。全テンソル/残留B/向き・phiモデル、全Jphiと三荷重、境界と穴、psi基準と相対/絶対係数を保持する。同じ実FEMを再構築して元6場、Jの構成ポテンシャル、Wb磁束、A周回/反力と規約を照合する。能力表は専用APIの範囲を示し、Project/GUI/Studyは未対応とする。

manifestを最後に公開し、既存出力・symlink・不完全保存・再hashされた物理改変を拒否する。追加4unitは31.621秒でPASS。非零psiを持つB=0/有限H、向き付き材料界面、二層、P1/P2電流源と複数穴、零場を再構築した。テンソル/残留B/向き/phi透磁率、三荷重、所有、係数/基準/dtype、各構成ポテンシャル・元反力/磁束・規約の改変と公開中断も検査した。既存能力表3unitもPASS。

3CLIスモークでAPI/CLIの5ファイルの全バイト一致と、元場・材料・出典hashを含む全プローブJSONの一致を確認した。共有点は厳密に表されたメッシュ頂点を使い、接続する最小セル番号の元片側場を照合する。

独立解析済み24例の48native/80CLI、元240native/98参照ファイル不変を確認した。標準1255件をout/validation-off-axis-recoil-native-candidate-20260913へ終了0。固定候補は不変。

新規依存・この工程の追加外部資料・旧版実行なし。合成材料のみ。対象版材料モデル、S03と全計画は未完。

独立保存比較は214.712秒でPASS。証拠はout/off-axis-recoil-native-independent-20260913/report.json。標準と同じ固定786sourceを用い、保存元は最終96例の固定783sourceとCLI/能力表3件を除き一致する。API/CLI各24保存の全5ファイルが一致し、元場とtensor/remanence/orientationを含む全プローブJSONも一致した。

標準2636.430秒、1252合格・任意NGSolve参照2件/HTTP環境1件skip、ResourceWarningなし。主4unitは31.899秒でPASS。標準/独立の固定786sourceと主792source（不変egg-info 6件）は完全一致。独立例を主で全再実行したとは扱わない。旧ベンチマーク・許容差不変。統合証拠は標準出力内seed_regression.json。
