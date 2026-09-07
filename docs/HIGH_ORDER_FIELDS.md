# N02: P2の場・RF・保存契約

2026-09-08。N01の直線三角形P2 u空間を製品経路へ統合する。
本書は仕様と進行記録であり、N02全体の受入宣言ではない。

## 場評価

元の3頂点Meshで点を探索し、同じ要素の6係数からuと物理勾配を評価する。
Hphi=r u、Er=-r∂zu/(ωε0)、Ez=(2u+r∂ru)/(ωε0)。軸ではHphi=Er=0、Ez=2u/(ωε0)。
界面では選択要素の片側値。平滑化や頂点だけへの切捨ては行わない。
FieldSamplerは明示したQuadraticSpaceを検証し、from_solutionで次数と空間を受け取る。
空間を渡さない旧呼出しはP1契約を維持し、P2配列を拒否する。

## RF積分と表面量

体積Uは高次K/Mで計算する。軸電圧は各辺の二次多項式とexp(ikz)の積を積分し、
小さいkで桁落ちを避ける。区間端で多項式を切り、位相原点はR01の規約に従う。
TTF分母は二次式の実根で分割して絶対値を積分する。低betaでも細かい表示点に依存させない。
PEC損失は辺上のr³u²を厳密積分する。表面Eは二次、Hは三次であり、端点と内部停留点から
片側推定極値を求める。特異角の有限ピークや誤差上界は保証しない（N03で収束診断を扱う）。

## 保存・利用箇所の移行

元の幾何メッシュと高次自由度を別に保存する。次数・自由度座標・6列接続・境界中点と
係数形状を読込時に検証し、再構成した空間と一致しない保存物を拒否する。
P1旧保存とcase hashは維持。新しいCase次数指定はv3でstrictに検証する。
表示は各P2三角形を4枚に分割して高次場を評価し、描画近似と保存係数を区別する。
鏡映は全中点を含む自由度へ偶奇を適用する。半/全の正規化・R01区間を保持する。

移行対象はrf.cell_fields/quantities、sampling.FieldSampler、ioのVTK/NPZ/axis CSV、
savedの読込/解析比較/probe/モード比較、visualizeの場/磁束表示、symmetryの反射、
studiesの場重なり/軸評価、modesの軸テンプレート、Case/Project/CLI/GUIの次数保持。
保存完了manifest（O01）も新しい必要ファイルを検証する。

## 受入条件

独立した二次多項式で全場成分・勾配・軸極限を検査する。
Bessel場のE/H形状、U、RQ/Gを複数細分・複数モードで個別比較する。
P1/P2の誤差対自由度を周波数・軸Ez・RQについて別に記録する。
低beta・部分区間の電圧を独立積分と比較し、位相/寸法/正規化不変量を検証する。
半/全領域、保存再読込、probe、表示、追跡、CLI/GUIの次数保持を検査する。
N01の周波数合格だけではN02を完了しない。

## N02.I進行記録 — 2026-09-08

FieldSamplerの明示space指定とfrom_solutionを実装。元の三角形で探索した後、
6係数と二次基底の勾配から場を評価する。接続/中点座標/係数形状の不一致を拒否する。
独立二次多項式の全成分・軸極限・領域外処理、TM010の軸Ez一定形状を検査した。
保存、cell_fields、RF積分、鏡映、表示、追跡の製品統合は引き続き未実装。

ローカル検証: out/validation-n02-sampling-20260908/validation.json PASS。
152 tests中150合格・2 skip。円筒/成形セルのmode辞書全量とcase_sha256は
out/validation-n01-accepted-20260908と一致。
再現はOPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/validate.py --out out/validation-<unique-name>。
次は二次軸電圧の安定積分、PEC辺損失と片側極値を実装し、独立積分と比較する。
N02.V全体は未受入。

### 二次軸電圧の積分 — 2026-09-08

quadratic_rf.quadratic_voltageは元の軸辺の両端/中点から二次式を構成し、指定区間へ
変数変換して積分する。中心座標xでx=P1、x²=(P0+2P2)/3を使い、
指数関数との積分を球Bessel関数j0/j1/j2で評価する。SciPyは既存依存。
絶対値積分は実根で区切った多項式原始関数から求める。
accelerating_voltage_p2はP2解の軸辺とR01の区間/位相/betaを接続する。

独立のSciPy重み付きQUADPACK積分で波数0/1e-10/.01/10/±3000、
内部の符号反転2箇所、区間切断・位相回転・逆向き辺を照合した。
P2 FEMの2モードでbeta=.03と部分区間の電圧も任意点場の独立積分に一致。
ゼロ場と不正な辺の拒否を検証。RF quantitiesへの接続はPEC積分完成後に行う。

ローカル証拠: out/validation-n02-voltage-20260908/validation.json PASS。
155 tests中153合格・2 skip。円筒/成形セルの周波数/RF全量・case hashは直前と一致。
次はPEC辺の損失積分・内部停留点を含む片側極値。N02全体は未受入。

### PEC積分・RF量への接続 — 2026-09-08

surface_integrals_p2はPEC辺のr³u²を4点Gauss（7次厳密）で積分する。
同じ境界要素の6係数からEの二次多項式、Hの三次多項式を構成し、
ノルム二乗の導関数の実根と両端を比較して片側推定極値を求める。
rf.quantitiesとcell_fieldsはP2解へ対応。P1経路の演算順と結果は維持。
保存/描画/鏡映/追跡は引き続き未統合で、Case/CLIの次数指定も未公開。

