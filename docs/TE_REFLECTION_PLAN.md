# TE鏡映の後続契約

後続追補（2026-09-09）：[鏡映TEの元半領域収束比較](TE_REFLECTED_CONVERGENCE_PLAN.md)を同じ元物理/同じ対称条件に限定して接続した。以下の当時の未対応記録より、この追補を優先する。鏡映部分スペクトルの追跡も[同端条件円筒](TE_SECTOR_TRACKING_PLAN.md)に限定して接続した。

## 最終受入 — 2026-09-09

基準be212b7。標準17381・最終数値照合4175とも終了0。790件中788合格・2skip（unittest1193.336秒、command1193.711秒）。TM seed9モード19量の周波数差0、RF/エネルギー最大相対差8.882e-16、旧通常TE版2/3保存7件のRF差0。標準・直線/球形独立・GUI保存照合・改変/worker検証・固定時/終了後464対象hashが一致し、Chrome実装hashも一致。証拠はout/validation-te-reflection-20260909のtests.log/command.log/validation.json/source-fixed.json/verify_completion.py/comparison.log/seed_regression.json。

直線16独立FEM、球形両尺度/両対称4FEM、CLI/API6FEM、Chrome6操作/3FEM、GUI元条件/全プローブ/取込後再実行3FEM、実worker中止/完了/再起動、元係数/周波数改変・コピー中変更拒否を確認した。CLI初回の全source snapshotはGUI表示修正前のため、最終GUI/CLI係数一致と最終source照合を別に記録する。球形level3のG不合格とGUI注意書き消失の初回不合格は保持。

鏡映部分スペクトルの追跡/収束比較は製品では拒否する。次工程は[元半領域による鏡映TE収束比較](TE_REFLECTED_CONVERGENCE_PLAN.md)。その候補検証は今回の製品受入に含めない。親8受入/9進行中/15他/1候補=33の集計は維持し、全計画は継続する。以下の実行中・未接続という記述は当時の経過で、現在状態は本節を優先する。

2026-09-09。TE収束Studyの標準検証待機中に確認した後続工程。TE鏡映API・専用native・Project/Job・GUI表示を接続し、以下の範囲で限定受入を完了。以下の設計と過去の未接続記録より最新進捗を優先する。

## 対応すべき物理

軸に垂直な一つの対称面で反射し、もう一端はPECとする。TEのEφ=r vは、
磁気対称面では偶対称、電気対称面では奇対称である。HrはEφと逆の符号、Hzは同じ符号になる。
既存TMのuへTEのvを別名付けしたり、TMの境界条件・符号をそのまま再利用してはならない。
磁場は既存のquadrature phasor規約を維持する。

半領域の振幅を変えずに全領域へ延長するので、蓄積エネルギーとPEC壁損失は2倍、
周波数・Q0・Gは不変。軸加速量/RQはN/A。モードの番号は対称性で抽出された部分スペクトルの順序であり、
全領域の周波数順位や連続した物理IDへ読み替えない。

## 実装上の確認点

- 開始時にはsymmetry.reflect_solutionとProject.reflect_fullが全TEを拒否していた。今回、専用TE実装へ接続した。
- 直線P1/P2は節点/セル向きと二次辺DOFの対応を保つ幾何変換と、TEの符号移送を分ける。
- 曲線は元の二次写像を反射する。境界再投影で別の形状へ変えない。
  curved_reflectionの現行符号/拘束はTM用なので、幾何と物理を明示的に区別する必要がある。
- TEの全領域行列を組み、自由DOFに対する残差とエネルギー/直交性を検査する。
  PEC境界の拘束反力を固有方程式の残差へ含めない。
- nativeには元の半領域/符号/写像/部分スペクトル/規格化を保存し、読込時に再構成・再検証する。
  全スペクトルを解き直したかのような順位表示や、別解の振幅合わせは行わない。
- API/CLI/Project/worker/GUIへ接続し、保存・再起動・改変拒否・場表示を確認する。

## 現時点の証拠と必要な受入

out/te-reflection-contract-20260909のverify.py/command.log/report.jsonは、現行TE鏡映の拒否と
既存R35の円筒解析2モードのEφ/Hr/Hz符号を確認した。新しいFEM計算は0件。
初回は解析的なゼロ点近傍の丸め差へ絶対SI許容差を適用して失敗した。
場成分ごとの振幅で無次元化し、同じ1e-12精度の符号検査で合格した。初回driver/logも保持。
これは解析契約の確認であり、鏡映実装の合格ではない。

製品受入には直線P1/P2・曲線P2、左右/両種対称の実FEMで、場の符号・境界拘束・
周波数/エネルギー/損失/G/規格化を独立に検証する。円筒・球形の解析解、全領域の独立FEM、
保存再検証を用い、残差だけで物理精度を保証しない。旧TM鏡映・通常TE・標準回帰を維持する。
新規資料・依存・legacy参照は採用していない。

