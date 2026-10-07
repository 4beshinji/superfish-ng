# P09 曲線比較・追跡・調整の条件別監査

2026-10-07、原カード[P09](development-plan/03-planar.md#p09)の元14条件と共有公開修正を全条件受入。
先行P04/P08はDONE。本書の表は既に受入済みの限定検査を統合するもので、
新しい全件実行数へ加算しない。修正後の節目全validateは実終了0/PASS、P09はDONE。
全123カードと原互換課題の完走はこのカード単独の完了と区別する。

## 元条件と証拠

| 原条件・影響する挙動 | 独立対照と受入証拠 | 状態 |
|---|---|---|
| 同一二次領域・宣言写像の完全比較 | [幾何分割](PLANAR_CURVED_COMPARISON.md)の全六節点/外周/独立native被覆、有理参照分割の欠落・重複拒否。独立二次patchの面積/多項式moments、vertexだけ一致する反例。新7＋関連12の分割19件 | PASS |
| 元電場・磁場を別々に比較 | [E/H Gram](PLANAR_CURVED_FIELD_COMPARISON.md)の両側実面積/自己・交差内積、独立積分、相似・位相・改変拒否。新8＋関連10の分割18件。場の片側だけでIDを受入しない | PASS |
| 固定二次境界の細分・有限guard | [有限スペクトル](PLANAR_CURVED_SPECTRAL_RESOLUTION.md)の参照セル四分割・全PEC・scalar transfer、独立dense有限固有値区間と尺度/回転。新4＋関連6の10件。解析曲線へ再投影しない | PASS |
| 個別ID・順位交換・曖昧停止 | [追跡核](PLANAR_CURVED_TRACKING.md)の実TE楕円反射parity/順位交換、真doublet/null、上位guard越境・全E/H不一致。新8＋関連14の分割22件。順位をIDへ置き換えない | PASS |
| 実過去anchorによる個別回復 | [回復核](PLANAR_CURVED_IDENTITY_RECOVERY.md)の完全比較/既存ID集合一致と未確認null、新4＋関連6の10件。[所有履歴](PLANAR_CURVED_TRACKING_HISTORY.md)で実解決済みsnapshotへ束縛、後続継承・誤anchor/断絶拒否 | PASS |
| 全試行を元Projectから生成 | [形状法則](PLANAR_CURVED_SHAPE_LAW.md)のproper affine多項式族/全区間det/全六節点/全PEC。独立非一様座標式・二尺度TE/TM場/RF、新4＋関連4の8件。[試行生成](PLANAR_CURVED_TUNING_TRIALS.md)の全細分chart/固定外周/累積予算、新4＋関連11の15件 | PASS |
| 円の尺度調整・両周波数gate | [実調整](PLANAR_CURVED_TUNING.md)の円TM、検索256→最終1024セル、独立Bessel目標と事前宣言した絶対f基準、目標差/粗細差を別評価。[調整worker](PLANAR_CURVED_TUNING_JOBS.md)で実最終求解も受入 | PASS |
| 非円形合成調整・最終回復・両gate | [実調整](PLANAR_CURVED_TUNING.md)の非一様TE楕円/回転、同有限作用素の独立dense参照、反射parity・実順位2→1、検索/最終の過去anchor0回復。[大容量GUI](PLANAR_CURVED_GUI_LARGE_CHECKPOINT.md)で全三trial/両gateと実順位2の元場を確認 | PASS |
| 最終二次境界不変・全場保存 | [試行生成](PLANAR_CURVED_TUNING_TRIALS.md)の全階層有理chart/全六節点式と固定PEC、独立境界多項式評価。[所有調整](PLANAR_CURVED_TUNING_SAVED.md)の元九byte/完全移動再生と全E/H・RF・判断保存。[大容量GUI](PLANAR_CURVED_GUI_LARGE_CHECKPOINT.md)の完全checkpoint/元五byte download | PASS |
| 比較・細分・回復予算不足は停止 | [比較](PLANAR_CURVED_COMPARISON.md)/[guard](PLANAR_CURVED_SPECTRAL_RESOLUTION.md)/[試行](PLANAR_CURVED_TUNING_TRIALS.md)の資源事前検査・累積点/全試行pair予算。[実調整](PLANAR_CURVED_TUNING.md)の全controls拒否、真doublet/guardでは周波数null、失敗prefix保全 | PASS |
| 所有再開・移動・改変拒否 | [調整保存](PLANAR_CURVED_TUNING_SAVED.md)の完全元native再生/新owner、再hashした係数の物理拒否。新7種類＋関連3を分割受入。[履歴](PLANAR_CURVED_TRACKING_HISTORY.md)は新13種類＋関連10、遅い祖先改変の検出漏れを再現して修正 | PASS |
| CLI/workerで実取消し・再開・再起動 | [二点](PLANAR_CURVED_TRACKING_JOBS.md)新6種類＋関連10、[履歴](PLANAR_CURVED_TRACKING_HISTORY_JOBS.md)新8種類＋関連5、[調整](PLANAR_CURVED_TUNING_JOBS.md)新8種類＋関連5。実running取消し−15/新worker0、管理器再起動、source生存中の移動、元creator/claim不変、失敗を成功にしない終了コード | PASS |
| GUI操作・元場/実ID・保存地点 | [専用GUI](PLANAR_CURVED_GUI.md)19 strict操作/新API8種類＋関連6種類、実Chrome調整/再開7＋render1。[履歴実操作](PLANAR_CURVED_GUI_HISTORY.md)は比較/回復/延長/取消し・真doublet/nullの分割14項目。[大容量](PLANAR_CURVED_GUI_LARGE_CHECKPOINT.md)は円5＋不足2/TE8の分割15項目 | PASS |
| 節目の全unittest・seed f/RF・固定源 | 元全validate終了1を保持。修正後は2359検査/479モジュール、3215.343秒、0FAIL・0ERROR・3skipで実終了0/PASS。全1366源は開始/終端/現行一致。seed9モード/207量を相対1e-10で別照合しf最大差0・RF最大差8.881784197001248e-16。skipの範囲は下記 | PASS |

## 数値と範囲

円TMの目標は4780938659.800418 Hz、実最終は4781070789.776281 Hz、
相対目標差は約2.764e-5。粗細差208643.6307630539 Hzは目標差とは別gate。
非円形TEの実最終は4230213276.3066583 Hz、独立dense参照は4230213276.305762 Hz、
粗細差30077.812368392944 Hz。dense参照は同有限作用素の独立解で、連続境界問題の参照ではない。
両gateを個別に不成立とする反例は保存済み実データのterminal判定で確認した。
それを異なる要求で新調整を実行した数へ加算しない。

対応は宣言した二つの有限snapshot間の元Cartesian E/H transport。
連続pathのidentity、連続固有値の誤差上界、surface peak精度を保証しない。
調整lawはproper affine族で、任意の非アフィン曲線変位lawへ暗黙に拡張しない。
真空・閉PEC断面のTE/TM、SI・peak phasor・単位長U′/RFを維持する。
遮断断面の加速器定義/回路定義R/Qは理由付きN/Aで、3D量へ正規化し直さない。
合成円/楕円/二次patchを測定構造として提示しない。

## 再現と来歴

各リンク先に限定検査の実コマンド・raw・失敗/補完・基準源を記録した。
元のFAIL/ERRORを保持し、成功を分割受入と一括PASSの別なく集計しない。
既に受入済みで変更のない数値源を、文書の更新だけのために再実行しない。
元全validateを節目で一度起動し、事前に全discoveryを重複させていない。
元全実行中に再現した共有保存競合を終端後に修正し、限定45＋実取消し/再開1PASS後に新全validateを起動した。
修正後全実行の開始から実終端までsrc/tests/scripts/examples全1366源を固定し、終端後の現行源とも一致した。

最終監査の条件mapは `out/p09-checkpoint-publication-20261007/completion-audit-plan.json`。
本表の元14行と追加の完全公開不変量を結び付け、13行の歴史的限定receipt、
開始時点の新全実行/seed f+RFの未確定、共有消費先の検査、skipの個別確認を分けて記録した。
最終結果は同rootの `p09-final-acceptance.json` / `p09-final-card-audit.log`（実終了0）。
元14行＋追加完全公開不変量を全受入し、16歴史的receipt/91 entryのhashと科学源の互換性を最終照合した。
この読取監査は新FEM/物理再生0であり、全goalの完了ではない。
このmap自体を新検査数やP09完了証拠へ加算しない。

P09の16受入記録が参照する91 evidence/log entryを改めてhash照合した。
`out/p09-planar-curved-large-gui-20261007/p09-evidence-inventory.json` は欠落0/不一致0、
`evidence-inventory-audit.log` は終了0。これは歴史的証拠ファイルの整合性検査で、
新しいFEM/物理再生/全件成功を証明する数へ加算しない。
また `historical-tuning-source-audit.json` は生成当時/現行の `_trial`/`_assess`/
`_reconstruct`/`validate_planar_curved_tune` がAST同一であることと、本書/大容量GUI文書の
全ローカルリンク先の存在を確認した。

大容量GUI監査は基準e395996の全420製品源不変、元7trial×九ファイル=63 entry、
完全科学保存と元native五byte/実download五byteを確認した。
生成時の曲線源15件は14現行不変＋1生成当時archive一致。古いmanifestを現行creatorへ置換しない。
新外部実装/依存/legacyソース再利用なし。大容量検証器のCDP設定だけは
[Chromiumの公式Network protocol定義](https://raw.githubusercontent.com/ChromeDevTools/devtools-protocol/master/pdl/domains/Network.pdl)
のAPI意味を参照した。旧ソルバー比較/実測/Hosted CI/科学GPUは今回未実施。
P09はDONE。全123カードと原互換32要件は維持し、後続はC07-planar→P10。

## 修正後の全検証・seed照合

全コマンドと限定45＋実取消し/移動/再開1検査は[公開修正記録](PLANAR_CHECKPOINT_PUBLICATION.md)に記載。
新全rootは `out/validation-p09-publication-20261007`。`validation.json` はfull PASS、
`test-run/report.json` は2359検査/479モジュール、失敗0/エラー0/skip3。
全コマンド終了0、実handle69844終端0を `new-full-terminal.json` へ保存し、数値源固定を解除した。
全unit内のGUI API/worker検査は実Chromeの再実行ではなく、実Chrome証拠は上表の歴史的限定検査である。

skipは次の3件。前2件は任意NGSolve環境不在で未実施、最後は専用受入native rootを要するため既定全実行では未実施。
専用円TM/回復付きTEの実取込・移動・完全再生は[所有調整](PLANAR_CURVED_TUNING_SAVED.md)で865.527秒PASS済み。
科学調整kernelは生成当時のarchiveとAST一致、今回の保存修正は共有消費先の全検証と限定実取消しで別確認した。
これらのskipを実行済み物理検査へ数えない。

- `test_independent_comparison.ReferencePhysicsTests.test_pillbox_frequency_rf_and_bessel_field`
- `test_independent_comparison.ReferencePhysicsTests.test_reference_rejects_unsupported_physics`
- `test_planar_curved_tuning_saved.PlanarCurvedOwnedTuningTests.test_actual_accepted_circle_and_recovered_ellipse_import_move_and_replay`

seedは旧benchmarks/validationとpillbox6＋合成shaped3の9モード、各23量=207量を別照合。
周波数/全RFの事前gateは相対1e-10で不変、複素電圧の実部/虚部には同じ全体実符号だけを許す。
最大相対差は周波数0、RF 8.881784197001248e-16。Case/mesh/両PEC端、1 J規格化、
全旧phasor/energy/電圧/VTK規約、加速器定義R/Q=2×回路定義R/Qを照合した。
pillbox絶対fの0.003基準とshaped自己細分は別の検証で、連続誤差上界やsurface peak精度を主張しない。

初回 `full-final-audit.log` のmetadata全体一致assertはAssertionErrorとなったまま保全した。
既存出力が追加したdomain注記（入力領域の積分・対称面損失なし・自動倍化なし）と、
明示対称部分領域も含むcapability scope文字列が旧metadataと異なるためである。
修正版 `audit-full-closed-domain-after-terminal.py` は既知の旧/新scope文字列と新domain値を厳密確認し、
全旧規約・実Case/mesh・閉PEC端一致を要求した。注記以外の無条件除外や数値許容差の変更は行っていない。
`full-final-audit-closed-domain.log` と `seed-regression.json` はPASS。
最終カード監査は全条件・原失敗・skip・源/receiptを照合し実終了0。
文書と台帳の変更だけのためにFEM/全検証/専用validatorを再実行していない。
