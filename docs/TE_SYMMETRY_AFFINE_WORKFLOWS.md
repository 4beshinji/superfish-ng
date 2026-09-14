# TE対称曲線のアフィン調整・Study

2026-09-15 JST、開始HEAD `693f987`。D02のTE対称曲線について、既存の
[比較基盤](TE_CURVED_SYMMETRY_TRACKING.md)をアフィン調整版4とStudy版2へ接続する。
受入条件は元対称セクターの保持、直接/鏡映の実FEM、保存再開・改変検査、
実Eφによる追跡と最終細分、独立したMaxwell周波数・係数・RF尺度則である。

`validate_te_affine_sector`で両入口の条件を共有する。native P2・非組立・固定RFで、
高々一つの対称端を扱う。鏡映指定には元対称面が必要である。
軸方向せん断は多項式の全係数がゼロでなければ拒否する。
採用端点でゼロになるだけの式は、中間値・適応挿入点の対称面を保証しないため受理しない。
実変換でも既存の対称面と二次境界・履歴を検査し、元セクター内の周波数順位を保持する。

非アフィン曲線調整版5/7/8の直接閉PEC条件は維持する。
直接閉PECのアフィンせん断は従来どおり扱う。FEM組立、固有値解法、RF規約は変更しない。
TEの加速量と両R/QはN/Aであり、アフィン変形時に加速区間を作らない。

## 検証方法

記録は`out/te-symmetry-affine-workflows-20260915/`。
新`test_te_symmetry_affine_workflows`は実装前に旧ガードの拒否を再現した。
Studyはz_min/z_max、電気/磁気対称、直接/鏡映の8組を原寸/倍寸で実計算する。
全係数と周波数、U/G/Q0/壁損失を別々に1e-10で検査し、完了Studyの追跡と保存再生を確認する。
調整は直接/鏡映で最初の試行後に停止・再開し、最終細分と元試行hash保持を確認する。
端点でゼロになる非ゼロせん断多項式の拒否も検査する。

調整の目標は元の実FEM周波数。1 Hzの目標差条件と1 MHzの粗細差条件を持つ要求では、
細分解が目標を外れる場合にREFINEMENT_FAILEDとなることを検査する。
別の操作要求では両条件を1 MHzとし、TUNED経路を検査する。厳しい要求の停止を成功へ読み替えない。
1 MHzを解析精度保証として扱わない。
前段の対称全領域FEMとの照合・鏡映エネルギー則は変更していないため再利用する。

専用native検証は鏡映磁気対称の逐次/適応Studyをそれぞれ停止・再開し、
保存再生、全係数・周波数・RF尺度則と元ファイルのhash保持を検査する。
以下の独立Study実GUIを追加検証した。調整/逐次/適応の実GUI・CLI専用経路は後続であり、API/native証拠から受入済みとは主張しない。
新しい外部資料や旧ソルバーのコード・バイナリは使用していない。

## 診断と証拠の範囲

初回の新3件158.464秒はStudy/せん断拒否が成功し、調整のTUNED期待が失敗した。
初期細分を1段から2段に増やした調整1件80.068秒も同じ期待で失敗した。
最初は粗細差の不足と考えたが、最終判定の実装を確認すると、目標差と粗細差は別ゲートだった。
元の粗いFEM周波数への1 Hz要求が細分解でも満たされるという検証の前提が誤っていた。
その要求は削除せず、目標ゲートfalse/粗細ゲートtrueの停止検査として残した。
製品の許容差・停止判定は変更していない。

関連は`test_te_affine_study test_curved_affine_study test_te_jobs test_te_curved_symmetry_tracking`
の20件232.009秒PASS。非アフィンの直接利用先は`test_te_partition_tuning`の
`test_te_contract_rejects_accelerating_coordinates_and_reflection`と`test_te_curved_tuning`の
`test_expression_and_study_geometry_preserve_te_and_reject_acceleration_coordinates`が2件55.707秒PASS。

専用の逐次2点と適応3点がCOMPLETE・保存再生PASS。成功系列は半領域5実FEM、
65 nativeファイル保持、Maxwell全係数/周波数/RF尺度差最大3.255e-15。
最初の適応2点は1比較で既に完了し、再開不可を正しく拒否した。
3点の別要求でPAUSEDからの再開を検査し、完了済み2点の診断出力も保持した。
診断を含め専用7実FEMで、unit内の計算は別である。
full/seed validatorとhosted CIは今回実行していない。

最終の調整2テストは688.332秒PASS。直接/鏡映の両方で、1 Hz目標は
refined_target_met=false、mesh_difference_met=trueとして停止し、別の1 MHz要求は両方trueでTUNED。
新4テストは分割証拠で成功し、単一全件PASSとは表記しない。
[集約記録](../benchmarks/tuning/te-symmetry-affine-workflows-20260915.json)を保存した。
全実行handle終端。次は調整/逐次/適応の実GUI・CLI、その後非アフィン対称接続・D02/D03の残件を進める。

## 独立Studyの実GUI

APIの実行要求から`gui-study.json`を作り、既存Chrome検証器で実計算を確認した。
検証器に以前の履歴2/3段と変数名の固定条件があり、入力の履歴・モデル・変数名から
検査条件を導くよう変更した。読込前の既定モデルも安全に待機する。
先行2回はFEM前の検証器エラーであり、失敗ログを保持した。

`browser-ready`は12項目PASS。独立Study2 FEM、完了追跡・保存再生・逐次/適応要求の準備、
元対称セクターの順位とTEのN/A表記を確認した。実行中の製品336ファイルhashは不変、外部HTTPは0。
GUIと逐次APIの原寸/倍寸2組で、全NPZ16配列と全RF値が完全一致し、元57ファイルを保持した。
対称条件はz_max磁気対称・鏡映の専用例であり、GUIの全対称条件受入とは主張しない。

計算終了後、TE対応説明を更新した。せん断の全係数ゼロを要求する対称アフィン経路と、
未対応の非アフィン対称経路を明示する。新旧入力の`--layout-only`は各3項目PASS、追加FEM0。
これらは説明変更後の別hash記録であり、実計算のhash記録と混ぜない。
結果と更新後画面を目視した。独立Study Jobと両点はcomplete、専用サーバーPID 2515293へSIGINT、終了0を回収した。
本工程の専用FEMはAPI成功5＋診断2＋GUI2の9回。全handle終端。
