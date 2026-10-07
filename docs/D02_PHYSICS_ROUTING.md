# D02の物理別接続と未完事項

2026-10-07 D02原カード **DONE**：[直線TM調整の条件別監査](STRAIGHT_TM_TUNING_ACCEPTANCE.md)。D01法則からの試行/追跡/独立細分/保存再開、独立円筒f/H/E/壁loss/両R/Q、実段差の元境界/体積/個別ID、無効中間形状の求解前停止、API/CLI/実Chromeの元要求/最終場/両R/Q一致を原6条件群で照合。52個別unit＋実Chrome7項目を源/元logへ再結合し、監査内の新FEM/unit/full/seed/legacy0。一般折返し輪郭は正しい未達停止/完全再生を受入し、追加二系列の差71.166/31.378 kHzをTUNEDへ変更しない。初稿監査の「折返し輪郭成功」は原カードを超える追加条件だったため、原文との照合記録を残し、原条件へ戻した。全1275源固定・全handle/server/browser終端、slot 0。原123はD02だけDONEへ変更、66 DONE/2 IN_PROGRESS（H17/C07-planar）/55 PLANNED。親D02/P01/全goal/原互換32要件は継続、次はD03（TE階段/一般輪郭）。rawは out/d02-whole-acceptance-20261007/acceptance.json。

2026-10-07 D01仕様 **DONE**：[非曲線TM/TEの形状・区分写像・対称/最終細分](NONCURVED_TUNING_SCOPE.md)。profile/階段/単一一般輪郭の六正常/拒否要求と元追跡先を固定。現行profile正常2、未対応4、不正6、将来六領域の両bounds/面積・体積尺度と不正拒否、未実装版9拒否、TE異セクター事前拒否をmetadataだけで確認。136式は既存SI parserに適合し、初稿leaf拒否/runner引数順ERRORを保全して修正。製品/テスト/script1179源不変、新FEM/unit/seed/full/legacy0。現在の区分TM追跡と不足するTM調整/TE直線区分追跡を分離し、既存曲線TEを再実装へ戻さない。原123台帳はD01状態だけ変更、65 DONE/2 IN_PROGRESS/56 PLANNED。D02/D03実装・親D02/P01/全goal/原互換32要件は継続、次はD02。

現行のD01仕様は上記リンク。以下の2026-09-15表は当時の履歴で、平面P01〜P09とHφ H10/H13/H15/H16の限定受入は[現行入口](development-plan/CURRENT.md)を参照。全物理の親受入は別に維持する。

2026-09-15 JST。元`COMPATIBILITY_PLAN.md`のD02.S/I/Vと、BACKLOG P2-02の
「他物理の調整」を現在の専用入力・ソルバー・追跡の入口へ対応付けた。
過去の曲線TE追加ごとの未完記述を、全物理の完成判定として使わない。
D02は引き続き未受入。全計画の受入範囲を今回の機能へ縮小していない。

| 物理/幾何 | 現在の経路 | 残件 |
|---|---|---|
| 軸接続真空m=0 TM | tuning.py、式版7、分割版8、保存/CLI/worker/GUI | 非曲線の一般輪郭/階段を含む要求との最終照合 |
| 軸接続真空m=0 TE | te_tuning.py、profile・native P2曲線・最大1対称面/鏡映、Study/調整/保存/GUI | 直線階段の専用写像/接続、親要件との最終照合。TE自動計画生成はe4fb07dで接続済み |
| 平面cutoff TE/TM（P02） | PlanarProject・planar_tracking.py。今回[専用調整API/CLI](PLANAR_TUNING.md)を追加 | [worker](PLANAR_TUNING_WORKERS.md)と[GUI](GUI_PLANAR_TUNING.md)は接続済み。既存多角形アフィン比較と形状法則の接続、個別ID回復と全体受入 |
| 内導体/材料Hphi（P03/P04） | 真空一様尺度の調整/API/保存/worker/GUIは接続済み。[版2](HPHI_SHAPE_TUNING.md)で真空直線の同軸寸法/頂点変位・調整/所有保存/CLIを追加。[操作受入](HPHI_SHAPE_TUNING_GUI.md)で新写像worker/GUI・再起動後復元も確認 | 個別ID回復、曲線/材料の追跡・調整と親要件照合 |
| 静電/静磁場（S系） | 専用源問題のStudy/後処理 | cutoff周波数という目標は定義されない。静的設計探索を周波数tuneの成功として数えず、必要な目的量/制約は別仕様で扱う |

D02の共通受入は、変数・範囲・目標・停止条件、追跡付き実FEM、無効形状と失敗履歴、
寸法–周波数の独立検証、ID切替拒否、最終形状の細分、目標許容差と粗細差の分離である。
保存解/単独追跡があるだけでは、この調整workflowの完了証拠にはならない。

D03は別親課題。RF制約付き探索の要求版1〜3が存在するが、一般形状・追加物理・
初期/最終の独立細分と制約未収束時の判定を元要件へ照合してから受け入れる。
既存の限定例を全体完了へ読み替えない。

2026-09-21追補：H09の非一様直線Hφ調整worker/GUIを受入済み。次はH10の個別ID回復。
C00の旧版/付属文書の確認不能は別件として保持し、この実装可能な経路を止める理由にしない。
