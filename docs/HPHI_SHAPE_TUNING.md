# 非一様直線Hφの調整要求・所有保存・CLI（H09-c）

2026-09-21。Hφ調整要求版2に同軸寸法と明示頂点変位を追加する。
既存[版1](HPHI_TUNING.md)の一様尺度、二分判断、二つの周波数ゲート、元native保存は維持する。
場比較は[H09-b](HPHI_MAPPED_TRACKING.md)、幾何の全親被覆は[H09-a](HPHI_MAPPED_OVERLAP.md)。
新写像での実worker中止/GUIクリック列・再起動後復元は[H09-d](HPHI_SHAPE_TUNING_GUI.md)で受入済み。

## 要求版2

`format=superfish_ng_hphi_tune`、`schema_version=2`。
版1と同じ最上位キーを要求し、未知/欠落・非JSON型・bool数値・非有限値・重複キーを拒否する。
`project`は真空直線`CoaxialCase`/`HphiMeshCase`/`AxisHphiCase`に限定。
材料・曲線・追加物理をこの版へ混入しない。

| mapping.kind | parameter | 単位 | mappingの追加必須項目 |
|---|---|---|---|
| `coaxial_dimensions` | `inner_radius_m` / `outer_radius_m` / `length_m` | m | なし |
| `general_piecewise_affine` | `deformation` | 無次元 | `reference_value`, `displacements_rz_m`, `acceleration_policy` |

同軸は指定した一寸法だけを元Caseから置換する。内外半径の順序と全正値条件は各試行で確認する。
一般形状の式は各元頂点iについて次の通り。

```
p_i(value) = original_p_i + (value-reference_value)*displacements_rz_m[i]
```

`reference_value`とboundsは正で有限。変位の各成分は符号付きmで、元頂点ごとにr,zの2値を要求する。
省略頂点・自動対応・累積変形は使用しない。全元セルが区分アフィンの制御分割になる。
原メッシュの全境界節点を制御輪郭の明示頂点とし、元直線辺の途中から曲がる変位もその節点で表す。
黙って直線へ戻したり、丸め誤差を許容差で吸収したりしない。
これは直線折線形状法則であり、曲線CADや連続変形経路の保証ではない。

各候補は全外周・PEC穴・軸・正Jacobian・全域被覆を既存mesh readerとH08で検証する。
要求の両端と予算を出力予約前に検査し、二分中の各値と最終細分もFEM前に検査する。
両端が有効でも区間内全値の形状有効性は保証しない。無効な途中試行は例外/失敗記録となり、
周波数を採用せず、既存checkpointは保持する。空間・要素の予算超過は隠さない。

## 軸と細分

`acceleration_policy=transport_on_axis`を明示必須とする。
軸頂点のr変位は厳密に0。加速経路があれば端点と位相原点を対応軸辺上で移送し、betaを保持する。
元軸区間外の位相原点は外挿せず拒否する。経路がない正半径Caseへ加速軸を作らない。

最終細分は採用値で生成した未細分候補を親にする。同軸はnr/nzの倍化、明示メッシュは四分割。
比較写像は両値の未細分候補から構成し、現FEMが細分されても制御番号を取り違えない。
浮動小数点で正確な直線境界を構成できない入力は、既存の厳密幾何契約に従って拒否する。

## 判定・保存・操作

探索比較の親は初期試行、最終細分の親は採用候補。版2の非一様比較で周波数倍率は推測しない。
E/H両方のIDが全て確認された場合だけ、指定IDの実順位の元固有周波数を評価する。
縮退・guard・比較未解像では周波数/目標差をnullとして停止する。
目標差と採用/最終細分の周波数差は別判定し、RF収束や真の誤差上界を宣言しない。

checkpoint包絡版1を保持し、内側に要求版2と全形状法則を保存する。
`scope`は`coaxial_dimensions`または`general_piecewise_affine`で要求から再検証する。
再生は各元Project/native・hash・要求・全判断を再構成し、新しい候補をsolveしない。
再開は常に新出力へ全native/RFを所有コピーする。元出力を移動しても新出力で再生できる。

```sh
PYTHONPATH=src UV_CACHE_DIR=/tmp/superfish-uv-cache uv run --no-sync --python .venv/bin/python \
  python -m superfish_ng tune-hphi examples/hphi_tune_coaxial_length.json --out out/<new-name> --max-new-trials 2
# 同じ環境で:
# superfish-ng resume-tune-hphi out/<new-name>/checkpoint-002.json --out out/<another-new-name>
# superfish-ng replay-tune-hphi out/<another-new-name>/checkpoint-004.json
```