## 直線離散場の予備検証

out/te-reflection-discrete-candidate-20260909/verify.py/command.log/report.jsonは終了0。P1/P2×磁気/電気対称の4実FEMを半領域で解き、右端鏡映メッシュへTE係数を直接移送した。全領域の自由方程式残差・電気エネルギー規格化/直交性、蓄積エネルギー/損失2倍、f/Q0/G不変、Eφ/Hr/Hzの鏡映符号がPASS。振幅合わせや全領域の再解はしていない。主ツリー460source不変。
この候補は右端の直線移送の確認であり、左端/曲線・一般形状・保存契約/部分スペクトル表示・Project/GUIの製品受入ではない。移送場を通常の全スペクトルnativeとして保存していない。

## 主ツリーの鏡映API接続中（基準be212b7）

`te_reflection.py`を追加し、symmetry.reflect_solutionからTEへ分岐。左右・両種対称の直線P1/P2と曲線P2で係数vを直接移送する。曲線は既存reflect_curved_spaceへ明示coefficient_parityを追加して固定写像だけを再利用し、既存TMの既定符号は維持した。TE拘束を反射後の空間へ設定し、自由DOF残差とEPS0による電気エネルギー規格化を検証する。

初期API段階ではTESolutionへreflection_source_caseを追加し、半領域の来歴を保持した。専用nativeができるまではsave_te_runがこの結果をディレクトリ作成前に拒否する。Project.reflect_fullもまだTEを拒否する。API接続を保存/CLI/GUIの完了と扱わない。

新test_te_reflection3件（内部で直線8条件/曲線4条件、誤Case・再鏡映・通常native保存拒否）は6788終了0、1.606秒PASS。既存TMを含む鏡映11件92484終了0、9.558秒PASS。out/te-reflection-development-20260909にログを保持。FEM数式/既存TM既定動作/物理精度許容差は変更しない。まだ未コミット。

## 専用nativeの実装方針

反射後の係数・幾何だけでは部分スペクトルの出所を再検証できない。新しい反射用結果版で、元半領域Caseと元mesh、元係数/周波数、反射後係数/幾何、side/parity/規格化/番号の意味を保存する。読込では半領域の行列と境界拘束・規格化を再検証し、その係数を鏡映して全係数・全幾何と照合する。再固有値計算や振幅調整はしない。通常TEの既存版2/3の内容と読込を維持する。

_namesと完了manifest、te_jobs/te_probe/保存追跡/収束比較のsnapshotが追加の元ファイルも含む必要がある。managed Projectは元半領域とreflect_fullを保持し、直接native取込も元meshと半領域へ戻してrerun可能にする。部分スペクトルの比較/追跡を未接続のまま黙認しない。GUIに全スペクトル順位ではない旨を表示する。保存後の再構成・改変/検証中変更拒否・CLI/Job/GUI・旧TM/TE・標準を検証して受入を確定する。

TE全体31116は45件19.720秒PASS、全実行終了。続いて公開APIのdocstringに部分スペクトル番号と元振幅を明記した（挙動は同じ）。

## 専用nativeとProject接続中

結果版4を鏡映TE専用とし、results.reflectionに元半領域Case・side/parity・mesh役割・部分スペクトル番号/規格化を明記。mesh.jsonは元半領域、source_fields.npzは元係数/周波数、fields.npzと曲線geometry.npzは反射後を保存する。完了manifestに元係数を必須追加。通常TE版2/3は保持する。

read_te_runは元Case/meshでFEM行列・拘束・規格化を再検証し、同じ反射APIで全Case/係数/曲線幾何を再構成して保存値と照合する。再固有値計算や振幅合わせはない。共通の_restore_fieldsへ通常TE読込の数値検査を移した。source_fieldsを_run_namesでprobe/Job/保存追跡/収束の前後snapshotにも含める。probe metadataにも部分スペクトルのreflectionを保持。

Project.reflect_fullのTE拒否を、対称面一つ/もう一端PECの検査に変更。Job検証は元半領域とreflect_fullを照合し、直接取込は元Case/meshとreflect_fullを保持する。GUI結果の要約とRF詳細に部分スペクトルを表示する。部分スペクトル自体の追跡/収束比較は未接続として拒否し、元半領域の比較を案内する。

69316終了0、native往復3件3.160秒PASS（直線8/曲線4条件）。追加Project/改変テストの25119はJobManagerを未対応with構文で使ったテスト誤りで終了1、初回log保持。closingで明示closeへ修正し85589終了0、5件3.375秒PASS。TE全体41861終了0、47件21.485秒PASS。out/te-reflection-development-20260909へ保持。全native/Project単体検証は終了、標準はまだ未開始。

CLI/API6FEMは74235実行中、out/te-reflection-cli-20260909/verify.py/command.log。P1磁気・P2電気・曲線磁気の3条件でsolve --reflect-full/専用read/API係数一致を検査する。case/project JSONもGUI検証用に生成。終了までソース変更を保留する。GUI実操作・独立物理解析・全保存改変/再起動・旧TM/TE/標準回帰・文書確定/commitは継続中。

