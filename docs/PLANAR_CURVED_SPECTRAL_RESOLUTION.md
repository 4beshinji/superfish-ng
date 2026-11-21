# 平面曲線の有限細分スペクトルguard

2026-10-07、P09のguard leaf。P09はIN_PROGRESS。
[元E/H内積](PLANAR_CURVED_FIELD_COMPARISON.md)とは別に、元曲線領域を細分したP2空間の
近傍スペクトルを診断する。元係数/周波数を置き換えず、細分解のrank・連続固有値・個別IDは推定しない。

`planar_curved_spectral_resolution.py` の `planar_curved_spectral_resolution` は、
元解の最低正帯/幾何/K/Mを再検証し、元の全二次写像をuniform四分割する。
外周を真円/楕円へ投影しない。明示 `binary64_roundoff` 方針と局所512ε上界を保存し、
[完全比較分割](PLANAR_CURVED_COMPARISON.md)で全セル/PEC被覆を再確認する。
元P2多項式のnodal制限をprolongationで移す。これは細分空間の診断ベクトルで、別の固有解ではない。
TMは全新PEC節点の零値を検査し、TEは細分operatorに定数静的核を保持する。
元/細分のscalar mass norm差を1e-8以内とし、元場の振幅を再規格化しない。

shift s=1/元二次xy面積、T=(K+sM)⁻¹M、μ=1/(元λ+s)。
細分ベクトルvのδ=||Tv-μv||M/||v||Mは、厳密演算なら有限operatorのスペクトルへの距離を与える。
浮動演算では線形solve残差1e-10を検査し、δに1e-10μの明示paddingを足して周波数区間を報告する。
上端が無限ならnull、TE区間下端が0なら定数核到達としてUNVERIFIED。
報告区間は少なくとも一つの近傍有限固有値を診断するもので、rankの分離・認証enclosure・
連続問題誤差・surface peak・mode identityの保証ではない。製品は細分固有値solveをしない。

面積求積は標準min(32,max(16,元Case次数+4))、明示4〜32。
本区間はその次数で組み立てた有限K/Mに対する診断であり、求積の連続精度を別途保証しない。
元scalar massと実E/H求積のゲートは別で、元E/Hの受入には先行比較の検査も必要。
全体予算は細分セル250,000、細分native DOF250,000、比較pair2,000,000、
細分面積求積点2,000,000。面積点予算は細分組立のみを数え、元解の再検証を含めない。
T元セルなら四分割は4T、native節点はN+2E+3T（Eは元corner edge数）、比較pairは10T、
面積点は4T×次数²。全て細分前に検査し、予算不足では部分細分へ進まない。
Domain幾何検証は元Caseの明示budgetを保持し、whole-P2 Bernstein bbox最大径が減ることも検査する。

## 独立対照と限定検査

最初に実TE/TM楕円の細分operatorを別のSciPy dense generalized eighで解く検査を作成し、
API不在のModuleNotFoundErrorを `spectral-baseline.log` に保存した。元数値回帰の失敗ではない。
独立dense spectrum（TE定数核を別確認/除去）が報告区間に入ることを各元modeで確認した。
二尺度・90度回転でf/区間×1/2、inverse相対残差不変、shift×1/4を照合する。
全元係数/周波数byte不変、元二次外周への制限、厳密被覆、scalar mass差、
全四予算の細分前停止と元解改変/strict拒否を分けて確認した。合成楕円を測定構造とは扱わない。

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-ng-uv-cache \
uv run --no-sync python -m unittest -v \
test_planar_curved_spectral_resolution test_planar_curved_refinement test_planar_tracking_fields
```

新4＋関連6、10件3.689秒PASS（終了0）。rawは
`out/p09-planar-curved-comparison-20261007/spectral-selected-tests.log`。
`spectral-acceptance.json` に初回FAIL/成功/実装/test hashと基準4c95f1bの元405製品不変を記録した。
新製品は専用guard1モジュール。曲線/seed kernelは無変更。
今回のunit内の元実FEM/dense有限対照を実行し、full/seed/GUI/大型validatorは実行していない。
既存自作の二次制限・nodal prolongation・xy面積組立・完全比較分割を再利用し、
shifted inverseの自共役残差関係と尺度則を独立導出した。新外部資料/依存/legacy参照なし。
次は元E/H双方の割当、有限区間の群/guard越境、曖昧停止を使う追跡核。
個別ID回復、円/非円形の両調整周波数gate、全元場保存/所有再開/GUIは後続P09の必須範囲。