独立検証は、内部極大を持つ既知の二次/三次式、二次多項式uの表面積分と
解析微分からの場、独立QUADPACK積分と有界極値探索。円筒の3モードで
R/QとGを4×8、8×16、16×32と細分し、最後の相対誤差を1e-4未満、
8→16の誤差比を0.15未満として合格。16×32のR/Q誤差は
9.066e-6 / 2.313e-5 / 7.404e-5、G誤差は1.253e-7 / 8.705e-7 / 6.341e-6。
U=1 J、電磁エネルギー均衡、Uを4倍にした時の電圧2倍/損失4倍とRQ/G/Q0不変も検証。
円筒ピーク量・Bessel場形状の収束、誤差対DOF、半全・保存・表示は後続の受入に残す。

ローカル証拠: out/validation-n02-rf-20260908/validation.json PASS。
158 tests中156合格・2 skip。円筒/成形セルのmode辞書全体とcase_sha256は
out/validation-n02-voltage-20260908と一致。N02全体の.Vは未完。

### P2半領域の鏡映 — 2026-09-08

reflect_solutionは幾何メッシュの鏡映後に全領域QuadraticSpaceを組み立て、
元要素と鏡映要素の6自由度へ偶奇を適用する。局所順0/2/1への反転に伴い
辺01/12/20は20/12/01へ写る。座標の近似照合や場の補正を用いない。
磁気対称の中点も厳密ゼロを要求し、全K/Mを再組立して残差を検査する。
全領域順位とは異なるparity-filtered spectrumの注記を維持する。

両端×電気/磁気対称の4条件で、全中点を含む場の偶奇、U/損失2倍とQ0不変、
同じ全領域メッシュを別に固有値計算した周波数/RQ/損失との一致を検証。
非ゼロの磁気対称中点を故障注入して拒否を確認した。
ローカル証拠はout/validation-n02-reflection-20260908/validation.json PASS。
159 tests中157合格・2 skip、円筒/成形セルのmode辞書全量とhashは直前と一致。
次はP2保存・再読込・表示/追跡統合とBessel場/ピークの収束証拠。N02全体は未受入。

### 表示用分割とVTK — 2026-09-08

display.display_fieldsは各P2三角形を中点で4分割し、元のP2係数から表示点のHと
表示三角形中心のE/Hを評価する。write_vtkへ接続し、タイトルに表示用分割を明記。
RF計算は表示三角形を使用しない。P1の頂点・要素・場・VTKバイト列は維持する。
独立二次多項式で中心場、分割の正向きと面積保存、VTKの点/要素数・保存場を検証。
ローカル証拠: out/validation-n02-display-20260908/validation.json PASS。
161 tests中159合格・2 skip。円筒/成形セルのmode全量・hash・全VTKは直前と一致。
保存runのP2解禁と再読込、plot_modeへの接続は未完。次はその保存契約を実装する。

### 保存・明示読込 — 2026-09-08

save_runはP2を保存し、results.field_spaceに次数2・幾何次数1・基底名・DOF数、
fields.npzにdof_points/cell_dofs/boundary_dofs/axis_dofsを追加する。
axis CSVは中点を含む全軸自由度。完了manifestは追加配列を含むNPZ全体をhash検証する。
read_solution(..., allow_quadratic=True)は空間を再構成して4配列とDOF数を照合する。
旧消費側の移行完了までは既定読込とplot_modeがP2を明示拒否する。これは移行途中の
保護であり、完成仕様ではない。次は全消費側へ次数/空間を渡してこの制限を撤去する。

全係数・probe場の往復一致を検査。manifestを再hashした接続/座標/軸/境界の破損も
構造検証で拒否した。out/validation-n02-storage-20260908/validation.json PASS、
162 tests中160合格・2 skip。円筒/成形セルのmode全量とcase hashは直前と一致。
N02全体は未完。

### 保存P2解の描画 — 2026-09-08

plot_modeはread_solution(..., allow_quadratic=True)で完了・構造検証してから
display_fieldsのP2表示分割とFieldSamplerの高次場を使う。軸曲線は元の軸節点と
401点の評価を併用し、radial/quiverも元P2場を評価する。P1も完了検証を通す。
保存前の解と描画radial値の完全一致、PNG生成、未完了run拒否を検証。
out/p2-plot-20260908/mode2.pngを実生成して目視確認した。
標準証拠はout/validation-n02-plot-20260908/validation.json PASS、
163 tests中161合格・2 skip。円筒/成形セルのRF全量とhashは直前と一致。
plotの暫定拒否は撤去済み。savedの解析/probeとstudiesの次数移行は引き続き未完。

### 保存済みP2のprobeと円筒解析比較 — 2026-09-08

export_radial_probe/compare_pillboxを明示高次readerとfrom_solutionへ移行した。
P2の軸場L2誤差は元の軸辺ごとに8点Gaussで高次場と独立cos場を比較する。
頂点や中点を直線で結んだ場を誤差評価へ流用しない。P1の評価経路は保持。
保存probe全成分が元解と完全一致。円筒3モードの場同定はTM010/011/012となり、
周波数・軸場・RFゲートがPASS。表面ピークはこのゲートに含めない。
ローカル証拠out/validation-n02-analysis-20260908/validation.json PASS。
164 tests中162合格・2 skip、円筒/成形セルのRF全量とhashは直前と一致。
次はバンド解析/studiesの高次軸評価と追跡を移行する。N02全体は未完。
