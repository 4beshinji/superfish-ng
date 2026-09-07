# N01: 直線三角形上のP2スカラーTM空間

2026-09-08仕様。物理はPHYSICS.mdのu=Hphi/r弱形式を維持する。
形状写像はアフィンなままであり、P2導入で円弧境界そのものが曲線要素になるわけではない。
P1の公開solve・入力・保存・数値結果は維持する。

## 自由度・組立

三角形の局所順は頂点0/1/2、辺01/12/20の中点。重心座標Liに対し
頂点基底Li(2Li−1)、辺基底4LiLjを用いる。隣接要素は同じ辺中点自由度を共有する。
元のMeshを変えず、QuadraticSpaceにmesh、dof_points、cell_dofs、boundary_dofs、axis_dofsを保持する。
cell_dofsは6列、boundary_dofsは端点2個と中点の3列。dof_pointsは(r,z)[m]。

Kij=∫r[(2Ni+r∂rNi)(2Nj+r∂rNj)+r²∂zNi∂zNj] drdz、Mij=∫r³NiNj drdz。
P2の剛性は5次、質量は7次。Duffy変換後の次数を含め、5×5 Gaussで両者を厳密積分する。
P1の4×4積分経路は変更しない。軸上でuを0にせず、軸の中点自由度も残す。
磁気対称境界だけで端点と中点のuを0にする。PEC/電気対称は従来の自然条件。

## 解契約と公開範囲

high_order.solve_p2(case, mesh_data=None)は開発用の実FEM固有値計算API。
既存と同じ対称一般化固有値ソルバー、残差基準、質量正規化・ピークphasor U[J]を使う。
Solution.meshは元の3頂点メッシュ、uは全P2自由度×モード、element_order=2、spaceはQuadraticSpace。
P1はelement_order=1、space=Noneを既定とし、既存の構築コードを維持する。

N02の場復元・RF・保存・sampling・鏡映・表示が未完の間、P2をCase/CLIの設定へ追加しない。
P1専用quantities/cell_fields/save_run/reflect_solutionへP2解を渡すと明示的に拒否する。
FieldSamplerも節点数と係数行数の不一致を拒否し、中点係数を黙って捨てない。
高次のRF計算が完成したとは表示しない。

## 独立検証

1. Kronecker性、分割の和1、勾配の和0、共有辺中点と番号付け。
2. 単位三角形の単項式u=r^a z^b（a+b≤2）の全組合せでK/M二次形式を階乗積分と比較。
   ∫r^p z^q=p!q!/(p+q+2)!。質量の7次項まで検査し、別数値quadratureを答えにしない。
3. 行列対称性、正定値、P1をP2へ正確に埋め込んだときのK/M一致。
4. 円筒の複数モード・細分でBessel固有周波数へ収束。16段階で相対誤差1e-5未満、
   8→16で誤差比0.2未満を目標とし、同じ元メッシュのP1より小さい誤差を要求する。
5. 磁気対称の辺中点も拘束、軸上自由度は残す。質量内積正規化・直交性・自由行残差を別検査。
6. 長さs倍でK→s³K、M→s⁵M、f→f/s。節点番号変更で同じ固有値。

標準unittest/validateの既存f/RF差を確認する。周波数の改善をRF/表面精度の証拠にしない。
本実装の根拠は既存の弱形式と一般のLagrange多項式・単項式積分からの独立導出。
新規の外部コード・ソルバー・依存は使わない。

## N01.I/V受入 — 2026-09-08

`high_order.py`、`solver._solve`、7件の`test_quadratic_elements.py`で上記を実装・検証。
テストを先に追加した時点では未実装モジュールにより6件エラー。実装後に全件合格し、
追加の番号変更/周波数スケーリング検査も合格した。許容差は緩めていない。

再現（既存出力を保護するため新しい出力先を指定）:

```sh
OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/validate_quadratic.py --out out/quadratic-<unique-name>
OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/validate.py --out out/validation-<unique-name>
```

ローカル証拠は`out/quadratic-n01-accepted-20260908/quadratic.json`と
`out/validation-n01-accepted-20260908/validation.json`、いずれもPASS。
標準suiteは150件中148合格・2 skip。標準の円筒/成形セルのmode辞書全体とcase.jsonは
直前の`out/validation-r01-final-20260908`と一致し、既存周波数・RF量を維持した。

R=0.1 m、L=0.2 m、先頭3モードの周波数相対誤差:

| nr×nz | P2自由度 | 第1 | 第2 | 第3 |
|---|---:|---:|---:|---:|
| 4×8 | 153 | 5.139e-6 | 2.695e-5 | 2.791e-4 |
| 8×16 | 561 | 3.422e-7 | 1.928e-6 | 1.962e-5 |
| 16×32 | 2145 | 2.183e-8 | 1.276e-7 | 1.289e-6 |
| 32×64 | 8385 | 1.375e-9 | 8.179e-9 | 8.227e-8 |

同じ2145自由度のP1（32×64）の誤差は4.264e-6 / 1.197e-4 / 4.368e-4。
同じ基底メッシュでの比較も全4段階・全3モードでP2が改善。
実測時間はJSONに残すが、この小規模測定を普遍的性能保証としない。
磁気対称中点拘束、自由軸、質量直交性、独立単項式積分、番号変更、寸法3倍も合格。
N01は受入完了。N02の高次場/RF/保存・表示、N04の適応誤差推定は未完であり、
K06と製品高次要素全体の完了ではない。
