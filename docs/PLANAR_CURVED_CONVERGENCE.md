# 平面曲線の固定円・最終二水準 — P07限定検証

2026-10-02、基準 `bb9b26a`。[P07](development-plan/03-planar.md#p07)はIN_PROGRESS。
[P05の固定gate](PLANAR_CURVED_RF.md#検査入力と固定した個別gate)に従い、
保持した円の解析対照とは別に、最終二水準のf・元E/H・全単位長RF差を検査する。
独立A/B内部mesh、増求積次数、真形状の幾何系列、楕円/再入角はこの実行の受入範囲に含まない。

## 比較の対象と独立対照

`scripts/validate_planar_curved_convergence.py` は前回の14元解を再solveせず、
最終8解のCaseと全係数を `restore_planar_curved_solution` で物理再構築する。
geometry/K/M/拘束・規格化・lowest正帯を再検査するため、再構築にも行列とスペクトル検査が必要だが、
保存係数を新固有ベクトルへ置換しない。前後の401製品hashと、前監査の全raw artifact hashが
完全一致する入力だけを受け付ける。新出力は既存結果を上書きしない。

uniform親chartは粗い元Domainから再生成し、fineの全geometry配列と一致することを確認する。
保存NPZの親cell/chartを無検証で使用しない。細分は元P2写像の制限であり、真円へ再投影しない。
全領域の座標丸め上限/局所幅も記録する。

order10の独立Duffy面積則でscalar crossを積分し、各完全群の単一直交回転を求める。
第二のpassでは、その同じ回転を粗い元EとHへ適用し、実vector差の二乗を直接積分する。
ほぼ等しいGram行列同士の差で誤差を算出せず、E/H別の位相や振幅合わせを行わない。
fineの実面積を使い、各側の場はそれぞれの元J逆と元周波数から評価する。

周波数とRFは各元順位の値を保持して比較する。RF対象はU′/U′e/U′m、P′、Rs、Q0、G、
実壁H二乗積分。面積/実周長/求積次数/規約を含む完全RFを保存し、二つのR/QとVacc/Eaccは
理由付きnullを照合する。円の静的解析群を使う限定validatorであり、永久モードIDや枝追跡を宣言しない。
guard完全群も全場・全RF・判定を保存し、対象TEの最初5/TMの最初3を判定する。

独立対照の新5unitは、元P2係数の正確な制限、線形scalar二重群の既知回転、
規定周波数の3%変化でTEのEだけが3%変わること、振幅3%差が残ることを検査する。
これらのmanufactured場は比較積分/同群回転の不変量であり、Helmholtz固有場の解析解ではない。
不正Domain/全正帯の不完全群/異なるσ/不正次数、入力artifact/製品hash変更も拒否する。

## 着手時に再現した未達条件

保持RFだけを照合すると、TM二尺度のL2→L3はP′差8.516784e−3、
G差8.441330e−3、Q0差8.442507e−3で、0.5%基準を超えた。
解析GがL3で0.295791%以内でも、最終FEM差は別に未達である。

直接元場比較ではTE01のL1→L2 E差1.031211955%も1%基準を超えた。
他の対象群の場やTEのRFが合格しても、これをTE全対象の合格にまとめない。
未達を保持し、元境界・規格化・f≤1e−4/E,H≤1%/全RF≤0.5%の許容値を変更せず、
TEだけL3、TMだけL4へ一水準ずつ追加する。geometryの検査予算は最大1e8へ明示的に増やす。
これは物理gateの緩和ではなく、より大きい同Domain細分の全edge検査に必要な上限である。

## 実行記録

新5unit/session79738は1.828秒PASS/終了0。
初回専用/session8261は最初のTE比較後のNumPy bool JSON保存で終了1、新FEM0。
exception記録も同じ型で失敗したため、終端後にhash不変/新FEM0/理由を`termination.json`へ記録した。
失敗logと初回出力を保持し、gateの保存型だけPython boolへ変更した。
JSON往復を加えた限定1unitは0.521秒PASS/終了0。数値製品・物理許容値は不変。

専用/session72321は1086.911秒PASS/終了0。二尺度・両偏波の4最終caseで全対象群がPASS。
前回14元解のrawは全byte/hash不変、最終8解を物理再構築し、未達4caseだけ追加4FEMを行った。
保持する元FEM解は合計18。通った既存解を新係数へ置き換えず、全初回未達とguard判定を残した。
TE L3は7168cell/14465DOF、TM L4は28672cell/57601DOF、いずれも元初期N16円の制限。

二尺度の最大値を以下に示す。群のE/H差は完全領域の実面積norm、RF差は各元順位の値である。

| 偏波/最終二水準 | f差 | E L2差 | H L2差 | P′差 | G差 | Q0差 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| TE L2→L3 | 3.378027e−6 | 2.600747e−3 | 8.860740e−5 | 1.251303e−5 | 7.445893e−6 | 9.134889e−6 |
| TM L3→L4 | 1.513137e−7 | 1.059211e−5 | 5.502180e−4 | 2.211194e−3 | 2.206089e−3 | 2.206164e−3 |
| 固定gate | ≤1e−4 | ≤1e−2 | ≤1e−2 | ≤5e−3 | ≤5e−3 | ≤5e−3 |

残る正RF値も同じ0.5%以内：全U′/U′e/U′m差最大1.168e−12、Rs差最大1.690e−6、
壁H二乗積分差最大2.211118e−3。全accelerating null/規約の一致を確認した。
この有限差を連続問題の誤差上界とは呼ばない。

追加fine解の解析対照も前回と同じP05 gateで確認した。

| 偏波/追加fine | 解析f差 | 解析E L2差 | 解析H L2差 | 解析G差 |
| --- | ---: | ---: | ---: | ---: |
| TE L3 | 2.488730e−5 | 6.771821e−4 | 6.108803e−5 | 6.903476e−7 |
| TM L4 | 2.467804e−5 | 5.604844e−5 | 1.957747e−4 | 7.534796e−4 |

独立order10場energyと元RF差は最大2.513e−13、親制限座標の相対丸め上限は最大9.039e−15。
小さい代数/energy値を離散化誤差の根拠にせず、上の場/RF差と解析対照を別々に使う。
実行前後401製品hash不変、比較器/テストの実行版hashも保持。全handle終端、固定解除。
証拠は `out/p07-planar-curved-convergence-20261002/`。最終artifact/入口リンク/全123カード依存・
節IDの監査は`progress-audit.json`へ記録する。新FEMを監査のために再実行しない。

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python -m unittest -v test_planar_curved_convergence_reference
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python -m unittest -v test_planar_curved_convergence_reference.PlanarCurvedConvergenceReferenceTests.test_original_restriction_preserves_both_vector_fields_and_all_RF
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python scripts/validate_planar_curved_convergence.py --from-evidence out/p07-planar-curved-rf-20261002/circle-extended --source-audit out/p07-planar-curved-rf-20261002/progress-audit.json --extend-failing --out out/p07-planar-curved-convergence-20261002/circle-last-two-final
```

既存の出力名は証拠を指す。将来の再実行は未使用`--out`を指定する。
製品src・共有core・seed TMを変更しない検証器の追加で、seed/full validate/hosted CIは未実行。
native保存・Project/CLI/worker/GUIの受入はP08、一般曲線比較/追跡/調整はP09で未接続。
新しい外部資料/依存/legacy資産参照はない。既存自作P2・Gauss・元Domain細分と、
P05/P07のR39/R40に基づく独立円解析対照を継続利用する。

次は同じ初期Domainから生成する独立A/B内部meshの全元場/全RF比較。
最後二求積次数≤1e−8、N16/32/64真形状への幾何と十分細かい各FEM、
楕円/再入角の二尺度収束も未確認であり、P07/原互換親/全goalは継続する。
