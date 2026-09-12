# 軸区間とPEC穴を持つ真空HφのFEM・保存契約

`AXIS_CONNECTED_HOLES_PLAN.md`の製品Case/solve/RF/native/CLI工程。
候補 `/tmp/superfish-axis-rf-20260912` を主ツリーへ統合し、以下の範囲で限定受入。
Project/Job/GUI/Studyとの接続は後続工程。親P03/O02や全計画をこの工程だけで完了にしない。

## 入力と物理

`AxisHphiCase` / `superfish_ng_axis_hphi_case` schema 1を用いる。
一つの連続真空軸と0個以上の直線PEC穴を持つ、検査済み`AxisConnectedMesh`を必須とする。
vacuum・closed PEC・axisymmetric・m=0・Hφ族・直線P1/P2を明示し、未対応の物理や未知キーは拒否する。
元の正半径HphiMeshCaseの意味は変えない。

未知数は正則なu=Hφ/r。軸の自由度を全て保持し、canonical TMと同じK/Mを使う。
行列積分は各座標方向4点（P1）・5点（P2）の既存Duffy-Gauss、体積RFは各方向5点、壁線積分は5点Gauss。
直線要素の多項式を厳密積分する固定仕様で、ユーザー指定のquadrature_orderを受け取って無視することはしない。
正の最小スペクトルを解き、零モードは除かない。固有値残差・エネルギー規格化・直交性を検査する。
残差や積分の厳密性は、連続問題に対する離散化誤差の保証ではない。

peak exp(+iωt)、Hφ real、E quadratureを保存する。

    Hφ = r u
    Er_quadrature = r u_z / (ω ε0)
    Ez_quadrature = −(2u + r u_r) / (ω ε0)

軸上Hφ/ErはゼロでEzは有限。元のP1/P2係数から評価し、穴内部・負半径・非有限プローブを拒否する。
プローブJSONには全18個のE/H/B成分とSI単位・位相・入力nativeのhashを含める。
3D体積積分は2πr dr dzで穴を除き、各PEC穴の表面損失は正に加える。軸の面積・損失はゼロ。
鋭い角の連続表面ピーク値はこの入力から保証しない。

## 明示した加速経路

`acceleration`はnull、またはpath=`axis`とz_start_m・z_end_m・beta・phase_origin_mの全項目を持つ。
0<beta≤1で、積分区間は宣言真空軸の内側にある。nullならVacc/Eacc/両R/Qはnull。
軸があるという理由だけで区間や粒子速度を補完しない。

Vaccは元の軸上P1/P2をexp(+iω(z−origin)/(beta c))と積分する複素電圧で、real/imagを保存する。
既存の中心化Legendreモーメントによる位相積分を再利用し、要素途中の区間端も扱う。
Eacc=|Vacc|/(end−start)、accelerator R/Q=|Vacc|²/(ωU)、circuit R/Q=|Vacc|²/(2ωU)。
Uは指定した全3Dの時間平均電磁エネルギー[J]。係数位相の選択で複素Vaccは変わるが、両R/Qは変わらない。

## 保存とコマンド

専用形式のcase.json・mesh.npz・fields.npz・results.jsonを保存し、最後にmanifest.jsonを公開する。
保存・再生では宣言から幾何/K/Mを再構成し、軸/PEC/穴の所属、元自由度、最小スペクトル、全RF・規約を照合する。
hashを付け直した結果改変や下位モードの省略も拒否する。既存出力を上書きしない。

    python -m superfish_ng solve-axis-hphi CASE.json --out NEW_RUN
    python -m superfish_ng replay-axis-hphi NEW_RUN
    python -m superfish_ng probe-axis-hphi NEW_RUN --points POINTS.json --mode 1 --out NEW_PROBE.json

modeは1から始まる保存スペクトル順位で、解析ラベル・追跡IDではない。

## 検証状況

追加8unitは2.909秒で合格。既存TMとの同一メッシュK/M・スペクトル・係数/RF、
軸上の多項式場・独立96点の複素電圧、穴内部拒否、実CLI、保存の改変・未完公開を確認した。
実装前の未実装module失敗をout/axis-rf-development-20260912/unit-before.logへ保持する。

一穴/二穴のBessel解析場と全壁RF・二尺度・細分・nativeは16件でPASS。標準1038件もPASS。
周波数最近傍が別の場を選ぶ先行反例を受け、解析磁場との全真空内積と上下guardで照合対象を確認する。
これは解析検証器の対象選択であり、製品FEMへ解析値を埋め込んだり、一般のモード追跡を実装したりするものではない。
最終ゲートはAXIS_CONNECTED_HOLES_PLAN.mdに固定済み。新しい外部資料・依存・旧版参照はない。

12件の番号入替/軸方向鏡映でも、72モードのf・元の場・全線分壁損失・複素Vaccを確認した。
鏡映ではErの符号と、経路・位相原点を写した複素電圧の共役関係を検査した。
証拠はout/axis-rf-independent-20260912、out/axis-rf-geometry-20260912。

## 最終受入記録

標準1038件（1035合格・3skip）は1749.380秒、ResourceWarningなしでPASS。
skipは任意NGSolve参照2件とsandboxの既存ローカルHTTP待受1件。新しいGUI接続は後続工程で検証する。
独立16件のFEM/nativeは1060.310秒、二尺度相似の最大誤差は1.033e-13。
番号入替・z鏡映12件/72モードは2.394秒、軸区間が全z幅より短い凹形・0/1穴は4FEM/native（0.526秒）で確認した。
全z幅を誤って加速区間へ使う要求と、凹形の外側・穴内部の点を拒否する。
主8unit（2.855秒）、同梱2例題の6実CLIも合格。固定601sourceと主607source（不変egg-info 6件）を照合。
seed9モード19量はf差0、最大相対差8.882e-16。閾値・ベンチマークは変更していない。
証拠はout/validation-axis-rf-candidate-20260912/seed_regression.json、out/axis-rf-main-examples-20260912、out/axis-partial-interval-20260912。

最終細分水準の一穴/二穴・二尺度での最大相対誤差。各量の固定ゲートと、各壁線分を含む細分での減少を個別に確認した。

| 次数 | f | E L2 | H L2 | G | Q | P | 壁線分 | 複素Vacc | 両R/Q |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| P1 | 2.793e-04 | 2.368e-02 | 1.453e-03 | 9.392e-05 | 2.335e-04 | 5.130e-04 | 2.081e-03 | 1.685e-03 | 1.309e-03 |
| P2 | 6.003e-06 | 3.468e-03 | 1.366e-04 | 1.666e-05 | 1.966e-05 | 2.567e-05 | 8.804e-05 | 1.557e-04 | 1.758e-04 |

最終P2の解析対応場を元係数から描画し目視した。out/axis-rf-analytic-plots-20260912の二図とsidecarを参照。
この合成例の順位17/26を一般のモードIDとして使わない。
