# P08：曲線native・操作経路の実装準備

2026-10-07。P07実検証中の読取調査。P08は未着手であり、この計画は製品の接続・受入証拠ではない。
先行条件は[P07全条件監査](PLANAR_CURVED_ACCEPTANCE.md)。主source/実検証checkoutの固定を維持する。

同日追記：P07全条件を受入れ主sourceをfe25aadで統合した。全数値handle終端、固定解除。
P08の先行条件が成立したため、下記の版付きnative保存・全配列/RF再構築から実装する。
この読取計画自体をP08実装/受入へ数えない。

## 現行コードで必要な変更

専用`PlanarCurvedCase`は既に`superfish_ng_planar_case` schema_version 3を厳密に読込み、
`geometry.domain`内に全二次node/六node cell/三node壁を保存する。
一方、既存`planar_polygon.planar_case_from_dict`、`PlanarProject`、`planar_saved`は矩形/多角形の版1/2を対象とする。
`planar_jobs`のworkerは`solve_planar`へ、Studyのscaleは版2の直線mesh配列へ直接接続する。
`planar_display`は`space.triangles/cell_dofs`とbarycentricの直線点を使い、曲線空間の
`cell_nodes/boundary_nodes/boundary_local_edges`・二次写像をまだ扱わない。
型だけを許可すると保存/再構築/Study/表示が不整合になるため、次の順序で直接利用先まで接続する。

| 実装単位 | 入口・直接利用先 | 独立受入と限定検査 |
| --- | --- | --- |
| 版3 Caseの明示dispatch | `planar_polygon.planar_case_from_dict`、`planar_project`、専用solverへのdispatch | Case/Project往復の全二次配列・numerics保持。版とgeometryの不一致/unsupported physicsをsolve前拒否。旧版1/2 parser/Projectの直接利用test |
| 曲線native保存・再構築 | `planar_saved`と新曲線専用保存helper、`planar_curved_fem/solver` | 同じ全二次DomainからK/M/free/最低正帯を再構築。元係数/周波数dtypeとbytes・全RF metadata、全TM壁拘束、TE核を検査。geometry/係数/帯/結果の各改変を再hashしても拒否。旧native読取/保存test |
| CLIと元点probe | `cli`のsolve/replay/probe-planar、`planar_display` | 独立API対CLIの元配列/全RF一致。strict曲線point locationと全12phasor SI場を直接比較。理由付きR/Q/Vacc/Eacc N/Aを維持 |
| Project workerと所有中止 | `planar_jobs`、`jobs`の既存planar経路 | 完成manifest・実装source hash・全native bindingを保持。実processを中止し終端を観測、既存出力を上書きせず新jobとして再起動。importは新solveと区別。直接jobs test |
| 独立Study | `planar_study`と`planar_study_jobs` | 全二次nodeを同じ正scaleで変換し、cell/壁接続を保持。RF energy/σ sweepはgeometry保持。矩形寸法sweepを曲線へ適用しない。実二尺度のf/E/H/RF則を独立に検査 |
| 元場表示・GUI操作 | `planar_display/visualize`、`gui_planar`、既存静的UI | display vertex/centroidを元二次写像から生成し、元owner/refで場を評価。元二次壁を表示。GUI/API/CLIの保存配列・全RF・signed probe一致、実中止/再起動・旧矩形/多角形の再生 |

曲線nativeは既存五fileのcompletion/regular-file/hash検査を保ち、case版とmesh配列schemaを一致させる。
P07検証器の`fem-fields.npz`は製品nativeではない。検証adapterや診断のないraw frameをnativeへ流用しない。
元写像/係数を持つ`PlanarCurvedSolution`を使い、表示の細分三角形や直線補間からRFを作らない。

## 着手と検査方針

P07の受入・主source統合後、最初はCase/Project/solver dispatchとnativeだけの有界変更として実装する。
変更契約の独立反例を先に再現し、各直接利用先のunittestを一回実施する。
CLI/worker/Study/GUIは順に接続し、未実装経路へ曲線Caseを黙って通さない。
既存P04の比較/収束/追跡/調整が共有parserから曲線を受け取る場合、P09で実装するまでは
対象経路の入口で明示拒否する。mode indexをidentityへ読み替えない。

P08全受入には独立API/CLI/GUI、改変拒否、実中止/再起動、旧保存再生が全て必要。
限定nativeの成功だけでDONEにしない。共有dispatchの影響が境界内に収まらない場合や
実際のmilestoneではAGENTSのfull validate条件を適用し、先行full discoveryを重ねない。
現時点はコード読取のみ。新FEM/unit/full/seed/GUI、外部資料参照・新依存は全て追加していない。
P09と原互換要件を含む全123カードgoalを維持する。