例は合成同軸の長さ0.5〜0.75 mを調整する。`<...>`は未使用の実パスへ置換する。
APIの`run_hphi_tune`結果は同軸パラメータ単位m、一般変形はdimensionlessと明示する。
GUIに流れる共有表示のパラメータ名・単位も要求から導出する。新規操作のGUI受入は別カード。

## 検証の設計

- 同軸長さはTEM `f=c/(2L)`、内外半径は既存独立Bessel根を参照して実二分探索する。
- 片側境界頂点の変位による面積/回転体積増分を三角形の独立式と比較する。
- 一般例は半径[1/32,1/8] m、長さ3/8 mから矩形PEC穴を除いた合成真空。
  z=L/3,2L/3の穴端で自然境界を満たす`q=cos(3πz/L)`を独立参照とする。
  軸方向伸長と半径方向の穴移動を同時に指定し、f=3c/(2L)と元q質量overlapを別判定する。
  試験だけでこの解析場を同定し、製品は指定IDと実FEMを使用する。
- 保存は実CLI開始/再開/再生、全コピーのbyte/hash一致、元出力移動、要求/形状法則/native改変拒否を検査する。
- 軸・穴・反転・不正項目・予算の拒否はsolve/出力前で確認する。

最初の一般例probeは補助スクリプトのCaseキー誤記で停止した（solver未実行）。
修正後の粗いメッシュ/5-ID要求はguardとの重なりによりUNVERIFIEDで停止した。
解析場は実順位4だったため、別要求で4-ID prefixとその上のguardを明示し、
元/最終の周波数差を確認できるよう元メッシュを細分した。許容差・判定式は維持した。
これらの予備結果を成功件数へ数えない。rawは`out/h09-c-tuning-20260921/`に保持する。

再現用専用validatorは`uv run --no-sync --python .venv/bin/python python
scripts/validate_hphi_shape_tuning.py --out out/<new-name>`（`OPENBLAS_NUM_THREADS=1`推奨）。
出力先は新規作成し、要求・全native・checkpoint・判断・独立比較のreport.jsonを保存する。

新規外部資料・依存・旧資産の参照なし。既存Bessel参照と真空TEM式、体積の独立式を検証専用に再利用した。
FEM/場/RF核とseed TM経路の変更はない。seed/full validatorは今回の対象外。

## 実行記録

unittestは`OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-uv-cache
uv run --no-sync --python .venv/bin/python python -m unittest -v`で実行した。
以下は新7件の分割証拠と既存18件を分けた記録である。

| 対象 | 結果 | `out/h09-c-tuning-20260921/`内のログ |
|---|---|---|
| `test_hphi_shape_tuning`初期4件 | PASS、26.826秒、終了0 | `initial.log` |
| 追加境界折曲げ1件 | PASS、1.253秒、終了0 | `boundary-bend.log` |
| 内/外半径の実二分とBessel参照1件（2探索） | PASS、27.620秒、終了0 | `radial-bisection.log` |
| `test_hphi_shape_tuning_saved`実CLI/所有保存1件 | PASS、96.367秒、終了0 | `coaxial-saved.log` |
| `test_hphi_tuning test_hphi_tuning_saved test_hphi_tuning_jobs test_gui_hphi_tuning` | 18件PASS、551.668秒、終了0 | `regression.log` |

共有表示の変更は`node --check src/superfish_ng/web/hphi.js`で構文確認した。
新要求版2での実worker中止/再開と実ブラウザーのクリック列はH09-dの別受入とする。

専用validatorは`out/h09-c-general-20260921/report.json`がPASS、プロセス終了0。
新4実FEMで、一般形状の両端・中点・最終細分を実行し、元要求を保持して所有再開した。
最大解析周波数相対誤差2.53404e-4、最終1.62859e-5、最小q質量overlap 0.9999999766。
最終f=1,128,648,810.903 Hz、目標差18,380.786 Hz、粗細差267,455.162 Hzで、
別々の1 MHzゲートを満たした。要求値/最終係数・全RFと所有コピーの再生、元出力移動、
形状法則の改変拒否を確認した。予備2FEMのUNVERIFIEDは別記録として保持する。
全検証プロセスは終端。H09-cの受入はAPI/所有保存/CLI範囲であり、次はH09-d。
