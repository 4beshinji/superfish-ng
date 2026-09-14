# TE円筒チューニングの限定受入

2026-09-15 JST：[TE一般profile調整](TE_PROFILE_TUNING.md)をnormalized_profileへ接続。
非円筒の連動寸法・局所半径式、閉PEC/半領域/鏡映、保存再開と最終粗細判定を検証。
新2件51.729秒＋関連48件94.247秒PASS。専用尺度8FEM、Chrome11項目/4FEMがPASS。
5組native全配列/RF一致、元81ファイル保持。曲線TE・他物理調整とD03は残り、全goal ACTIVE。


2026-09-15 JST、開始HEAD `c92ba87`。D02の他物理調整のうち、既存のTE円筒追跡を
実FEMの寸法調整、保存再開、個別ID回復、CLI/worker/GUIへ接続する。
受入条件は独立Bessel周波数と場、RF・尺度則、交差時のID維持、粗細差の独立ゲート、
native保存の完全性、既存TMの保存互換と実GUI動作。D02全体の完了ではない。

## 対応範囲と契約

要求版1/2/3/7（7はprofile）の直線一定半径円筒、P1/P2、normalized_cylinderに対応。
閉PEC、同じ側の一対称面を持つ半領域、その鏡映結果を扱う。通常/鏡映の混在や端条件の変更は
既存追跡で拒否する。対称系の順位は元セクター内の周波数順であり全スペクトル順位ではない。
版6の回復要求でこれらを包める。版4/5/8のTE曲線、一般非円筒、組立、宣言変形のない明示メッシュは未対応。
各候補生成後にも円筒条件を検査するため、端点が円筒でも途中で非円筒になる式はFEM前に拒否する。

比較は既存の実Eφ電場と円筒正規化写像を使用する。固有値・場・RFのFEM核や許容差は変更しない。
TE native readerで係数と物理を保持し、TM場として解釈しない。両R/Q、加速電圧等はN/Aを維持する。
全Jobのファイルhash、完了状態、宣言Project一致、TE native完全性を再検証する。
TM側は以前の検証へ委譲しcheckpointのscopeも変更しない。汎用tracked Studyの対応範囲は広げない。
目標周波数差と最終粗細差を独立に判定し、ID未検証時は周波数を採用しない。

## 検証記録

証拠はignored `out/te-tuning-20260915/`。共有要約は
`benchmarks/tuning/te-tuning-20260915.json`。新たな外部資料・依存・旧実装資産は使用していない。
独立解析は既存test_te.referenceのBessel円筒式を再利用し、周波数・RF・場を分けて照合した。

- 関連52unit、113.689秒PASS：test_te_tuning、test_tuning、test_coupled_tuning、
  test_polynomial_tuning、test_expression_tuning、test_partition_tuning、test_gui_tuning、
  test_tuning_jobs、test_te_mode_tracking、TEJobTestsの未接続workflow拒否。
- 追加P1粗細ゲート拒否1unit、1.549秒PASS。粗いFEMの周波数を目標にしても、
  1Hzの粗細条件を満たさなければREFINEMENT_FAILEDになる。計53件は分割実行。
- 専用base/倍寸法/4倍エネルギー各4試行、計12実FEM。周波数最大相対誤差
  1.618324e-6、G 0.003715898、場成分0.002054499。既存許容差1e-4/.005/.01内。
  電気/磁気エネルギー等分、軸Eφ=0、加速量N/Aを確認。場尺度差最大4.4865e-14。
- 実交差を含む回復6実FEM。成功4試行のうち3回復、対象順位4→3でもID維持。
  回復失敗側2試行はUNVERIFIED・周波数未採用。先行保存を保持して再開。
- CLI再開1実FEM。Chrome閉PEC9項目/4FEM、鏡映式入力11項目/4FEM、旧TM9項目/17FEM。
  全PASS、外部通信0、製品335ファイルSHA固定。画面のTE/N/A/元セクター表示を目視確認。
- direct/CLI/GUI/importの8組で全保存配列と全RFが完全一致。元114ファイル保持。
  鏡映4試行は全領域の軸方向p=2 Bessel場と照合し、最大成分誤差0.001506346。
- 前回partition tuningのTM checkpoint完全再生（新FEMなし）。全9GUI Job complete、
  専用サーバーSIGINTで終了0。全検証終了。専用FEM合計44、unit内部の実行は別。

初期の新4テストもPASS。許容差の緩和なし。限定adapter変更につき全suite/seedは再実行せず、
直近milestoneの証拠を置き換えない。hosted CIの実行は観測していない。
一般TE形状・曲線の追跡/調整、他物理調整、D03一般制約付き探索は残る。
