# P07：元二次mapを保つ適合境界細分

2026-10-07、分離branch `p07-boundary-refinement`、worktree `/tmp/superfish-ng-p07-boundary-refinement`。
mainと `p07-geometry-bvh` の実検証ソース固定を保つため、別checkoutで変更する。mainへ未統合。
全goal/P07は未完了。元円/楕円/角の他gateとP08/P09の必要性を維持する。

## 問題と受入条件

N16楕円TM尺度1は実A4が全gateを満たし、B3→B4はf/E/HがPASS、全RF差最大0.684177%で未達。
一様B5と追加二分は、元親mapの累積丸めが512ε/local extentを超え、FEM前に終了1。新FEM0。
予算の問題と丸めの問題を分け、512ε・RF0.5%・E/H1%・f1e−4を緩和しない。
壁RFは実壁Hの積分であり、境界側のFEM解像度を増やす適合細分を追加する。

受入条件は、全boundary cellをred細分し共有辺をgreen閉包する、内部の無関係cellを保持する、
全元parentを有理数で完全被覆し全二次mapを再投影せず制限する、
定数/線形場と粗いK/Mのenergy formsを保存する、既存全geometry予算・detJ・Green・丸め検査を保持する、の五点。
数値問題の受入はさらに新実BのB4→B差、独立A4対B差、完全guard、独立energy/壁積分で判断する。
境界細分機能のunit成功を楕円RFや全P07の成功とはしない。

## 変更と分割検証

`refine_planar_curved_domain` の明示的なpatternに `boundary` を追加する。
元boundary edgeを持つcellの三辺をmarkし、全cellの共有辺markから既存のred/green templateを適用する。
座標の正確なFraction parent評価、二次scalar transfer、boundary再接続、全Domain検査は従来コードを使う。
新しいinput physics、座標projection、solver補正、許容値変更はない。未知patternは明示拒否を維持する。

変更前は新独立test一件がunsupported patternでERROR、0.092秒/終了1。`before.log`を保持。
変更後は新3件と直接利用する旧細分3/元場solver7、計13件8.048秒PASS/終了0、handle59598。
新testは全boundary splitと内部cell保持、全parentのFraction完全被覆・全元二次node評価、面積/周長、
定数/線形場、粗いK/Mを実P2形式で引き戻したenergy一致、geometry予算拒否を独立検査する。
求積16のK/M pullbackは相対1e−10/1e−12、面積/周長は1e−12、map丸めは512εを維持する。
既存旧細分/元場/物理restore検査もPASS。全13件を文書更新のために繰り返さない。

ログはmainのignored `out/p07-planar-boundary-refinement-20261007/before.log` / `after.log`。
seed radial/共有r形式を変更せず、影響はCartesian曲線Domainの新patternに限定する。
seed/full validate/GUI/hosted CIは実行していない。

## 一回の新実B検証

新driver `scripts/extend_planar_curved_boundary.py`、構文検査PASS、実handle99269を開始。
出力mainのignored `out/p07-planar-boundary-refinement-20261007/ellipse-tm-s1-boundary/` と同名log。
元六FEMの完全prefix/全raw、元一様/二分の実終端1と新FEM0、全元8/9/10validatorを必須とする。
旧399製品不変・geometry/refinement二変更を明示し、geometryは実測済み分離版のhashと完全一致を必須とする。
A3/A4/B4を全元parent/nativeから物理再構築し、全係数/周波数bitwiseと全RF/metadata完全一致を確認する。
元Aの全gateを再検証した後、元B4の履歴 `bisection,uniform,uniform,uniform,boundary` を生成し、
最終累積元map丸め512εを検査して一回の新実FEMを解く。
B4→BとA4対Bは完全有理共通parent上で元E/H/全RFを直接比較し、完全bandと独立積分を別判断する。
同一A/B meshは拒否する。元artifactを上書きしない。

現在は実検証中。branch401製品/使用10validatorを99269終端まで固定し、timeoutで再起動しない。
このbranchは他branchの生存中源を変更しない。尺度2/他形状/P07全体は未確認。

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=/tmp/superfish-ng-p07-boundary-refinement/src:/tmp/superfish-ng-p07-boundary-refinement/tests UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python -m unittest -v test_planar_curved_boundary_refinement test_planar_curved_refinement test_planar_curved_solver
OPENBLAS_NUM_THREADS=1 PYTHONPATH=/tmp/superfish-ng-p07-boundary-refinement/src UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python -u /tmp/superfish-ng-p07-boundary-refinement/scripts/extend_planar_curved_boundary.py --from-evidence out/p07-planar-curved-independent-20261007/ellipse-tm-s1 --uniform-failure out/p07-planar-curved-geometry-20261007/ellipse-tm-s1-L5 --bisection-failure out/p07-planar-curved-geometry-20261007/ellipse-tm-s1-extra-bisection --geometry-evidence out/p07-planar-geometry-bvh-20261007/results --out out/<new-unused-name>
```

## 来歴

既存自作P2 refinementの有理数評価・red/green templateと既存geometry/実FEM/元場を再利用する。
追加は明示的な境界cell mark選択だけで、適合性と保存不変量を独立検査した。
新外部資料、依存、legacyソース/バイナリ参照はない。
