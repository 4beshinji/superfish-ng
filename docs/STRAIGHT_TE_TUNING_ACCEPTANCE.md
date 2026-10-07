# D03直線TE調整の原条件監査

2026-10-07、原実装カードD03をDONEとする。
親P01/D02、D04最終監査、全goalと原互換32要件は未完。

原文は [04-design.mdのD03](development-plan/04-design.md#d03)、
全形状/元法則は [D01](NONCURVED_TUNING_SCOPE.md)。
既存曲線TEを再実装へ戻さず、元直線比較/版9法則をTE固有の場・境界へ接続した。

## 原条件と独立証拠

| 原条件群 | 確認内容 | 判定 |
|---|---|---|
| 元D01法則からTE試行/追跡 | 完全Case boundary owner/SI式/全座標同時更新、profile/step/contour、各実Case被覆と元Eφ体積重み。固定RF・両R/Q N/A、版6回復wrapper | PASS |
| 円筒TE解析周波数/場 | 独立J1零点とsin/cos軸関数でf/Eφ/Hr/Hz、全PEC壁lossを別検査。閉PEC/電気対称/両側磁気対称、1 J・実細分で各誤差減少 | PASS |
| 段差の独立細分 | 実元Case/全境界/体積/個別ID、同候補の独立細FEMと二つの周波数gate。磁気対称通常/鏡映は元10 kHz条件内8,973.866 Hz | PASS |
| 直接PEC/半領域/鏡映・対称偶奇 | 元両端・電気/磁気・P1/P2。Eφ/Hzの電気奇・磁気偶、Hrの逆偶奇。元鏡映両ローブを実sample、U/lossの倍化と元セクター順位 | PASS |
| 未確認停止/保存再開 | 実曖昧IDはfrequency null、細分なし、UNVERIFIEDで停止。無効中間形状を次FEM前に拒否。旧全byte保持、PAUSEDから新規出力再開と完全再生 | PASS |
| TM境界を流用しない | 元TE-nativeとTEFieldSampler/TEマトリクスを使用。元半比較meshを元面に従い全域へ導出。混在polarization/端/鏡映、mixed端をsample前に拒否 | PASS |

元場一様尺度1.25のf逆尺度/Eφ・Hr・Hzの-3/2乗、G不変/Q平方根、
独立非一様体積内積と元面積/体積の二乗/三乗則を別に確認した。
任意の非線形式の区間全体の有効性や連続分枝は保証しない。

## 規約と解析修正

TE peak Eφ=A J1(χr/R) a(z)、χはJ1の第一零点。
全U=ε0/2∫E²dV、Ue=ε0/4∫E²dVを使う。
閉PEC/一つの端対称で∫a²dz=L/2なので
A²=4U/(ε0 πR²L J2(χ)²)。
Hr quadrature=−A J1 a′/(ωμ0)、Hz quadrature=Aχ J0 a/(Rωμ0)。
各場・壁lossの解析は検査専用で、FEM solveを置き換えない。

初回解析振幅を誤ってA²=2U/(...)としたため、全四円筒subcaseの
場誤差約0.414でFAIL。元ログと検査源を保全し、
既存 [TE規約](AXISYMMETRIC_TE.md) のε0/4へ照合して解析式を修正した。
製品FEM/1 J/全閾値は不変。修正後の円筒1検査（四subcase）は15.652秒/終了0。

## 入口と実GUI

元要求を独立API、実CLI、実Chromeのworker開始/PAUSED/再開へ通した。
要求/decisionと元最終Eφ/Hr/Hz、f/U/Ue/Um/Pwall/Q/Gは相対差0
（確認閾値1e-10）、両R/Qと加速量はnull/N/Aを保持する。
最終表示importのfields/case/results/modes/axis/VTKの元6科学ファイルもbyte一致。

GUIの元要求完全復元・再構築、重複キー求解前拒否、保存/改竄拒否、
両gateと個別順位の元場、TE明示は初回8項目成功。
RF表を行構造と仮定した最後のselector検査だけERRORとなった。
既存表は列構造なので、その検査を修正し、保存済みTUNEDから
--rf-checkpointで不足1項目だけ確認した。新eig求解0。
合計9項目の分割受入で、初回レポート全体をPASSへ改記しない。
両R/Q N/Aの物理理由を示す元RF表の画像も確認した。

scripts/verify_gui_straight_tuning.mjsは既存browser-session管理を使用。
通常 --url/--out/--request、任意 --checkpoint でPAUSED再利用、
--rf-checkpoint は保存済み最終結果の不足RF表示だけを確認する。
外部要求0、全browser/server終端、slot 0。

## 数値未達と範囲

閉PEC/電気対称段差は粗細差25,043.061 Hzで元10 kHz条件未達。
粗いz折返しTE輪郭は差1,348,165.402 Hzで未達。
ともにREFINEMENT_FAILEDと完全保存再生を保持し、TUNEDへ変更しない。
磁気対称の通常/鏡映段差の成功を全境界条件や全輪郭の数値成功へ拡大しない。
二FEM差は連続誤差上界、RF三水準収束、角の物理ピーク精度の保証ではない。

## 検査・源・来歴

追跡コアba1c0b1の新10＋直接消費29を受入済み。
調整接続の新metadata5＋新実物理5＋直接消費25は分割35個別成功。
合わせて74個別unitを元ID/log/源hashへ結合した。
TE旧profile/円筒、TM版9、jobs/gui transport、回復wrapperと保存/history/旧曲線を含む。
成功済み検査を文書のために再実行しない。新full/seed/legacy0。

metadata fixtureがcontourへ禁止されたboundariesを付けたERRORは、
元log/源を保存後、edge_tagsへ統一して不足一ケースだけ再検査した。
新mixed端のsample前拒否は独立反例で先にFAILを再現してから実装。
元TMmetadataの「TE版9未対応」negativeは、この対応拡張に従い取り除き、
残る明示mesh/zero-change拒否を保持して六metadataを再検査した。

監査ID生成がmethod名を二重付加していたため、生成前記録を保全して
canonicalな74 IDを現行test class/method ASTへ照合した。
D03追跡39とD02コア52の過去receiptも元hash束縛を維持し、
別canonical-test-ids.jsonに該当commitのASTと訂正IDを保存した。
件数/log/数値は不変、訂正内の新検査/求解0。

全1279源固定（Python1186＋web/script）、既存科学マトリクス/RF積分/閾値不変。
受入済み追跡kernelの差はmixed端の追加拒否だけで、元正常3タグの全計算ASTは同一。
元10追跡検査の源もbyte不変。既存製品変更はpiecewise/savedのTE入口、
straight法則guard/controls、TE版9能力guard、GUI説明だけ。
新依存/外部資料/GPU/hosted CIは使用していない。

raw：
- out/d03-te-straight-tracking-20261007/acceptance.json
- out/d03-te-straight-tuning-20261007/：各metadata/物理/直接消費logとobserved-handles.json
- out/d03-te-straight-interfaces-20261007/acceptance.json / api-cli-receipt.json
- out/d03-whole-acceptance-20261007/acceptance.json / conditions.json

全123カードのD03だけDONEへ変更（67 DONE/2 IN_PROGRESS/54 PLANNED）。
次は依存成立のD06。D04はH18/P10/C07-TEを待ち、親P01/D02と全goalは未完。
