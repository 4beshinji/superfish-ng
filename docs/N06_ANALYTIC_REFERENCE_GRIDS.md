# N06：円筒/球の全域解析参照格子

2026-10-08 JST、`adaptive_efficiency_analytic_grid.build_analytic_efficiency_grid` を限定受入する。
[N05固定条件](N05_ADAPTIVE_EFFICIENCY_PLAN.md)の完全初期Caseと元source meshだけを認める。
ケース名/寸法だけで別Case/sourceを認めない。orderは16/24、丸め形状は保存独立参照を要求する。
固定入力の全byteを既受入planで検査し、正規化された完全Case・全source meshを照合する。
sourceのcanonical JSON SHAとファイルSHAの違いを保持し、元入力を上書きしない。

円筒は元4×5分割の全(r,z)にGauss16/24を置き、全3D体積重みと全物理軸を保存する。
Bessel TM010の元1 J場・全PEC両端壁loss・両R/Q・解析ピークを参照にする。
球は全P2壁の元curve parameter各区間にGauss16/24を置き、全解析球と全native領域を
半径分率のradial fanで対応させる。P2壁係数と正のz-monotone密度を使い、
元sourceの内部幾何や境界を解析球へ再投影しない。全区間の被覆・正重み・正密度を要求する。
解析場は完全な解析球内で評価し、native場は完全P2領域内で別に評価する。
nativeはsqrt(volume density)で固定円筒成分の単位的L2比較へ接続する。
これはMaxwell場の変形則や振幅fitではない。旧0.95-volumeの診断を全域受入へ流用しない。

独立参照は既存`analytic.pillbox_tm_mode/pillbox_tm010`と`analytic_sphere.SphereTM`を使う。
それらのBessel/PEC根・エネルギー/通過位相・規約の来歴は
[球参照](SPHERE_REFERENCE.md)と[物理仕様](PHYSICS.md)を保つ。新外部源の取得なし。
球l=1のPEC境界では法線Eがcos(theta)、Hφがsin(theta)に比例するので、
極/赤道の既存解析場からそれぞれの最大値を得る。全壁損失・元全軸電圧/両R/Qを保持する。
FEMの場/周波数を解析式で作らず、native解を求める入口は本moduleにない。

返した参照格子は有限Gauss診断の準備であり、native精度PASSではない。
nativeの保存byte・Case/source・全P2境界・実ID・求積/二全域確認を外側で照合する必要がある。
physical_acceptance_status=NATIVE_SOURCE_DOMAIN_ID_CHECKS_REQUIRED、physical_error_bound=nullを保持する。

## 独立物理不変量と限定検査

未実装ImportErrorをbaselineに保存した。新5個別unitの初回1.736秒は数学4件PASS、
不正mesh検査が元schemaのpointsをpoints_rz_mと仮定して1件ERROR。
検査器のキーだけ訂正し、その一件だけ0.703秒・終了0/PASS。製品moduleと四数学検査は不変。
反復分を別件数へ数えず、元ERRORを保全する。

両次数/両ケースで既知の全体積、全軸長、独立3D積分Ue=.5 J/Um=.5 Jを確認した。
球の全native radial-fan volumeは、P2壁のdegree5多項式を独立Gauss4 Green積分した値と
相対1e-12で一致する。全native P2のbulgeを保持し、解析場の領域外点評価/欠測削除をしない。
全curve区間被覆、円筒の密度1/元座標一致、Bessel軸Ez一定/Er0、両R/Qのfactor2を確認した。
球は解析PEC法線Eの極/赤道ピーク、独立全壁H²積分loss/通過電圧/両R/Qを照合した。
変更Case/name/history/source mesh、未対応order/丸めを参照場評価前に拒否する。

主uv・BLAS1・明示PYTHONPATH、standard unittestで分割実行。
元1421対象源は全byte不変、新1423対象/1216 Python源、N06計54個別unit。
新FEM/seed/full/12benchmark/legacyは0。旧fullは1405源であり新源の全検証へ昇格しない。
rawは `out/n06-cost-recording-20261007/analytic-grid-*.log` と `analytic-grid-acceptance.json`。
実保存参照package、共通native/domain判定、実worker費用/12独立実行は後続。
N06・N04・親G03・全goalは継続する。

## 共有参照packageの実保存/終端監査

commit bacabc6の全1423源を固定し、同じ元Case/sourceから四格子を実生成した。
円筒Gauss16/24は5120/11520体積点と80/120軸点、球は2048/4608体積点と128/192軸点。
全配列を四NPZへlossless保存し、allow_pickle=Falseで完全array一致を確認した。
完全Case/source/両R/Q・全wall/analytic peak、元入力四SHAをmetadataへ保持する。
全1423源、helper自身、四元入力、四metadata/四NPZを終端監査で再hashした。
両次数/両ケースのUe/Um各.5 Jと全shape/finiteを再確認し、欠測の削除は0。
これは新たな共有準備consumerであり、unit件数やnative benchmarkへ加算しない。

生成は0.995978秒・終了0/PASS、recorder lifetimeに限りimport/プロセス開始は含まない。
process peak RSS=89391104 bytes。片側FEM費用をこの共有準備で割り引かない。
新FEM/12benchmark/seed/full0、元1423源は不変。
rawは `analytic-reference-grids/manifest.json`、四JSON/四NPZ、
`analytic-reference-export-acceptance.json` とexport/audit log。
N06実workerの全native source/domain/実ID/量別精度・費用確認は後続。
