# RF版5対照の独立全域参照

2026-10-13 JST、`ADD-N04-rf-goal-03` **DONE**。
[固定仕様](CURVED_RF_GOAL_EFFICIENCY_SPEC.md)の六ケースについて、Gauss16/24の全領域参照を準備した。
球は独立解析式、長球と丸め二ローブは既存N03の独立E空間の三h・全五modeである。
参照データの受入とnative実計算の精度を区別し、返却値の`native_accuracy_status=NOT_RUN`、
`physical_error_bound=null`を維持する。worker/36実行/保存GUIは04〜06、親N04と全計画は未完。

## APIと固定データ

新`src/superfish_ng/curved_rf_goal_efficiency_reference.py`の入口は次の三つ。

| API | 責任 |
| --- | --- |
| `build_sphere_rf_goal_reference` | 固定球Caseの全域数学参照。尺度2は半径0.16 m・4 JでSphereTMの式を再評価 |
| `map_prolate_rf_goal_points` | 全ての供給点を今回の固定P2領域へ写像し、元順序と正の体積密度を返す。単独では求積の全域被覆を保証しない |
| `load_curved_rf_goal_efficiency_reference` | 固定六ケースの元要求/全mesh/ID、独立源・場配列、両Gauss次数・三hの二変化を結合して返す |

[prepared_references.json](../examples/curved_rf_goal_efficiency/prepared_references.json)は
球/丸めの元manifest、丸めの元matrix、今回の長球manifestの四SHAと履歴源の明示aliasを固定する。
registry自体のSHA/byte数もreaderに固定し、callerが改変manifestを再hashしても受理しない。
任意`bindings`はこの四つの同一byteを別pathから読むためだけに使う。
各依存fileを読取前後に検査し、欠落/変更/不完全なmode・node・重みはValueErrorとなる。
大量の元参照・保存係数はignored `out/`に残す。配布時にそれらを同梱したとは扱わない。
依存がない環境では参照不足となり、native解を代用しない。

## 全域・実場・相似の確認

| family | Gauss16の体積/軸点 | Gauss24の体積/軸点 | 尺度 |
| --- | --- | --- | --- |
| sphere | 2048 / 128 | 4608 / 192 | 1, 2 |
| prolate | 157184 / 9824 | 353664 / 14736 | 1, 2 |
| rounded-two-lobe | 22528 / 1408 | 50688 / 2112 | 1, 2 |

計12grid、体積1181440点・軸56800点を全て使用した。crop/点削減/欠測除外/振幅fitはない。
三つの幾何積分（断面積、回転体積、断面上の∫r³）は別の境界Green積分と照合し、
相対差最大5.885e-15、元許容1e-12以内。全物理軸重みの和も空洞長と一致する。
球では解析場の電気/磁気エネルギーがそれぞれU/2となることを独立に確認した。
現P2写像と解析形状を混同せず、全radial/polar fanと体積密度平方根の既存比較規約を保つ。

長球の旧N03 native chord=0.0001 mと今回0.0016 mは異なる領域である。
旧独立参照の全614角度区間には今回の全P2境界区間端点が含まれており、
元解析点/正求積重み/全独立場を保持して、新しいnative点と密度を全点で作成した。
各境界区間の二次Jacobianは端点と内部極小を調べ、供給点がない区間も正であることを要求する。
readerも新しい固定P2写像を再計算し、packageの全native点/密度と正確に一致させる。

長球は元2.20 GBの全場記録と保存係数を結合し、両次数・三hそれぞれの32点
（体積16＋物理軸16、計192位置・全五modeの960場vector）を既存独立solverの係数から再評価した。
このprobeは元評価座標/密度を使い、保存済み全場の該当値とbit一致する。
全gridの再標本化や固有再求解は行っていない。元全五候補からの実Hφ対応、target/二guard、
overlap≥0.98・margin≥0.05、元TE/TM適格性・Ue/Uh/規格化も保存した。
丸めは元N03 matrixの全個別ID、元native anchorの全Case/source/byte、全参照modeを再確認した。
これは新規native初期場との対応証明ではない。04/05では初回実場からIDを別に確認する。

