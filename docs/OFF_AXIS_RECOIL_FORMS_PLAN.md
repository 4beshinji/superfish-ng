# S03: 軸非接続の線形反跳材料と縮約磁束弱形式

2026-09-13 JST。次の限定課題。[実装記録](OFF_AXIS_RECOIL_FORMS.md)の弱形式API範囲で限定受入。

全r>0の直線MeridionalMeshでpsi=r*Aphi[Wb]を使い、Br=−psi_z/r、Bz=psi_r/rとH=nu(B−Brem)を解釈する。子午面の正値主軸mu_r・局所残留B・領域向きを明示し、phi結合なし/mu_phi=mu_rr/残留B_phi=0の3次元拡張を保存する。軸を含まないので子午面の向き/残留B二成分を制限しないが、軸への適用は明示的に拒否する。

Kij=2pi∫(1/r) (−Ni_z,Ni_r)ᵀnu(−Nj_z,Nj_r) dr dz[1/H]、fJ=2pi∫Jphi Ni dr dz[A]、frem=2pi∫(−Ni_z,Ni_r)ᵀnu Brem dr dz[A]を分離する。定数psiはAphi=C/r、B=0のgauge成分でありKの核と残留荷重総和0を保つ。C0=∫Bremᵀnu Brem dV/2[J]と二つの構成ポテンシャルの基準差を記録する。除かれた軸を貫く絶対磁束を補わない。

受入は材料2unit・弱形式3unitと独立72例/216多項式。P1/P2、穴0〜2、均一/二層/向き付き領域、幾何尺度/移動・mu倍率・源反転・所有順序/JSONを検証する。独立Gauss/Vandermonde積分と解析モーメントから1/r重みを確認し、P2のpsi=Brem_z*r²/2による一様軸B=Brem/H=0を照合する。幾何尺度sでKは1/s、fJはs²、fremはs、C0はs³（残留荷重の基底微分は1/s、子午面積はs²）。mu倍率mでK/frem/C0は1/m。内部求積は既存と同じ16対20を既定とし5e-12、独立行列/仕事/尺度則は1e-11。境界付き解・元場/保存と旧版モデル確認は後続。新規依存・外部資料・旧版実行なし。S03/全計画は未完。
