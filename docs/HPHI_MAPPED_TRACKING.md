# 非一様直線Hφの比較移送・射影・追跡（H09-b）

2026-09-21。[H09-aの全親被覆](HPHI_MAPPED_OVERLAP.md)を用いて、
明示写像の元E/H比較、q/u質量射影、保守的なモード対応を接続した。
調整要求・所有保存/CLI再開はH09-c、worker/GUIはH09-d。H09全体は未完了。

## 比較用移送の定義

前領域x=(r,z)、現領域y=F(x)=(R,Z)、D=det(dF/dx)>0とする。
全3Dの体積倍率は`Jv = D R/r`。比較空間を次で固定する。

```
T(E_r,E_z)(F(x)) = sqrt(r/(D R)) (E_r,E_z)(x)
T H_phi(F(x))     = sqrt(r/(D R)) H_phi(x)
```

円筒座標の成分ラベルを固定する。ベクトルを回転せず、共変/反変のMaxwell移送でもない。
これは領域の違う実FEM場を比較するための単位的L2写像であり、
変形後のPEC条件やMaxwell方程式を満たす場、連続モード枝を生成する操作ではない。
形状間の場の対応はこの明示規約に依存し、曖昧なら従来通りUNVERIFIEDとなる。

`Jv*(sqrt(1/Jv))²=1`なので、現領域の`2πR dR dZ`で積分した自己Gramは
元の物理E/H内積と一致する。逆写像はTの逆で、逆方向の交差Gramは順方向の転置になる。
F(x)=s xならD=s²、R=s r、係数s^(-3/2)となりH02と一致する。
一般変形に解析的な周波数倍率を仮定しない。

軸上quadrature点は使用しない。軸接続ではH08がr=0の対応を保持し、
開三角形内の正半径で上式を評価する。非有限・非正の係数は拒否する。

## scalar質量と射影

`H=r*u`と`H=q/r`から係数の移送を導く。

```
T_u u = (r/R)^(3/2) / sqrt(D) * u
T_q q = sqrt(R/(r D)) * q
```

現uの質量はR³、現qは1/Rで重み付けする。どちらも元質量内積を保存する。
cross_mass[i,j]=<T basis_old_i,basis_new_j>とし、現質量行列による直交射影を解く。
直接差積分とPythagoras整合、線形残差、二つの積分次数の差を別々に検査する。
射影場に固有周波数やRF量は付与しない。非一様写像で定数qが定数になるとは仮定しない。
静的核の扱いを変更せず、追跡の有限比較空間診断は各元物理領域で従来通り行う。

## APIと互換性

- `hphi_field_grams(..., geometry_mapping=mapping)`：元場を元要素重心座標で評価する。
  `previous_scale != 1`との同時指定は拒否。E/H別のPSD・元Gram再現・二次数差ゲートを保持する。
- `hphi_mass_coupling` / `project_hphi_coefficients`：同名の任意引数で明示対応を指定する。
- `track_mapped_hphi_modes(previous,current,request,mapping)`：requestから対象prefix・ID・controls・
  各元領域の比較メッシュを取得する。E/H一致・符号・guard・投影損失・有限スペクトルを従来と同じ閾値で検査する。
- `HphiGeometryMapping.to_dict/from_dict`：形式`superfish_ng_hphi_geometry_mapping`、版1、
  `kind=piecewise_affine`と両側の全制御メッシュを保存/strict再検証する。

既存のtracking版1 readerと同一領域・H02一様尺度の出力は保持する。
新しい結果形式は`superfish_ng_hphi_mapped_tracking_result`で、
`superfish_ng_hphi_mapped_comparison`版1の宣言に全写像と
`transport=unitary_fixed_cylindrical_components`を含む。
現段階でこの新結果を既存の保存履歴readerへ渡すことは対応していない。
CLI/worker/GUIによる新写像要求の受理と再生はH09-c/dで接続する。

## 独立検証と来歴

新規検査は次を分ける。

- 同軸TEMのf=c/(2L)と、異なる内外半径/長さでの独立Gauss半径積分によるE/H overlap。
- 単位エネルギーの自己E/H Gram、順逆交差Gram、一様尺度のH02 Gram一致。
- q/uの一様尺度係数則と射影誤差、非一様変形での非零射影損失と入れ子細分による減少。
- 非一様同軸寸法と、穴移動の独立分割/番号置換、軸接続の実FEM ID対応。
- Bessel径方向根krとL=π/krから構成したTEM/径方向モードの実縮退。
  二つの解析周波数との一致を確認し、個別IDを作らず集合だけを保持する。
- guardが対象帯域へかかると個別IDを全てnullにし、以前の集合を個別化しない。
- 対応判定前後の元FEM係数・周波数・RF量一致、strict宣言と不正入力拒否。

同軸の解析参照は既存`validate_coaxial.radial_roots`とMaxwell/TEM式を検証専用に使用した。
新規外部資料・追加依存・旧資産の参照はない。比較専用の密度補正は上の変数変換から独立導出した。
解析式を製品FEMの代替や周波数補正に使用していない。

## 実行記録

全コマンドは`OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-uv-cache
uv run --no-sync --python .venv/bin/python python -m unittest -v`に続けて実行した。
記録先は`out/h09-b-fields-20260921/`。

| 対象 | 結果 | ログ |
|---|---|---|
| `test_hphi_mapped_fields`初期5件 | PASS、7.329秒、終了0 | `fields-initial.log` |
| `test_hphi_mapped_tracking`初期2件 | PASS、20.688秒、終了0 | `tracking-initial.log` |
| 追加非一様射影1件＋同軸追跡の非一様寸法への変更1件 | PASS、11.647秒、終了0 | `nonuniform-additional.log` |
| 追加軸接続追跡＋解析縮退2件 | PASS、12.558秒、終了0 | `axis-degeneracy.log` |

初期の同軸追跡試験の寸法は一様尺度だったため、それだけでは非一様の証拠とせず、
長さ倍率を変えた上でその1件を再実行した。最終の新6場/射影＋4追跡＝10件は分割証拠であり、
一括実行の成功とは表現しない。

既存の利用先回帰は別記録とし、seed TMの経路は変更していない。

専用TEM入力は(a,b,L)=(0.0625,0.125,0.5) mと
(0.078125,0.171875,0.75) m、P2、nr=3/4、nz=12、3モード、U=1 J。
周波数の相対許容差4e-6、独立正規化overlapの絶対許容差2e-7を別に判定した。
縮退例は内外半径(0.0625,0.125) mと(0.078125,0.1640625) m、
P2 nr=nz=8、各L=π/kr。各側の低い二周波数をBessel参照に相対1e-4で比較した。
これらは製品のID/積分ゲートを緩和する設定ではなく、有限FEMの独立参照検査の許容差である。
元RF量は変更前後の全辞書一致を要求し、RFメッシュ収束の新規主張はしない。

呼出先の追加調査で確認した`hphi_convergence`の3件も25.704秒でPASS、終了0。
ログは`convergence-consumer.log`。既存のE/H・全RFの収束比較を含む。

既存利用先回帰は31件が459.244秒でPASS、終了0（`regression.log`）。対象:
`test_hphi_field_overlap test_hphi_mass_projection test_hphi_spectral_resolution
 test_hphi_tracking test_hphi_tracking_history test_hphi_tuning test_gui_hphi_tracking`。
既存GUIの実workerと所有コピー再実行を含むが、新写像のGUI受入ではない。
全検証プロセスは終了0で終端。新規10件の分割証拠、既存31件、追加収束3件を区別して保持する。
seed/full validatorと新写像のブラウザークリック列は今回の対象外。