長球/丸めのh=0.005/0.0025/0.00125 mについて、全E/H/軸Ezと両R/Q/G/peak/fの二変化を再計算した。
元nativeノルム分母・一つの磁気符号・元九閾値を維持し、Gauss16/24間の誤差差も確認する。
全family/次数/尺度での最大値はE=0.002439、H=0.001500、軸Ez=0.0001650、
f=3.657e-7、両R/Q=9.749e-6、G=0.002800、Epeak=0.0001224、Bpeak=0.002656で、全て元閾値内。
有限求積による場エネルギー診断と、元係数のUe/Uh適格性を別記し、前者を新しい厳密誤差上界とはしない。

U=a² Jの相似は全点の座標×a、体積重み×a³、軸重み×a、E/H÷√a、f÷aを確認した。
密度・両R/Q・G・正規化peakは不変。全三h・全五modeの配列を変換して保持する。
独立peakは有限solverの経験的値であり、連続最大値の保証ではない。

## 出典・履歴源の結合

独立源は既存MIT cavsim2d commit `48741ff46ca44463281a5ab5945328615881b502`の79fileと
元N03/A01のmanifest。既存隔離uv環境で係数probeだけを実行した。
新取得/依存追加/network/legacy solverは0。製品readerはNGSolveをimportしない。

最初の全参照読取は、旧N06が要求する過去の`cli.py`のSHAで停止した。
後続GUI/再mesh作業で変わった八fileをcommit `bacabc6`から別outへ保存し、
元manifestのSHAと完全一致させた。registryの明示aliasで履歴源を参照する。
古いコードは出典確認用で実行せず、現行源の巻戻し、元場/閾値/旧readerの変更はしていない。
aliasにも元SHAを要求し、symlink/変更/欠落を拒否する。

## 検証とraw

rawは`out/n04-rf-goal-reference-20261013/`。

- 新幾何unit5件：9.832秒、終了0、handle96080。
- 新整合unit4＋旧analytic_grid5＋旧accuracy8の17件：3.976秒、終了0、handle19980。
- 長球package準備：38.833秒、最大RSS6120251392 B、終了0、handle98834。
  3600秒/32 GiBの独立準備枠内。内側観測31.374秒との重複加算はしない。
- 六ケース/12gridの全参照検査：終了0、handle75114。`all-references.json`に全結果と源SHAを保存。

unitは計22個別PASS（新9＋直接利用先13）。いずれも既存unittest/uvを使用する。
コマンドは`OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-uv-cache`
の下で`uv run --no-sync python -m unittest -v`へ次の二組を渡した。

1. `test_curved_rf_goal_efficiency_reference.CurvedRFGoalReferenceGeometryTests`
2. `test_curved_rf_goal_efficiency_reference.CurvedRFGoalReferenceIntegrityTests test_adaptive_efficiency_analytic_grid test_adaptive_efficiency_accuracy`

初回inventoryの集約report取違えKeyErrorと、履歴SHA不足による読取停止を元logのまま保全した。
全grid成功後の変更は履歴sourceのsymlink拒否とその検査追加だけで、成功時の源byteを再構成してSHA照合し、
全数値関数のAST不変を確認した。科学検査は再利用し、hash更新のための数値再実行を行わない。
元1470対象源は全byte不変、新module/test/registryの3源を加えて1473。
全handleは終端、新FEM/seed/full/GUI/36benchmark/legacyは0。
監査初稿のTSV列名誤記も元script/logを保全して訂正した（数値再実行なし）。
監査は`acceptance.json`、コミット結合は`commit.json`に保存する。

全141カードは91 DONE/2 IN_PROGRESS/48 PLANNED。原123は76/2/45を保持。
次は`ADD-N04-rf-goal-04`の版5branch・全event観測・保存/完全再生workerである。
