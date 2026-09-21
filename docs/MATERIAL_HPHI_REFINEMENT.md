# 材料領域を保持する直線細分

2026-09-22。H16-aの細分基盤を実装。形状則、試行生成、調整runnerへの接続は残る。

`refine_material_hphi_partition(partition, ...)`は各三角形を4分割し、子セルに元の領域ID・材料ID・係数を継承する。元全PEC輪郭、穴、軸型を保持する。完全なsame_domain材料比較で全領域と界面の被覆を再検証してから返す。丸めで元境界/界面の厳密な対応が失われた場合に、許容差で吸収した成功を返さない。

返り値は`MaterialHphiRefinement`で、専用partition、各子セルの`parent_cells`、P1/P2 scalar係数の`prolongation`、規模診断を持つ。移送行列は参照三角形の4分割と基底値から構成し、共有DOFの行が一致することと全DOFの被覆を確認する。軸DOFと静的定数qを保持する。新周波数・規格化・RFは付与せず、調整では生成したCaseを改めてFEM solveする必要がある。

要素数と自由度予算は細分配列/材料行列を作る前に検査し、元領域/界面比較にも独立の予算を渡す。元partitionを複製し、親セル配列と疎移送行列の内部配列は読み取り専用にする。

## 検査と来歴

`out/h16-material-refinement-20260922/`。`before.log`でAPI未実装のred。`initial.log`は検査側のtuple添字をNumPyの多次元添字として扱った失敗で、セル番号listへ修正した。

`final.log`は新`test_material_hphi_refinement`2件＋直接利用先`test_material_hphi_fem`3件、3.214秒PASS。後から全領域/界面被覆の検証を追加したため、新2件を`coverage.log`で再検査し、3.027秒PASS。全handle終了0。

新検査はP1/P2・正半径/軸・二つの穴で、材料領域継承、領域別回転体体積、界面辺2分割、`Pᵀ K_f P=K`と`Pᵀ M_f P=M`、独立多項式再現と定数保持、元入力不変を確認する。予算/次数不正は材料行列組立前に拒否する。関連の材料弱形式は独立区分場/境界traction、領域順序、一様epsilon/mu則と静的核を検査する。

既存自作直線4分割とP1/P2基底を再利用し、専用材料所有と参照セル移送を追加した。新規外部資料・依存・legacy参照なし。FEM弱形式/seed TMを変更せず、対象不変量と直接利用先を検査した。全suite、調整完了、GUI受入を主張しない。
