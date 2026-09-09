# 平面TE/TM遮断固有問題：入力・保存・CLI

[単純多角形の専用版2](PLANAR_POLYGON_RF.md)を追加し、標準835件と両尺度独立f/場/Gまで限定受入。以下は保持する矩形版1の契約。

矩形の真空PEC断面を、軸対称Caseとは別の `PlanarCase` で指定する。z方向の伝搬定数は0であり、有限長空洞の端板や伝搬モードを計算する契約ではない。物理式と独立検証の基準は[平面RF計画](PLANAR_RF_PLAN.md)。現時点の実装範囲は矩形P1/P2、TE/TM、API、専用nativeとCLI。一般断面・明示外部メッシュ・曲線・材料・対称面・Project/Job/GUIは未接続。

## 実行

```sh
python -m superfish_ng solve-planar examples/planar/te.json --out out/planar-te-example
python -m superfish_ng replay-planar out/planar-te-example
```

出力先は新しいディレクトリにする。TMは `examples/planar/tm.json` を使う。例のメッシュは操作例であり、8モード全ての物理精度を保証する値ではない。周波数・場・壁積分を別に細分検証する。

Pythonでは `from superfish_ng import PlanarCase, solve_planar` とする。`PlanarFieldSampler` と `planar_quantities` は `superfish_ng.planar`、`save_planar_run` と `read_planar_run` は `superfish_ng.planar_saved` にある。既存の `Case` / `solve` / `save_run` へ平面入力を渡さない。

## 入力の契約

`format="superfish_ng_planar_case"`、`schema_version=1`。name、model、geometry、mesh、rf、modesを必須にする。未知項目と重複JSONキーを拒否する。

- model：physics=`rf_eigenmode`、coordinates=`cartesian`、polarization=`te`または`tm`、propagation_constant_per_m=`0`、material=`vacuum`、boundary=`pec`。
- geometry：type=`rectangle`、width_m、height_m。領域は[0,width]×[0,height]。
- mesh：nx、ny（ともに2以上の整数）、element_order（1または2）。各長方形を対角線で二つの三角形へ分ける。
- rf：stored_energy_j_per_m、conductivity_s_per_m。ともに正の有限数。stored_energy_jの別名として受け入れない。
- modes：最小の正固有値からの個数。TEの定数零モードは含めない。大メッシュの全固有値要求は拒否する。

入力の具体例は上記のJSONファイルを参照する。axisymmetric Modelのazimuthal_indexや回転体の半径・対称タグはこの形式に存在しない。対応能力は `capabilities` の `planar_cutoff` に別項目として記録する。

## 場とRF量

ピークphasor exp(+iωt)。TMは実Ez、TEは実Hzを未知数とする。他方のベクトル場はquadrature成分で表し、x/y/zのE/H全成分についてrealとquadratureを明示する。磁場の単位はA/m、電場はV/m。未存在の成分は0で、TEの近似Neumann微分を数値上強制的に0へ上書きしない。

例えば `points.json` に `[[0.1,0.1],[0.2,0.1]]` を保存して、

```sh
python -m superfish_ng probe-planar out/planar-te-example --points points.json --mode 1 --out out/planar-probe.csv
```

と実行する。出力CSVはnativeディレクトリの外に置く。内部への出力は保存結果の完全性を守るため拒否する。新しいCSVの先頭列はx_m,y_m。`--mode` は1起点の正スペクトル順位であり、解析モード名ではない。要素境界で派生場が不連続な場合、矩形格子の決定的な所属規則で片側の場を返し、平滑化しない。Python側のmodeは0起点。

エネルギーはstored/electric/magnetic_energy_j_per_m、壁損失はwall_loss_w_per_m。側壁だけからQ0とGを計算し、有限長端板を加えない。二つの加速R/Q、Vacc、Eaccはnullで理由を保存する。小さい固有方程式残差やnative再検証成功は離散化精度を保証しない。

## native保存と再検証

専用ディレクトリはcase.json、mesh.npz、fields.npz、results.json、manifest.jsonの5ファイル。meshはxy座標・三角形・P2自由度とPEC辺の所属、fieldsは実未知数係数と周波数を保存する。resultsは専用format、入力、単位・位相・正スペクトル規約、代数残差と全RF量を含む。保存時は入力と係数を再検証してから新しいディレクトリへ書き、manifestを最後に公開する。

再読込では全ファイルのhash、Cartesianメッシュと境界の再構築、PEC拘束・TE定数零空間、規格化・質量直交・固有方程式、RF/規約を検査する。正スペクトルも再計算するため、ハッシュを更新した高位モードの差し替えを先頭モードとして受け入れない。固有ベクトルの成分を再計算した基底へ置換せず、保存した係数を検証して保持する。縮退空間内の基底は一意な物理ラベルではない。

検証中の元ファイル変更、余分/不足ファイル、symlinkファイル、重複した配列名、pickle配列、別物理の保存を拒否する。一般の旧版AF/SFO変換は含まない。
