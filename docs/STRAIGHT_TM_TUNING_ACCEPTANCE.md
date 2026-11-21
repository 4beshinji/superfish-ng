# D02直線TM調整の原条件監査

2026-10-07、原実装カードD02をDONEとする。
親D02/P01、TEカードD03、原互換32要件、全goalは未完。

原条件は [04-design.mdのD02](development-plan/04-design.md#d02)。
D01仕様の明示法則をTM試行生成、追跡、最終細分と保存再開へ接続する。
解析円筒、実段差、無効形状停止、API/CLI/GUIの元要求・最終場・両R/Q一致が受入条件。
元全123カードは保持し、この監査ではD02状態だけ変更する。

## 原条件と証拠

| 原条件群 | 独立確認と元証拠 | 判定 |
|---|---|---|
| 元法則からのTM試行/追跡/最終細分/再開 | 全Case boundary owner、SI式、原座標同時更新、元geometry/mesh/Project束縛、個別ID、版6回復wrapper。metadata6件と実再開/全再生 | PASS |
| 円筒極限の解析関係 | 独立Bessel TM010 f/Hφ/Ez/Er/全PEC壁loss/両R/Qを別検査、1 J/peak-phasor、実最終細分で各誤差減少 | PASS |
| 実段差の元境界/体積/個別ID | 元Case/tags、体積三乗、元E/H長さ尺度の-3/2乗、G/RQ不変・Q平方根、実個別ID、別corner-refined系列の両10 kHz条件 | PASS |
| 無効形状停止 | 両bounds正常でも中間不正形状を次のFEM前に拒否、失敗記録と旧checkpoint/native byte保持 | PASS |
| 三入口の元要求 | 実Chromeで全法則・元Project・追跡条件/単位を復元/再構築、独立API/CLI/GUI request/decision一致、重複キー求解前拒否、改竄拒否 | PASS |
| 三入口の最終場/両R/Q | 同じ元mesh/Case、Hφ/Er/Ezと9 RF量は相対差0、確認閾値1e-10。GUI表示importの元6科学ファイルbyte一致 | PASS |

実曖昧IDはfrequency null、細分なし、UNVERIFIEDで停止し、再開不可を保持した。
元粗段差83,248.404 Hzは元10,000 Hz条件未達でREFINEMENT_FAILEDを保持。
別corner-refined段差系列6,239.675 Hzは元二条件を満たしてTUNED。
同じ閾値を緩和した成功ではない。

## 一般輪郭と数値限界

元z折返し輪郭の全Case/壁tags/体積/両R/Q、実個別IDと完全保存再生を確認した。
元1 Hz細分条件の未達はREFINEMENT_FAILEDを保持する。
追加の局所角細分では、10,217→37,695三角形で差71,165.949 Hz、
次の144,989三角形で差31,378.486 Hz。両水準とも元10 kHz条件を満たさない。
数値未達をTUNEDとする受入証拠はない。これらの全native/元Case/失敗はrawへ保存した。

初稿監査には「折返し輪郭の成功系列」を追加条件として置いた。
原カードの受入文は円筒解析、実段差の元境界/体積/ID、無効形状停止、三入口一致を要求する。
原文照合後、その追加条件を原カードの必須判定から外し、初稿/補正記録を保存した。
一般輪郭の実試行・比較・細分・未達停止が接続されたことと、任意メッシュでの数値成功は
それぞれ記録する。二水準の差は連続離散化誤差やRF/ピーク収束の保証ではない。

## 検査・源・来歴

コア9b6e091、GUI0dff639。
[実装契約と限定検査](STRAIGHT_TM_TUNING.md)の52個別unit＋実Chrome7項目、
独立API/CLI/GUI場/RF比較を原log/源hashへ再結合した。
unitの52件は新metadata6＋新物理6＋直接消費40の分割成功で、
失敗を含む元コマンドの終了1を全PASSへ改記しない。
NumPy scalar・読取namespace・pilot Case・cluster・selectorの元ERRORと修正履歴を保持。

操作比較の誤ったtune.json読取は元API/CLI計算後のrunner ERROR。
checkpoint-004.jsonの原nativeを読取/再生するだけで修正し、追加eig求解0。
輪郭probeの誤importも求解前のERRORを保存してsave_runへ修正。
追加輪郭二求解54.311秒、次の一求解179.535秒は終了0で数値gate false。

raw根拠：
- out/d02-straight-tuning-20261007/bounded-audit-pre-docs.json / source-applicability.json
- out/d02-straight-gui-20261007/corrected/report.json / api-cli-receipt.json / leaf-audit.json
- out/d02-contour-success-20261007/receipt.json / next-level.json / observed-handles.json
- out/d02-whole-acceptance-20261007/acceptance.json / conditions.json / conditions-draft.json

全1275源は開始/終端で固定、1182コアPython源も不変。
科学核・RF定義/積分・旧閾値は変更しない。新依存・外部数学資料・GPU・hosted CIなし。
全handle/server/browser終端、slot 0。監査内の新FEM/unit/seed/full/legacyは0。
過去のfullはこの新経路のfull受入へ relabel しない。

次はD03のTE直線階段/一般輪郭。現在版9のTEは明示拒否し、TMの境界を流用しない。
D04で親P01/D02、D06以降で探索、N03以降でより一般の精度/メッシュ運用を扱う。
