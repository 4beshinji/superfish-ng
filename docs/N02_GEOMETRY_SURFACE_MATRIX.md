# N02：保存3×3行列の幾何・場・求積・ピークを分けて評価する

2026-10-07。N01の完全CaseとN02の入力来歴・元場比較に、保存された
幾何3×固定幾何FEM3の数値集約を追加する。原カードの受入条件は、
故意のピーク未収束・場不一致・幾何未確認を合格させず、元楕円の成功判定を
保持し、NGの自己出力を独立物理参照にしないことである。
親G03/N03、原123カードと互換32要件、全goalの範囲は維持する。

## 入力と保存

[geometry_surface_matrix.py](../src/superfish_ng/geometry_surface_matrix.py) の
`build_geometry_surface_matrix` は保存nativeだけを読む。新しい固有値問題は解かない。
版1要求は次の四項目を持ち、未知キーを拒否する。

| 項目 | 内容 |
|---|---|
| schema_version | 1 |
| document_type | geometry_surface_matrix_request |
| plan_request | [厳密なN01計画要求](N02_GEOMETRY_SURFACE_PLAN.md)、完全な一Caseを選択 |
| runs | 三行×三列のnativeディレクトリ。未計算は明示null。結果の重複使用を拒否 |

全九点の完全Caseを計画と照合する。幾何ごとに元source mesh・全Caseを保持し、
細分は一様0/1/2、局所履歴なしを要求する。全点で解析形状・物理・単位・RF規約が
同じでなければ拒否する。read_solutionで元固有対・規格化・RFを再検証する。
completion所有ファイル全byteとmarker、全製品Python源、計画/参照を前後でSHA照合する。
保存は排他書込、読込は全元結果から再構築し報告全体の完全一致を要求する。

版2は元単一モード楕円専用の互換再生である。document_typeは
historical_ellipse_surface_matrix_request、archive_reportはpath/sha256を持つ。
元G03報告のSHA a025a9b0974bce2deec421032957fdd317733330b4fa7fdba1ce496eda48f0e2
だけを受け付け、その九点・元P2/次数12/単一モードを変更しない。
この結果を新三モードCaseや独立Maxwell照合へ昇格しない。

CLI：

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src UV_CACHE_DIR=/tmp/superfish-ng-uv-cache \
  uv run --no-sync python scripts/validate_geometry_surface_convergence.py \
  --matrix-request request.json --out out/<未使用の名前>
