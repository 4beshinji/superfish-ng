# P09 曲線比較・追跡・調整の条件別監査

2026-10-07、原カード[P09](development-plan/03-planar.md#p09)の全条件を監査中。
先行P04/P08はDONE。本書の表は既に受入済みの限定検査を統合するもので、
新しい全件実行数へ加算しない。節目の全validateはまだ実行中で、P09はIN_PROGRESS。
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
| 節目の全unittest・seed f/RF・固定源 | `out/validation-p09-milestone-20261007` の全validateを一度起動、handle60083の同じ実行を観測中。終了状態・skip・seed f/RF・開始時1365源fingerprintの一致は未確定 | 実行中 |

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
全validateはこのカードの節目で一度起動し、事前に全discoveryを重複させていない。
全実行終端まではsrc/tests/scripts/examplesを固定する。

大容量GUI監査は基準e395996の全420製品源不変、元7trial×九ファイル=63 entry、
完全科学保存と元native五byte/実download五byteを確認した。
生成時の曲線源15件は14現行不変＋1生成当時archive一致。古いmanifestを現行creatorへ置換しない。
新外部実装/依存/legacyソース再利用なし。大容量検証器のCDP設定だけは
[Chromiumの公式Network protocol定義](https://raw.githubusercontent.com/ChromeDevTools/devtools-protocol/master/pdl/domains/Network.pdl)
のAPI意味を参照した。旧ソルバー比較/実測/Hosted CI/科学GPUは今回未実施。
P09の状態は全validateと残る監査が終端した後に判定する。後続はC07-planar→P10。
