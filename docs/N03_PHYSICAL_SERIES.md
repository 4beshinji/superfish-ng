# N03：五つの合成形状の物理系列と独立参照

2026-10-08 JST：N03 **DONE**。五合成系列の元場/RF・両側二区間と失敗保全を受入。修正環境の全validate handle64569は2485検査/499モジュール、4772.019秒・終了0/PASS。0FAIL/0ERROR、skipは3件で未実行物理へ数えない。全1405対象源は開始/終端/監査時一致。seed9モードの周波数・RF207量を元相対1e-10で別照合し、最大相対差f=0/RF=8.88178e-16。既知の入力domain/scope注記だけを厳密に確認し、元Case/mesh/両PEC端・旧規約は不変。元1199源は明示した変更前三源archiveで解決し、全523bound入力を再hash。初回HTTP環境FAIL/244モジュールの終了130と元長楕円体R/Q FAILは保全。原123は73 DONE/3 IN_PROGRESS（H17/C07-planar/N06）/47 PLANNED。N04/親G03・原互換32要件・全goalは継続。詳細は[N03の条件別受入](N03_ACCEPTANCE.md)。

以下は日付付きの実行履歴。

2026-10-07。五系列の専用数値判定と終端後の元条件監査はPASS。
N03は節目の全検証が完了するまでIN_PROGRESS、親G03・互換32要件・全goalは継続。
すべてN01で固定した合成真空・閉PEC・軸接続m=0 TMであり、測定施設の構造ではない。

## 終端した条件

| 固定形状 | nativeの幾何3×FEM3 | 独立場/RF・参照二変化 | 独立比較の秒数 |
| --- | --- | --- | ---: |
| 球 | 元0/1/2 PASS | PASS、別に解析TM根・場・RFも確認 | 44.191 |
| 楕円 | 元0/1/2 PASS | 実領域polar fanでPASS | 631.688 |
| 長楕円体 | 元0/1/2 FAILを保存、追加2/3/4 PASS | 最終FEM4でPASS | 965.603（全処理1017.615） |
| 接線連続丸め二ローブ | 元0/1/2 PASS | PASS | 195.393 |
| 鋭角二ローブ対照 | 非ピーク条件PASS、SINGULAR_GEOMETRY | 非ピーク条件PASS、SINGULAR_GEOMETRY | 244.794 |

滑らかな各例で三つの固定P2幾何すべての連続FEM二区間、最細FEMでの幾何二区間を確認。
周波数1e-4、R/Q・G 0.5%、ピーク比1%を維持し、場・実個別ID・面積/回転体積・
同一二次境界・親子Ritz・求積・離散peak上下界は別ゲートで確認した。
鋭角では有限ピークを受入量に含めない。三IDは元Hφから追跡し、周波数順位で再付番しない。
追加長楕円体の元水準0/1からのID来歴と元R/Q失敗は別報告に保持する。

独立参照は隔離uv環境のMIT cavsim2d commit
`48741ff46ca44463281a5ab5945328615881b502`、SHA固定79ファイルと
NGSolve/Netgen 6.2.2606を使用した。製品依存やsolve時の通信は追加しない。
参照の全五モードを保存し、純TMの実電気エネルギーsectorとHφの対応で三IDを選ぶ。
最細三水準h=0.005/0.0025/0.00125 mの連続二区間を比較し、最終nativeと参照の
全領域E/Hφ・物理軸Ez・両R/Q規約・f/G/peak比をそれぞれ確認した。
位相はHφから一つの符号を定めてEにも適用し、振幅をフィットしない。
両R/Qは全採用行でaccelerator=2×circuitを確認した。

長楕円体の最終native/参照の相対差はf=2.441e-8、両R/Q=2.033e-5、
G=1.432e-4、Epk/Eacc=3.803e-5、Bpk/Eacc=7.257e-5。
粗い参照球のG等のFAIL、領域外lookup、未分割fan体積、参照root誤記、
元長楕円体nativeの未収束と費用はすべて元rawに残す。

## 実行・来歴・限界

raw rootは `out/n03-native-surface-series-20261007/`。
元45nativeは2995.296秒、追加六nativeは460.209秒。
版3の保存45点行列は1025.114秒、版4の保存九点＋ID来歴二点は1034.638秒。
後二つは新FEM0。独立参照の元15＋追加10求解は別環境/別成果物に保存した。
五系列は既存専用 `scripts/validate_geometry_surface_convergence.py --matrix-request`
のstrict保存行列契約を使用し、rawの独立比較器は別環境の保存場だけを読む。

`completed-physical-series-acceptance.json` は、完成した各 `report.json` の全必須ゲート、
元FAIL保全、全三ID、両R/Q、参照二区間を照合し、1199製品源と全bound入力/参照byteを
終端後に再hashした。監査は新FEM/場標本0、元報告を独立参照として生成し直さない。
元製品源の一部を変更する統合前に実行し、結果はその1199源に結び付く。

版4は別ツリーで新7＋直接3の10個別unitを分割受入し、実行源1200を固定した。
全主数値ジョブ終端後、三変更源＋新testを同一byteで統合し、残る1196源も同一を確認。
`appended-main-integration.json` に全before/after SHAとtemp commit `81bce60` を保存する。
変更前三源は `before-appended-main-integration/` に保存し、元検査の1199源を明示解決する。
同一byteの統合のためunit/FEMを重複実行しない。節目の全validateを実行したところ、
初回のHTTP一件がsandboxのsocket禁止でPermissionErrorとなった。
同じソースの同じHTTP一件はlocalhost可の環境で2.792秒・終了0/PASS。
初回handle72074は244/499モジュール完了時にrunnerへSIGINTを送り、既存finallyで
全module worker/孫を後始末し、1919.016秒・終了130・全1405源不変で保全した。
初回をfull受入とは呼ばない。数値ソース/閾値は変更せず、正しいlocalhost環境で
全validate handle64569を新 `out/validation-n03-milestone-localhost-20261007` へ再実行中。
初回と再実行の開始snapshot1405は一致する。失敗を修正するための再実行であり、
件数や完成文言だけを更新するための重複実行ではない。

場比較は実P2/参照曲線境界の全fanと正のJacobian・独立体積を確認し、
密度比の平方根で固定円筒成分の単位的L2測度を合わせる。Maxwell変形則ではない。
Gauss16/24の全点を保持し、領域縮小や失敗点削除をしない。
実領域の確認・候補検索の公開APIと元条件は [追加水準の仕様](N03_APPENDED_FEM_WINDOW.md) に記録した。
有限求積診断と参照solverのpeak推定による経験的受入であり、連続PDEの一般誤差上界や
厳密な連続最大値の証明ではない。physical_error_bound/physical_peak_error_boundはnullを維持する。