```

PASSは終了0、FAILは1、UNVERIFIED/SINGULAR_GEOMETRYは3。
完成した失敗/未確認報告も保存する。catalog計画経路・元archive経路は保持する。
N03が実精度系列を計算し、この要求へ元結果を渡す。

## 別々の数値条件

[geometry_surface_numerics.py](../src/superfish_ng/geometry_surface_numerics.py) は
既存の公開数学による独立診断を再利用する。科学ソルバー、RF定義、既存許容差は変更しない。

| 条件 | 判定と限界 |
|---|---|
| 幾何 | 元粗いP2境界の全辺に解析補間剰余＋140桁節点誤差。面積/回転体積は独立解析形状と比較。三誤差が二区間とも減少し、最終面積/体積差各1e-5未満 |
| 固定幾何 | 全二次境界の一致、面積/体積保存2e-12、真の親子Rayleigh–Ritz順位の非増加1e-10。モードIDの順位と変分原理の順位を混同しない |
| FEM/幾何の五量 | 各幾何の連続二FEM変化と、最細FEM間の連続二幾何変化。f1e-4、加速器R/QとG .005、Epk/EaccとBpk/Eacc .01 |
| ピーク | 保存離散上下界から外向き比区間を作り、Fractionで最悪区間差を計算。同じ推定値でも広い区間は未収束。欠測/零Eaccはnull/UNVERIFIED |
| 元場 | 元Hφからの単一符号をEr/Ezへ適用し、振幅を合わせない。全guard個別IDが確認できてからtargetを抽出。固定P2はN01のorder10強い追跡を追加 |
| 求積 | 全九点の同じ保存係数/周波数/規格化で体積12/16/24と壁8/16。K/M、Rayleigh比、U、R/Q、G、壁損失の差1e-8を別記録。新固有値求解0 |
| 鋭角 | SINGULAR_GEOMETRYを表示し、有限ピークの二量を要求しない。残り三量と場/幾何/求積のnumerical_statusを別に残す |
| 独立物理 | 原計画の参照来歴を保持するが、この集約だけで物理精度を受入しない。physical_error_bound=null、physical_acceptance_status=UNVERIFIED |

求積用K/Mの高次数組立でnative係数を再規格化しない。Rayleigh診断の一時係数尺度は
商の評価だけに使い、保存解を変更しない。離散ピーク区間を連続Maxwell問題の誤差上界と呼ばない。
全域被覆は元場工程と同様に保証しておらず、有限sample/欠測を報告内に保持する。

元楕円互換欄は、元五量区間・六FEM変化・二幾何変化、八つの元Study報告、
最細三点の元12/16求積条件、元固定/全体ゲートの完全一致を要求する。
新24次・全九点求積条件は別欄であり、元成功の意味を後から変更しない。

## 検証証拠

raw：out/n02-surface-matrix-20261007/、集約証拠はacceptance.json。全handleは終端。
新module未実装のbaseline、初回保存CLIの参照ディレクトリ指定不一致の検査側FAILを保持する。
後者はreference_directoryを明示して同じ入力に修正し、その一件だけ再検査した。
終端receiptの初回SHAキー誤記もreceipt-first-key-error.logへ記録し、
実スキーマのexpected_sha256/actual_sha256を読んで照合を修正した。FEM/求積は再実行しない。

新六不変量テストは2.215秒、終了0。五形状のmapped面積・体積をGauss3の独立Green境界積分と
照合し、境界midpoint変位を検出した。ピーク区間の各量/全区間、場・幾何未確認、
Ritz/求積不足が別条件で失敗/未確認になる。小さい代数残差でこれらを上書きしない。
同じP2製造場の12/16/24・壁8/16を検査し、固有値求解呼出を禁止、元係数不変と両R/Qの係数2を確認した。
これは境界条件を満たす固有解の精度証拠ではない。

新保存四件の初回8.400秒は三成功・一検査側FAIL。修正一件5.320秒、終了0。
完全未知の九点、強いCase/shape/重複path/旧report SHA拒否、実装SHAの後変異、
排他保存・完全再生・報告改竄拒否・実CLI/API一致を確認する。
直接消費は旧surface/affineの六件0.028秒、終了0。既存catalog CLI一件2.245秒、終了0。
新10＋直接7の17個別unitを分割受入した。成功済み検査を件数更新のために再実行しない。

新粗い楕円の三モード九点は機能反例であり、N01の精度系列と区別する。
chord .008/.004/.002、FEM各0/1/2、元二点を検査再利用・七点新規計算。
全rowのsource meshを保持し、保存nativeを再読込してから集約する。
費用・未収束/追跡未確認を消さず、精度達成を主張しない。
実行243.639秒、集約237.887秒、終了0。全九点のtarget/guard2/guard3の個別IDを保持し、
六つの固定FEM場・二つの幾何場、全九求積、固定面積/体積・全P2辺・Ritzは成立した。
それでも各幾何の最初のFEM区間はR/Q変化2.538〜3.099%、Bpk比1.590〜1.704%で未達。
二番目のFEM区間がすべて達成でも、連続二区間条件により全体FAILとなる。
幾何の五量二変化と最終面積/体積条件もFAILとして保存する。

元楕円九点は保存再読込のみで新FEM0。独立参照は未確認のまま保持する。
391.579秒、終了0、全体PASS。元五量区間・全八変化・八場報告・最細三点の元求積・
元ゲートが完全一致した。新24次/全九点の求積、全境界と独立momentもPASS。
元reportと九点のcompletion所有byteは不変である。
新seed/full/legacy/Hosted CIは実行しない。影響は読取専用の数値集約とCLIであり、
種子の弱形式・固有値求解・RF核を変更していない。

元1194 Python源の変更はvalidator CLI一つだけで、元六helperとarchive数値bodyはAST一致。
新二module/一testを加え1197源を実行前後で固定した。旧参照四reportもSHA一致を保持する。
新依存・外部取得・legacy参照はない。AGM/Taylor/補間剰余と元量区間/求積式は本実装の
公開数学に基づく既存validatorから再利用した。独立Green境界積分は比較用に別式で実装した。

## 原カードの受入

| N02原条件 | 証拠 |
|---|---|
| 新合成Caseを入力指定 | 版1のSHA付き計画・完全Case九点照合。全五形状の独立境界/moment、粗い楕円三モード九点の実保存集約 |
| 幾何/FEM/求積/元場/ピークを別報告 | 各ゲート・二連続変化・全上下界・元sample/欠測・個別ID・同一場求積を保持 |
| 未収束/不一致/幾何未確認を失敗させる | 新不変量反例、前場工程の実振幅/直交/欠測/零軸反例、粗いnative九点の正しいFAIL、未計算九点UNVERIFIED |
| 元楕円成功判定と一致 | SHA固定の元九nativeから原量/場/求積/ゲート完全一致、全体PASS、新FEM0 |
| 自作FEMを独立参照に使わない | 入力工程の自己参照拒否、historical診断の別来歴、全集約の物理受入UNVERIFIED/error_bound=null |

以上により**N02 DONE**。N01の各滑らかな精度系列の実行・両側独立照合は
次のN03である。N02の診断器受入をN03/G03の物理精度受入と呼ばない。
原123カードは70 DONE/2 IN_PROGRESS（H17、C07-planar）/51 PLANNED。
全goalと原互換32要件は継続する。
