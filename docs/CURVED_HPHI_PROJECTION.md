# 曲線Hφのscalar質量射影（H13-bの途中段階）

`curved_hphi_mass_coupling`と`project_curved_hphi_coefficients`は、元の二次幾何上のP1/P2 scalar空間を比較する。正半径qの測度は`dr dz/r`、軸接続uは`r³ dr dz`。2π倍が全回転体Hφ内積となる。全穴・軸・全native係数の対応には[H11比較領域](CURVED_HPHI_COMPARISON.md)を使い、丸めた細分は明示版2だけで扱う。

受入範囲は質量結合と直交射影まで。有限比較スペクトル、永続ID、E/H部分空間追跡、調整、保存/GUIは未実装で、H13-bと親H13は完了していない。

## 数値契約

自己質量はそれぞれの元native空間から再構築する。交差質量は共通参照分割上で両側のscalar質量密度の平方根を掛けて積分する。物理Hφの固定円筒成分と各側の実体積に由来するL2輸送で、Maxwell変換や周波数補正ではない。

両自己積分と交差積分は宣言求積次数+4/+8を比較し、正規化差1e-10以内を要求する。自己積分と元質量の差も1e-8以内を要求する。軸DOF・qの定数零空間を除去しない。幾何被覆/丸め診断も結果に保存する。

射影は`M_current b = C.T a`を解く。損失は場の差の二乗を直接積分し、さらに次数+2で再確認する。線形残差1e-10、Pythagoras欠損1e-8、非増大性、相対損失の求積差1e-10を検査する。零列は零損失として保持する。入力係数は変更せず、出力係数・質量行列は読取専用。固有値・RF・連続問題の誤差上界は返さない。

P1/P2、実有限係数、列数、DOF、共通分割数、pair数、求積点数を制限する。予算超過は`UNVERIFIED`例外、求積未分解は明示エラーとなり、省略した点で結果を生成しない。

## 独立不変量と検証記録

`out/h13-curved-projection-20260921/before.log`：非dyadic尺度0.7、2穴、既知shearに対して定数場の質量を独立矩形積分と照合後、未実装APIのimportで失敗（1件、1.638秒）。既存FEMの誤答を再現したものではなく、新API欠落のredである。

`after.log`：新5件、37.285秒、OK。q/uそれぞれについて以下を確認した。

- 独立質量モーメントと細分prolongationによる定数/r/z場の保存、零列。
- 粗視化したr³場の係数と非零損失を、独立した`P.T M_f P`の密行列解・質量代数で確認。
- 二倍尺度の密度因子（qは2⁻¹ᐟ²、uは2⁻⁵ᐟ²）と非一様shear。
- P1/P2の直線極限で既存直線質量結合と一致。
- 不正係数・次数・bool・DOF/求積点/列数予算の拒否。

新5件のtool session IDはコンテキスト圧縮で保持できなかったため、終了コードの証拠としては扱わない。ログのunittest正常終端と、その正確な実行コマンドに対応するプロセスが残っていないことを読み取り確認した。

`related.log`：関連3モジュールの16件、61.017秒、OK。tool sessionの終了コード0も確認した。成功した検査後の数値変更はない。

実行は`OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-uv-cache uv run --no-sync --python .venv/bin/python python -m unittest -v <modules>`。関連は`test_hphi_mass_projection test_curved_hphi_field_overlap test_curved_hphi_refinement`。seed TM/既存FEMは変更していないため全suite・seed検証は対象外。Hosted CI/GUI受入を主張しない。

既存の基底、共通分割、元FEM行列と独立合成shearを使用した。新外部資料・依存・legacy参照なし。次は曲線の明示細分比較空間での有限スペクトル診断を実装し、E/H追跡へ接続する。

2026-09-21追記：[有限比較スペクトル](CURVED_HPHI_SPECTRA.md)を追加・段階検証した。E/H部分空間追跡以降は引き続き未完了。

2026-09-21追記：[曲線E/H追跡とH13-b条件別監査](CURVED_HPHI_TRACKING.md)を完了した。曲線調整/履歴/操作のH13-c〜eと親H13は未完了。
