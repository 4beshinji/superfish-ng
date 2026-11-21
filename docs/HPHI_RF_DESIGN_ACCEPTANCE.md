# D09：Hφ RF評価の原条件受入

2026-10-07、D09 **DONE**。評価の原条件を保持し、四段階の実装証拠を条件ごとに監査した。
実装の最後は `c91583a`。原123カードはD09の状態だけ変更して64 DONE/2 IN_PROGRESS/57 PLANNED。
原互換32要件・親D03と全goalは未完。次は先行B01がDONEのD01（非曲線TM/TE調整の形状対応）。

## 原条件と証拠

| 原条件 / 継承D05評価条件 | 結果と証拠 |
|---|---|
| 親D03、先行D05/H16 | 両先行カードDONE、元依存/親は不変。親の完了へは数えない |
| 真空/内導体/確認済み材料の全周量を接続 | [五native観測](HPHI_RF_DESIGN.md)と[材料](MATERIAL_HPHI_RF_CONVERGENCE.md)・[直線真空](VACUUM_HPHI_RF_CONVERGENCE.md)・[曲線P2](CURVED_HPHI_RF_CONVERGENCE.md)の全元RF再構築 |
| 軸量の有無、全PEC壁 | 有効真空軸の複素Vacc/両R/Q、無軸N/A。全穴/component/参照segmentを保持、総和だけで壁の帰属を判定しない |
| 材料損失は受入済みH17モデルだけ | 実数無損失媒質＋常伝導壁Qのみ。[追加損失](MATERIAL_HPHI_LOSS_SCOPE.md)の必要性は対象版資料待ち、volume/complex/総Qを拒否 |
| 同軸TEM/TMの独立f・場・壁loss/保存 | TEMの二尺度/三水準、追加Bessel radial TMの三元FEMと個別四壁損失、保存完全再生。解析をsolverへ混ぜない |
| 一様材料/二層の独立f・場・壁loss/保存 | 単一観測の一様/二層と、二層三水準の全region energy/全壁、共通phase、移動完全再生 |
| 軸無し/非真空区間/未実装peak・損失拒否 | 能力/strict入力は行列再構築前に拒否。元RFの理由付きnullを保持、N/Aを0/無条件METへ変換しない |
| 三水準の個別ID/guard/量別判定と採用 | 元E/H個別追跡、各水準の実rank/有限guard。f/E/H/Ue/Um/U/P/Rs/Q/G/存在する両R/Q/複素V/全壁を独立判定。最後二変化と全inclusive包絡、親UNVERIFIEDが局所METを覆しeligible=null |
| 記録・元native/hash・再生・ローカル納品 | 元15byte hash、全宣言/criteria/値/gate/型を完全再構築、移動再生/偽装/遅い変異拒否。実装コミットと本条件別記録、raw終端を保持 |

粗い真正曲線や一般穴系列は、個別IDが成立してもf/E/局所壁などの数値gateが未達ならUNVERIFIED。
この拒否の受入を、その系列の連続問題への物理精度の証明へ読み替えない。
解析TEMの曲線API検査は幾何上直線のP2要素であり、非アフィン穴付きの元P2領域検査と区別する。
固定二次領域の経験的三水準包絡だけを評価し、解析境界の幾何誤差・連続誤差上界・表面peakを保証しない。

## 実行証拠と適用性

| 分割受入 | coherent commit | 過去の選択検査 |
|---|---|---|
| 単一観測 | `c582a30` | 新6（9.674秒）＋直接利用18（51.316秒）、全終了0 |
| 材料三水準 | `ad52fef` | 新6＋直接15＋事前region拒否1=22、全終了0 |
| 直線真空三水準 | `e47a433` | 新8＋直接17=25、全終了0 |
| 曲線P2と追加同軸TM | `c91583a` | 新8＋直接8＋TM1=17、全終了0 |

四receipt内で重複する検査IDを除くと過去76個別ID。新しい全suite実行数ではない。
元log hash/実終了0・各coherent commitの全選択テストbyte・全科学源を現在へ照合した。
変更された旧RF adapterは追記だけ、旧optimizerはimport追加だけで、すべての旧数値定義ASTは不変。
材料region事前拒否/曲線有理chart事前正規化は各段階の独立反例・FEM0修正証拠を維持。
新規の本全条件監査ではFEM/unit/seed/full/legacy実行0。文書のための数値再実行はしない。

追加同軸TMは元三solve後にNumPy scalarのcriteriaがstrict APIで拒否されたrunner ERRORを保全した。
同じ値のPython floatを使って全元nativeを再構築し、既存三solveを保持して追加1件49.705秒/終了0。
finite comparison計算と全再構築を実行し、新しい原solve呼出しは0。
専用validatorは成功数値core/元creatorの源結合と、CLI help終了0/既存出力拒否終了1（FEM0）を分けて確認。
配置CLI全体の新数値実行はしていない。[将来コマンドと証拠](CURVED_HPHI_RF_CONVERGENCE.md#検査と来歴)を参照。

rawは `out/d09-whole-acceptance-20261007/conditions.json` / `audit.log`。
四receiptは同rootにhashと元logの参照を束縛し、元を上書きしていない。
真空の歴史的receiptにはmethod suffixを二重に連結したコマンド表記が5件あった。
実ログは成功した元ケースを示しており、訂正した再現可能な同等選択コマンドを
`corrected_equivalent_commands` に別保存した。これを追加実行したとは主張しない。
初回読取監査のKeyError（vacuumの終端キー配置差）も保全し、元観測のlive=[]を照合して修正した。

## 後続と来歴

D10-hphiの初期/候補/最終独立solve・全trial・所有checkpoint・CLI/worker/GUI・中止再開は未受入。
先行D07が未完なので、依存の揃ったD01からD02/D03/D06/D07へ進める。
H17/C07-planarの不足資料/参照環境は独立して保持する。D09完了で親/global条件を縮小しない。

独立解析/尺度式は既存自作基準を検査に再利用。新外部資料・依存・legacy source/binary参照・旧実行なし。
Hosted CI/GPU実行を主張しない。今回の全条件監査は読取処理と文書/台帳状態更新だけ。
