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

99269は実終端PASSを観測した。受入結果と後続角TM二尺度の範囲は末尾の2026-10-07追記を参照する。
このbranchは他branchの生存中源を変更しない。尺度2/他形状/P07全体は未確認。

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=/tmp/superfish-ng-p07-boundary-refinement/src:/tmp/superfish-ng-p07-boundary-refinement/tests UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python -m unittest -v test_planar_curved_boundary_refinement test_planar_curved_refinement test_planar_curved_solver
OPENBLAS_NUM_THREADS=1 PYTHONPATH=/tmp/superfish-ng-p07-boundary-refinement/src UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python -u /tmp/superfish-ng-p07-boundary-refinement/scripts/extend_planar_curved_boundary.py --from-evidence out/p07-planar-curved-independent-20261007/ellipse-tm-s1 --uniform-failure out/p07-planar-curved-geometry-20261007/ellipse-tm-s1-L5 --bisection-failure out/p07-planar-curved-geometry-20261007/ellipse-tm-s1-extra-bisection --geometry-evidence out/p07-planar-geometry-bvh-20261007/results --out out/<new-unused-name>
```

## 来歴

既存自作P2 refinementの有理数評価・red/green templateと既存geometry/実FEM/元場を再利用する。
追加は明示的な境界cell mark選択だけで、適合性と保存不変量を独立検査した。
新外部資料、依存、legacyソース/バイナリ参照はない。


## 楕円TM境界B・角TE尺度2の終端と角TM残件（2026-10-07）

99269は2464.466秒PASS/終了0。元A3/A4/B4を物理再構築し、新境界Bの実FEMだけ一回追加した。
21760cell（旧B4は20480）、最終元map丸め7.028348e−14。B4→境界Bの対象f差最大2.1547e−8、
E差4.0985e−6、H差2.076318e−4、全RF差1.701740e−3。独立A4対BのRF差最大5.874163e−5。
完全band/独立energy・実壁積分も原gateでPASSし、楕円TM尺度1 A4/境界Bを受入した。
元399製品不変・geometry/refinement二変更、前後401分離製品/使用10validator/全元artifact不変。
別終端auditと全12artifact snapshotを保持。楕円二尺度の両偏波は各固定FEM条件を満たした。

角TE尺度2の保存済みB5復旧43214も3891.121秒PASS/終了0、新FEM0。
元終了143の原因は依然未確定。A3/B4/B5を全元chart/nativeから再構築し、全係数/周波数bitwiseと
元A3/B4全RF完全一致を確認した。対象B4→B5のf差1.101088e−5、E差4.222931e−3、
H差1.208029e−4、RF差3.629551e−5、独立A3対B5 RF差3.721745e−6。
完全band/独立積分もPASSしA3/B5を受入、角TE両尺度の固定FEM条件を満たした。
400旧製品不変・geometry一変更、前後401分離製品/使用10validatorと元39artifact不変。
復旧出力全8artifactのsnapshot/終端auditを保持し、保存済みFEMを再solveしない。

角TM混合細分50414/27391は終了1、7130.991/7129.920秒。各新3実FEMでAの混合細分は受入したが、
Bの第3対象群は最後二水準RF差5.514924e−3（0.551492%）で0.5%gate未達。
対象第1/2群RF差4.502693e−3/4.409091e−3、全f/E/Hと独立A/B（RF最大2.182286e−3）はPASS。
全401製品/使用10validator/元22artifact不変、各全21artifact snapshotと実終端auditを保持する。
B/角TM/P07を受入せず、既存境界patternで各尺度の保存Bへ局所細分を一回だけ追加する。
新driver `extend_planar_curved_corner_boundary.py` の全source/終端/raw preflightは二尺度PASS。
元accepted Aと最終Bを全chart/native/RFから物理再構築し、再FEMせず、新境界Bだけ各一実FEMを検証する。
boundary branch401製品/使用10validatorをhandle37232/67404の終端まで固定する。
出力 `out/p07-planar-boundary-refinement-20261007/corner-tm-s{1,2}-boundary/` と同名log。
1e8 geometry予算・512ε元map丸め・f/E/H/RF許容値・完全guard・独立積分は全て維持する。

上記終端四件の限定監査は新FEM/unit/物理再構築0。全前後hashと数値gateを照合し、受入を
証明済み形状/偏波/尺度に限定する。元円独立mesh38783、N64 TM四件、全P07とP08/P09は継続する。
