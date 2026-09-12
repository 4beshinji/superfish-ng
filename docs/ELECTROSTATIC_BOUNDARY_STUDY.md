# 静電場の有限外部境界とメッシュ細分

2026-09-13 JST。[計画](ELECTROSTATIC_BOUNDARY_STUDY_PLAN.md)の独立144例と追加2unitはPASS。主711sourceへ統合・限定受入。
候補は `/tmp/superfish-electrostatic-boundary-study-final-20260913`。ソルバー/保存/CLIに変更はなく、検証3ファイルと実行例2ファイルを追加する。

平面は幅w・帯状電荷0≤y≤a・接地y=b、他辺Dn=0とする。epsilonとrhoを固定し、b/a=2,4,8を独立に計算する。
電位は帯内でrho(2ab−a²−y²)/(2epsilon)、帯外でrho a(b−y)/epsilon。
Ey=rho min(y,a)/epsilon、接地電荷は−rho wa [C/m]、エネルギーはrho²w(a²b−2a³/3)/(2epsilon) [J/m]。

軸対称はa≤r≤b、長さL、内面の外向きDn=−lambda/(2πa)、外面接地、端面Dn=0。
lambdaを固定するとPhi=lambda log(b/r)/(2πepsilon)、Er=lambda/(2πepsilon r)、
接地電荷は−lambda L [C]、エネルギーはlambda²L log(b/a)/(4πepsilon) [J]。
固定電圧のコンデンサを拡大するとlambdaも変わるため、固定電荷の境界移動とは区別する。

各座標系、P1/P2、epsilon倍率1/7、電荷符号±、境界距離3通りで48個の固定境界系列を作り、各3段階を細分する。計144実FEM。
P1は16/32/64、P2は8/16/32。独立4×4 Gauss/Duffy積分で元Phi/E/Dを測り、エネルギーと元D表面電荷も別判定する。
反力電荷の保存だけで受け入れない。P2帯状電荷は表現可能な区分二次解として丸め誤差まで照合する。
境界間の共通内部プローブで32組の電位変化と場変化を別に記録する。

共通内部の電場は外部接地位置に依存しないが、絶対電位は帯状電荷ではbに比例し、同軸電荷ではlog(b/a)に比例して増える。
この2例には無限遠0電位の有限解がない。小さな場の境界差を、絶対電位や開放境界誤差の収束判定へ流用しない。
これらは解析可能な有限境界の合成対照であり、一般形状の自動遠方化機能や厳密開放境界ソルバーではない。

追加2unitは4.116秒、独立144例は163.620秒でPASS。
独立出力は `out/electrostatic-boundary-study-independent-final-20260913/report.json`。
最細P1の最大相対差（Phi/E/D/U/元場電荷）は平面 [1.62205e-4, 3.81577e-3, 3.81577e-3, 1.45601e-5, 5.08493e-5]、
軸対称 [5.75124e-4, 9.25796e-3, 9.25796e-3, 8.57098e-5, 1.62313e-2]。
最細P2は平面の全量1.889e-11以下、軸対称 [4.92037e-6, 3.01508e-4, 3.01508e-4, 9.09069e-8, 6.57486e-4]。
epsilon尺度則の最大差2.445e-11、共通電位シフトの最大相対差4.048e-4、共通場の境界間差1.128e-2。各固定境界の離散化誤差とは別の記録である。

単独で使える二層コンデンサ入力は `examples/electrostatic/axisymmetric_capacitor.json` と `examples/electrostatic/planar_capacitor.json`。
専用のsolve/replay/probe計6CLI、4nativeの全20ファイルとプローブJSONのAPI/CLI一致を確認した。元20ファイルは不変。
未使用の新しい出力ディレクトリで実行する：

```sh
python -m superfish_ng solve-electrostatic examples/electrostatic/axisymmetric_capacitor.json --out out/my-axis-capacitor
python -m superfish_ng solve-planar-electrostatic examples/electrostatic/planar_capacitor.json --out out/my-planar-capacitor
python scripts/validate_electrostatic_boundary_study.py --out out/my-boundary-study
```

固定705sourceは、平面native候補700sourceをそのまま継承し、最終独立144例の全source hashと一致する。
初回のRF例移行2検査は、静電例をexamples直下に置いたことで4errorsとなった。
専用examples/electrostatic/へ移し、入力内容・元RF例・RF parser・テストを変更せず、新規2+旧RF移行2unitと144例/6CLIを再実行してPASS。
初回144例のPASS、配置のFAIL、修正理由と元ファイルの同一性は `out/electrostatic-boundary-study-development-20260913/example-relocation-decision.json` と関連ログに保持する。
既存標準の製品/テストsource hashを照合し、新規2unitを別に検証する。標準1159件を新規に再実行したとは扱わない。
新規依存・外部資料・旧版実行なし。S01と全計画の状態は受入照合表で確認する。

主4unitは4.252秒でPASS。統合と全ソース対応の証拠は `out/electrostatic-boundary-study-main-20260913/integration.json`。独立144例は元のsource hashへ結び付け、本体で全144例を再実行したとは扱わない。

本体へのコピー時に新しい例ディレクトリの作成が欠けていたため一度停止した。既にコピーした3検証ファイルのhashを照合してから、欠けた例2ファイルだけを新ディレクトリへ配置した。再度主4unitと全711sourceを確認してPASS。記録は `out/electrostatic-boundary-study-development-20260913/integration-directory-repair.json`。
