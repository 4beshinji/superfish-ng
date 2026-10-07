# 元直線TE場の区分写像追跡

2026-10-07更新：版9のTE接続とD03原カードは [STRAIGHT_TE_TUNING_ACCEPTANCE.md](STRAIGHT_TE_TUNING_ACCEPTANCE.md) で受入。以下の「TE版9拒否/未接続」は各段階の履歴。親P01/D02/全goalは継続。

2026-10-07、D03追跡コア限定受入。版9調整とD03全条件は未完。

## 物理と宣言

対象は既存の真空m=0 TE直線profile、段差、単一輪郭の元FEM Eφ。
piecewise_remeshの比較meshはschema1、元各Caseの全領域と全境界を覆い、
両側の頂点番号・向き付き接続・tagsが一致する。native solver meshとは独立。

TE専用adapterは元Eφにsqrt(r/max(r))*sqrt(detJ/max(detJ))を側別に掛け、
共通三角形求積で比較する。側別定数は列規格化で消えるが、
非一様r・Jacobian因子を保持し、回転体積2πr dr dzも報告する。
TM Hφの読取名や本質境界をTEへ流用しない。

sample前に同polarization、同元端条件/セクター、同鏡映有無、
直線幾何、全比較領域のCase被覆と実native全境界を検証する。
TEは対称面一つまで、鏡映は一つの元面を必須とする。
保存trackingはCaseを含む元TE-nativeを読取/全再生し、未知キー/型/境界を拒否する。

## 元鏡映場

宣言meshは元半領域。既存TE反射と同じ平面/shift・正向き三角形で両ローブを構築し、
full Caseと全native境界へ再検証する。全域の元Eφを実際にsampleする。
電気対称でEφ/Hzは奇、Hrは偶、磁気対称でEφ/Hzは偶、Hrは奇。
元振幅を変えず、全Uと全PEC壁lossは半領域の2倍、fは同じである。
ID/順位は元セクター内の順序で、全物理スペクトル順位ではない。

sample上限262144は鏡映の二ローブを含め、mesh構築前に確認する。
宣言source hashと導出evaluation mesh hashを別に保存する。
対応成立はFEM/求積/連続分枝の収束保証ではない。集合対応から個別IDを推測しない。

## 独立検査と来歴

独立Eφ=rの非一様体積積分を先に計算し、旧経路のHphi_A_per_m
KeyErrorをbaseline.log終了1で再現した（FEM0の補間・積分検査）。
専用経路のinvariant.logは終了0。元科学核・TE FEM/RFは変更していない。

新7件0.916秒、追加反射証拠3件0.277秒は2成功/1検査ERROR。
低overlapでmatchesが空になる正しいUNVERIFIEDに対し、
検査がmatches[0]を参照してERRORとなった。原log/検査源を保全後、
overlap_matrixの元値へassertを修正し、不足1件だけ再検査して終了0。
新10個別＋直接消費29件39.571秒の計39個別成功。
保存/history/CLI、旧TM区分、TE profile、曲線TE/旧鏡映chart経路を確認した。

実段差と異なるsolver分割、実折返し輪郭、全鏡映nativeの保存/再生、
全元byte保持、両端・二偶奇・P1/P2を検査した。
同じ分割の一様尺度1.25で元Eφ/Hr/Hzの誤差は最大4.637e-15、
f逆尺度/G不変/Q平方根、1 J半領域と両R/Q N/Aを別確認。
二番目のローブを意図的に変えた補間検査は、実元sampleで対応をUNVERIFIEDにする。
その変えた配列を固有場と呼ばず、nativeとして保存しない。

raw: out/d03-te-straight-tracking-20261007/acceptance.json。
1184 Python源を固定、成功済み元7検査とhelperのAST/源不変。
旧製品変更はpiecewise入口dispatchとsavedのformal controls/TE能力guardの3関数。
formal validatorのallow_straight_symmetryは内部呼出keywordで、
実TM trackerは引き続き対称tagsを拒否する。ユーザーcontrolsの未知キーは拒否する。
新full/seed/legacy0。全handle終端、新依存/外部資料/GPU/hosted CIなし。

残件は版9の元形状法則をTE tuningへ接続すること、独立Bessel円筒と
実最終細分/対称偶奇/保存再開/未確認停止・操作を検査すること、D03全原条件監査。
TM版9と既存曲線TEの受入は保持する。