CLI74235は終了0、3条件（P1磁気/P2電気/曲線磁気）・計6FEMで版4保存/read/API係数と周波数が完全一致。report.json/source_sha256保持。全実行終了、ソース固定は解除できる。次は生成済み3project JSONを用いたGUI実操作、独立解析/全domain比較、改変・再起動・標準回帰。

## 統合検証の進捗

直線の独立検証 `out/te-reflection-independent-20260909/report.json` はPASS。P1/P2×左右×両種対称の16実FEM（8半領域＋8全領域独立固有値計算）で、全領域中の順位・場・RFを照合した。P2は円筒Bessel解の周波数1e-4、G 0.5%、各場1%の基準も満たす。粗いP1は離散反射不変量の検証であり、解析精度合格とはしていない。

Chrome初回は描画完了時に部分スペクトルの注意が消える不具合を検出した。app.jsのplot完了時にも表示を保持し、`out/browser-te-reflection-fixed-20260909/report.json` の6操作（P1/P2/曲面の結果と元半領域復元）がPASS。外部リクエスト0、実装hash不変。スクリーンショットは補助記録で、数値/表示判定はDOMと保存結果の照合による。

`out/te-reflection-gui-independent-20260909/report.json` は3ケースのGUI/CLI係数一致、保存結果一致、全SIプローブ成分、復元Case、直接native取込後の再FEM一致、管理器再起動を検証した。最初の再起動試行は稼働中GUIとの同一workspaceロックで正しく拒否された。検証用GUIだけをSIGINTで停止して再試行しPASS。新しい完成FEMは3件。

`out/te-reflection-worker-20260909/report.json` は実workerの中止、別ジョブ完了、管理器再起動・保存再検証がPASS。中止した大規模計算を完成FEMには数えない。

球形の初回level3では電気対称ell=2のG誤差0.59614%が0.5%基準を超えた（周波数/各場は基準内）。`out/te-reflection-sphere-20260909` と `/tmp/te-reflection-sphere-20260909.log` に失敗を保持した。許容差を維持してlevel4へ細分し、別ディレクトリ `out/te-reflection-sphere-refined-20260909` で両尺度・両対称を再検証中。

標準検証は `out/validation-te-reflection-20260909`、ログ `/tmp/validation-te-reflection-20260909.log`、実行handle17381。全標準/最終数値回帰の完了までは受入完了としない。新規数学資料・依存・legacy参照なし。

球形level4の両尺度・両種対称4実FEMは終了0でPASS。周波数最大相対誤差2.49143e-5、G最大0.00143360、各場最大0.000879564。1/2の周波数、G不変、Qの√2倍、場の尺度−3/2乗も1e-8基準内。元level3の不合格は取り消さない。

`out/te-reflection-integrity-20260909/report.json` は元係数/元周波数改変（内側manifest更新済み）と取込コピー中のsource_fields変更を拒否し、変更した保存場をcompleteにしないことを確認。

## 利用例と保存範囲

```python
from superfish_ng import Case, solve
from superfish_ng.model import Model
from superfish_ng.symmetry import reflect_solution
from superfish_ng.io import save_run

half = Case(((0.0, 0.1), (0.1, 0.1)), nr=32, nz=48,
            modes=2, element_order=2, normalization_j=0.5,
            z_max="magnetic_symmetry", model=Model(polarization="te"))
full, fields = reflect_solution(half, solve(half))
save_run(full, fields, "out/te-reflection-example")  # 新しい出力先
```

CLIは、model.polarization=teと一つの対称端を含むCase JSONに対して `python -m superfish_ng solve half-te.json --reflect-full --out out/te-reflection-cli-example` を使う。GUIは元半領域のProjectを読み込み、鏡映を有効にして実行する。保存結果から条件を復元すると全領域Caseではなく元半領域へ戻る。

通常TE native版2/3は従来形式を維持する。鏡映の版4では `mesh.json` は元半領域メッシュ、`source_fields.npz` は元半領域係数と周波数、`fields.npz` は全領域へ移送した係数と元周波数を保存する。曲面の `geometry.npz` は反射後の固定二次写像である。`results.json` のreflectionに元Case/対称面/符号/部分スペクトル/規格化を記録し、全ファイルを完了manifestへ含める。読込では元半領域のFEM方程式・拘束・規格化を再検証してから全領域を再構成し、保存した係数/幾何/RFを照合する。再固有値計算や振幅合わせは行わない。

直線P2の独立解析検証で最大相対誤差はf 7.31831e-7、G 0.00275091、場0.00194748。独立全領域の最初の8固有値との対応は、元のモード1/2が磁気対称で全順位1/3、電気対称で2/5だった。番号を全順位に読み替えない表示の具体的な検証例である。
