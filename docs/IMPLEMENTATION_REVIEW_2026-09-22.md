# 既存実装の横断レビュー — 2026-09-22

## 結論と対象

**最初に検証結果の来歴と検証環境を整え、その後に入力共通処理、所有保存/worker、
調整の決定処理、CLI/GUIの順で責務を分離する。物理別のFEMを一つの汎用solverへ統合する必要はない。**
科学的な検査と未対応条件の拒否は重要な資産である。一方、機能追加に伴い、共通処理が特定物理の
モジュールへ入り、非公開関数の横断利用と同形の保存処理が増えている。
ファイル数の削減より、修正の影響範囲を狭めることを目的とする。

- 対象基準：`a191b4e089da48808ab330b169fa4ad9ea3472bb`。開始時の作業ツリーはclean。
- 作業場所：`/home/sin/code/agent/reserch/superfish-ng`。原配置への移動は行わない。
- 対象：この独立実装の過去の蓄積を現行HEADで評価したもの。全コミットの逐次監査ではない。
- 手法：追跡対象ファイルのAST/依存/重複集計、代表経路のソース読解、既存検査の読解、
  非数値の限定再現。全関数の手動監査、数値正確性の全範囲再認証、性能測定は行っていない。
- 参照：README、PHYSICS、PROVENANCE、CODEX_HANDOFF、ARCHITECTURE、TESTING、
  CURRENT、B01台帳等の現行資料と、本リポジトリ内のソース/検査。
  旧ソース・旧バイナリ・ユーザー所有資料・外部サイトは参照していない。
- 成果物の範囲：[BACKLOGのREVIEW-01](BACKLOG.md)。製品コードと検証器は変更しない。
  修正と移行は別の[リファクタリング計画](REFACTORING_PLAN.md)で未着手として管理する。

`CURRENT.md`と新しい専用受入文書を過去の「次は」「未接続」より優先した。
例えば、直線Hφ比較が材料/曲線を拒否する実装は、専用の材料/曲線経路が存在するため、
製品全体の未実装とは判定していない。B04による現行入口の集約も既に実施済みとして扱う。

## 規模と依存の観測

集計の原本は[静的棚卸しJSON](reviews/2026-09-22-inventory.json)。行数は空行・コメントを含む。
`git ls-files`にある対象だけを読み、`out/`、環境、未追跡ファイルは集計しない。

| 対象 | ファイル数 | 行数/宣言数 |
| --- | ---: | ---: |
| 製品Python | 375 | 52,481行 |
| 製品JavaScript | 7 | 4,117行 |
| `tests/test_*.py` | 433 | 42,180行、`test_*`関数宣言2,099件 |
| Python scripts | 261 | 26,990行 |
| ブラウザー等の`.mjs` scripts | 65 | 17,206行 |
| `docs/**/*.md` | 473 | 50,444行 |
| `scripts/validate*.py` | 209 | 総合入口を含む。全てが総合検証で実行されるわけではない |

2,099はASTの宣言数であり、実行済み件数・合格数・subTest展開数ではない。
TESTINGの1,456件は明記された旧HEADの実測記録であり、この集計で上書きしない。

| 観測 | 値 | 解釈 |
| --- | ---: | --- |
| `cli.py:main` | 1,230行、依存先116モジュール | 構文定義と多数の実行経路が一つの関数に集まる |
| `gui.py:do_POST` | 391行 | HTTP認証/輸送と操作振分けが同じクラスに集まる |
| `web/app.js` | 3,053行 | 編集・追跡・調整・表示の共有状態の変更範囲が広い |
| 非公開名の直接import | 763箇所、222製品モジュール | `_canonical`等が事実上の共通APIになっている |
| 内部importの有向辺 | 2,347 | 同じ呼出元/依存先をまとめた静的集計 |
| 最大の強連結成分 | 281モジュール | 関数内importとTYPE_CHECKINGを含む依存の連結性 |
| 他のtest/scriptからのhelper import | 380箇所、222テストモジュール | ファイル名だけのテスト選択では影響先を落とし得る |

強連結成分は「互いに依存経路で到達できる集合」のこと。
この数をimport時の失敗件数や実行時の呼出経路とは解釈しない。動的importも解析していない。
また、1,000行を超える製品Pythonは`cli.py`の1本だけであり、全体が巨大ファイルに
集中しているわけではない。既存の細かな分割を残しつつ、分割間の依存方向を改善する。

集計手順は、追跡対象UTF-8ファイルの`splitlines()`、Pythonの`ast.parse/ast.walk`、
内部`ImportFrom`のグラフ化、Tarjan法による強連結成分抽出である。
重複は12行以上の関数について、docstringと位置情報を除いたAST本体が完全一致する組を抽出した。
引数・グローバル定数・呼出先の意味が同じとは限らないため、自動統合の根拠にはしない。
製品hashは、ソートした対象`.py/.js/.html/.css`ごとの`相対path + 空白 + SHA256 + 改行`を
連結し、さらにSHA256を取ったもの。棚卸しJSONに基準値を保存した。

## 確認した領域と維持すべき点

| 領域 | 読解した代表経路 | 評価と今回の限界 |
| --- | --- | --- |
| canonical TM、P1/P2/曲線/TEの入口 | `solver.py`、`fem.py`、`io.py`、`saved.py`、PHYSICS | 軸正則化、自由行残差、エネルギー規格化、専用経路の振分けを確認。今回は固有値を再計算していない |
| Hφ・材料・追跡 | `hphi_native.py`、`hphi_field_overlap.py`、`material_hphi_field_overlap.py`、`mode_tracking.py` | 元場の再検証、E/Hを別に扱う内積、材料重み、順位とIDの分離を維持すべき。全guard条件の再実行はしていない |
| 幾何・メッシュ | `mesh.py`、`certified_arcs.py`、関連import、`test_contour_mesh.py` | 有理数区間や境界/面積不変量は単純なfloat共通化の対象にしない。全conicアルゴリズムの正当性監査ではない |
| 静電・静磁・非線形 | `static_field_project.py`、`electrostatic_fem.py`、`planar_magnetostatic.py`、`off_axis_recoil.py`、`axis_bh.py`、`nonlinear_magnetic.py` | 専用Caseと構成則を保持。既存の製造解、界面、線形極限、真の接線の検査を確認。反復計算は未実行 |
| 調整・保存・実行 | `tuning.py`、`planar_tuning.py`、Hφ3系のtuning/jobs/saved、`jobs.py`、`completion.py` | 完了と途中保存、元入力と所有コピー、回復anchorと比較親を区別する設計は維持。重複と依存に改善余地 |
| 入力・公開操作 | `config.py`、`project.py`、`cli.py`、`gui.py`、`web/app.js` | 未対応キー/重複キー拒否、loopback/認証/操作制限を維持。全CLI/ブラウザー操作は再生していない |
| 検証・配布 | `scripts/validate.py`、CI、`scripts/package.py`、物理/保存/GUIの代表テスト | 独立場/RF検査と配布許可リストは資産。来歴と任意依存に問題を確認 |
| 現行仕様・履歴 | PHYSICS、ARCHITECTURE、TESTING、DEPENDENCIES、CURRENT等 | 日付付き履歴は保全する。現在形の入口と古い本文の境界には改善余地 |

具体的に残す検査は、[物理検査](../tests/test_physics.py)の周波数・Bessel場形状・RF・表面場の分離、
[材料場比較](../tests/test_material_hphi_field_overlap.py)の独立Gauss/Vandermonde再構成、
[モード追跡](../tests/test_mode_tracking.py)の順位交換・真の縮退・欠落方向の拒否である。
保存は[完了公開](../src/superfish_ng/io.py)の非置換hard linkと最後の完了マーカー、
[完了検証](../src/superfish_ng/completion.py)のファイル集合/hashを維持する。
これらを「重複テスト」「冗長な検証」として一括削除しない。

## 所見一覧

優先度「高」は次の広範な機能追加/共通変更より先に扱う候補、「中」は影響箇所の次回変更と
合わせる候補、「低」は測定条件が整ってから扱う候補。緊急の数値誤答を示す分類ではない。
「静的確認」はコードの制御/依存から確認した事実、「再現」は今回動かした限定条件、
「リスク」は将来の変更影響の評価を示す。

| ID | 優先度・確度 | 所見 | 対応計画 |
| --- | --- | --- | --- |
| F01 | 高・静的確認 | 総合validatorが実行後のソースhashだけで来歴を記録する | RF-01 |
| F02 | 高・条件付き再現 | CIの依存導入とGUIテストの必須依存が一致しない | RF-02 |
| F03 | 高・依存を確認、影響はリスク | 汎用の入力/JSON/来歴機能を物理・操作モジュールからimportする | RF-03 |
| F04 | 高・重複を確認、影響はリスク | Hφ3系の所有worker処理が複製されている | RF-04 |
| F05 | 中・依存を確認、影響はリスク | 物理共通の調整決定がTMのtuningモジュールに置かれる | RF-05 |
| F06 | 中・構造を確認、影響はリスク | CLI/HTTP/共有JSの入口に複数の責務が集中する | RF-06、RF-07 |
| F07 | 中・構造を確認、費用は過去の測定 | テストfixtureの横断importと層をまたぐ重い計算 | RF-08 |
| F08 | 中・静的確認 | 再現環境、現環境、導入手順が別々のまま | RF-02 |
| F09 | 中・静的確認 | 現在形のアーキテクチャ/物理説明にseed時点の範囲が残る | RF-09 |
| F10 | 低・呼出構造を確認、性能は未測定 | 逐次調整/完了検証で履歴全体の再検証が反復する | RF-10 |

### F01：総合検証の実行中変更を記録できない

根拠：[scripts/validate.py](../scripts/validate.py)の`main`、行40–85。
tests、convergence、seedとshapedの計算を終えた後で`fingerprints`を一度だけ作る。
`passed`には開始時/終了時のファイル集合・hash一致条件がない。
一方、[seminar_suite.py](../scripts/seminar_suite.py)は行201–203で実行前後を比較している。

途中で実装を変更すると、既にimportされたコードと後続subprocessのコードが異なっても、
最終状態だけを`source_sha256`として持つPASSを作り得る。
これは来歴の検出漏れであり、過去のPASSが実際に混在していたという証拠ではない。
今回、作業ツリーを途中改変する再現は行っていない。

対策は開始時と終了時の対象集合/hashを保存し、不一致なら総合受入不可にすること。
始終一致でも途中変更後の復元までは証明できないため、検証中のソース固定という運用も残す。
検証器の修正は構造整理とは別コミットにする。

### F02：任意依存なしのCI相当条件でGUIテストがエラーになる

根拠：[CI設定](../.github/workflows/ci.yml)の通常インストール`python -m pip install .`、
[pyproject.toml](../pyproject.toml)の`plot` extra、[gui.py](../src/superfish_ng/gui.py)の
`create_server`行86–92、[test_gui_hphi.py](../tests/test_gui_hphi.py)行67–70。
このHTTPテストは`PermissionError`だけをskipし、Matplotlib不在の`ValueError`を扱わない。

今回、`find_spec('matplotlib')`だけを`None`にする条件を注入し、既存テストを1件実行した。
結果は**1件実行、ERROR 1、skip 0**、`GUI plotting requires the plot extra`。
FEM実行とHTTP bindより前に停止した。仮想環境からパッケージを削除した検査ではなく、
クリーンCI全体を起動した検査でもない。Hosted CIが実際に失敗したとは主張しない。

推奨はcoreのみの利用契約と、`plot`を入れたGUI検証契約を分けること。
full受入環境には必要なextraを明示する。GUI検査を無条件skipする修正は受入れない。
再現コマンドは末尾に記載する。

### F03：共通機能の配置が依存を逆向きにする

根拠：`config.py:13–50`の`positive/integer/keys`は253モジュールがimportするconfig内にある。
同じconfigは`__post_init__`内でTEや幾何を読み、`model.py`とも相互に依存する。
`project.py:parse_json`は130モジュールから依存されるproject内にあり、Caseと結び付く。
`saved_mode_tracking.py:_canonical`は一般のJSON正規化に使われ、
`jobs.py:_implementation_hashes/_digest/_write_json`は物理別保存・調整から直接参照される。

具体例は[planar_tuning.py](../src/superfish_ng/planar_tuning.py)行22–26、
[hphi_tuning_jobs.py](../src/superfish_ng/hphi_tuning_jobs.py)行19–29。
`jobs → hphi_tuning_jobs → jobs`、`config → te → mesh → config`のような依存がある。
関数内importは現在の起動順を成立させるが、共通機能の責務を明確にはしない。

入力検査、JSON直列化、ファイル来歴を小さな下位モジュールへ移す。
ただし、ファイル来歴と物理的な再検証は別責務である。
型ヒント/Protocolは境界の説明に使い、物理差を消す共通`Solution`を先に導入しない。
非公開名を公開名へ一括置換するだけでは依存方向は直らない。

### F04：同じ所有保存ルールが3つのworkerで保守される

根拠：以下はdocstringを除くAST本体が一致する。

| 処理 | 直線Hφ | 曲線Hφ | 材料Hφ |
| --- | --- | --- | --- |
| `_snapshot` | `hphi_tuning_jobs.py:106` | `curved_hphi_tuning_jobs.py:112` | `material_hphi_tuning_jobs.py:112` |
| `_check_manifest_shape` | 同`:130` | 同`:136` | 同`:136` |
| tracking jobsの`_source` | `hphi_tracking_jobs.py:51` | `curved_hphi_tracking_jobs.py:50` | `material_hphi_tracking_jobs.py:50` |
| 履歴の`_verify_link` | 各`*_tracking_history.py:89` | 同 | 同 |

GUIの`_checkpoint_indices`も3系で一致する。
現在これらが食い違っていると断定する所見ではない。
一箇所の修正を他系へ反映する作業が必要になり、改変拒否や再開時の所有ルールが
物理追加に伴って分岐することがリスクである。

共有候補は宣言済みファイル集合、symlink拒否、所有コピー、checkpoint番号、状態/manifest整合。
共有しないものはnative場の復元、材料界面、曲線幾何、E/Hの物理再生である。
既存の入力名/format/kind/保存schemaを保つ明示アダプターから段階的に呼ぶ。

### F05：共通の二分決定を利用するためにTMの操作層へ依存する

根拠：[tuning.py](../src/superfish_ng/tuning.py)行147–180の`_decision`は、
planar、直線Hφ、曲線Hφ、材料Hφからimportされる。
同モジュールはProject、Study、jobs、保存追跡、TE/曲線調整と接続し、
`_decision`自体も`base_request`で回復要求を変換する。

共有したいのは、確認済み試行に対するbracket更新・停止・最終細分要求という決定である。
物理ごとの前処理をアダプターに残し、決定には必要な有限値と状態だけを渡す。
現在の`UNVERIFIED`停止、目標差/粗細差の別判定、親index、試行順は固定する。
ID未確認の周波数を評価するような「共通化」は回帰となる。

### F06：入口の責務集中が機能追加時の変更面を増やす

根拠：[cli.py](../src/superfish_ng/cli.py)は`main`一つで構文定義と実行処理を持ち、
物理別のrun/replay/resumeや保存出力処理が連なる。
[gui.py](../src/superfish_ng/gui.py)は操作名/許可キーの表と振分けを持ち、
専用`gui_*`モジュールへの分割は進んでいるが、共通Handlerにも多数の業務処理が残る。
[app.js](../src/superfish_ng/web/app.js)には共有画面の状態と複数workflowが集まる。

操作の追加が複数の一覧と分岐の更新を要求する。
現時点でCLI/GUIの不一致を全件実証したものではない。
既存の専用GUI境界を使い、CLIは分野別の構文登録/handler、HTTPは明示した操作定義と
輸送処理へ分割する。動的プラグイン探索や新しいWeb依存は不要。
認証、許可キー、要求サイズ、終了コード、既存DOM操作は移行時の互換対象とする。

### F07：テストの独立性と実行費用を別々に整理する必要がある

根拠：[test_material_hphi_field_overlap.py](../tests/test_material_hphi_field_overlap.py)は
別testのfixtureをimportしつつ、期待値には独立Gauss/Vandermondeを使う。
[test_gui_static_field_studies.py](../tests/test_gui_static_field_studies.py)は
形式/次数/パラメータの全組合せをGUI層で反復し、元場照合のため再求解も行う。
[TESTING](TESTING.md)には旧基準で遅い10ファイルが延べ時間の51.68%だった観測がある。
この時間比は今回のHEADでの測定ではない。

fixture構築、独立参照計算、操作契約を区別する。配置共有は可能だが、
期待値を製品側の積分/場評価へ置き換えて独立性を失ってはならない。
安価な全形式入力検査と重い実FEM操作検査を分け、実中止・再起動・改変拒否は残す。
新しい標準ランナーを作り直す必要はなく、既存`run_tests.py`の収集/失敗伝播を利用する。

### F08：現在の環境を再現する入口が一意ではない

根拠：[README](../README.md)のvenv/pip導入、[CI](../.github/workflows/ci.yml)、
[requirements-reproduce.txt](../requirements-reproduce.txt)と[DEPENDENCIES](DEPENDENCIES.md)。
`.python-version`は3.12、core宣言は幅のある依存範囲、追跡された`uv.lock`は存在しない。
再現用requirementsは納品時のNumPy 2.3.5/SciPy 1.17.0という履歴で、hash lockではないと明記される。
今回uvが選んだ既存環境はPython 3.12.3/NumPy 2.5.2/SciPy 1.18.1だった。

履歴の版が違うこと自体は誤りではない。しかし現環境、seed再現、サポート下限の確認を
同じインストール手順とみなすと再現条件を失う。
uvでの現開発環境の手順と、旧benchmark再現・Python 3.10互換検証の役割を明示する。
3.12環境の依存を3.10へ無条件に固定せず、依存更新は物理検証を伴う別の変更として扱う。

### F09：現在の本文と機能追加履歴を読む負担が大きい

根拠：[ARCHITECTURE](ARCHITECTURE.md)の「現在の責務」はseedの主要モジュールを中心に、
CLIをsolve/convergeとして説明する。
[PHYSICS](PHYSICS.md)本文には「穴・内導体は扱わない」「曲線局所細分…未受入」等が残り、
先頭追記や専用仕様の受入範囲と、canonical限定の説明を読者が突き合わせる必要がある。
これを全て実装の不整合とは呼ばないが、現在形で使う仕様として境界が分かりにくい。

基準時CODEX_HANDOFFは7,237行、PROVENANCEは4,227行。
既に[B04/CURRENT](development-plan/CURRENT.md)が現行の作業入口を集約しているので、
別の進捗正本を新設せず、現在の構成図と物理別入口/単位/受入範囲の索引を補う。
過去の失敗・未確認・許容差を履歴から削除せず、専用仕様を正本としてリンクする。

### F10：履歴再生の費用は構造上の懸念であり、まだ性能不具合ではない

根拠：[planar_tuning.py](../src/superfish_ng/planar_tuning.py)の`execute_planar_tune`は
各新試行で`_assemble(request, runs + [new_run])`を呼び、`_assemble`は履歴を走査する。
[hphi_tuning_jobs.py](../src/superfish_ng/hphi_tuning_jobs.py)の`_validate_checkpoint_files`は
保存prefixごとにreplayを行う。従って履歴長に対する検査回数が累積する。
検査の費用が一定ならprefix走査の総数は二次的に増えるが、実時間/メモリの支配項は未測定。

これは所有と元物理を確認する契約でもあり、hash比較だけへの置換は適切でない。
`hphi_tuning_saved.py`等には実行中の検証済み状態の利用もあるため、
全経路が毎回同じ費用で再計算されるとは判断しない。
まずhash I/O、native復元、行列、比較、JSON、GUI要求を分けて測る。
短命な実行内再利用を採用する場合も、外部replayと再起動後は全検証を維持する。

## 実施した確認・再現

環境参照と集計にはuv経由のPython標準ライブラリを用いた。既存環境/依存の変更はない。
既定uv cacheが読取専用だったため、cacheだけ`/tmp`へ指定した。
基準時のファイル数/行数/テスト宣言数は、作業ツリーを戻さず次のように再集計できる。
import/重複の集計定義は前述の「規模と依存の観測」に従う。

```bash
UV_CACHE_DIR=/tmp/superfish-review-uv-cache \
uv run --offline --no-project --python 3.12 python - <<'PY'
import ast, subprocess
revision = 'a191b4e089da48808ab330b169fa4ad9ea3472bb'
paths = subprocess.check_output([
    'git', 'ls-tree', '-r', '--name-only', revision, 'src', 'tests', 'scripts', 'docs'
]).decode().splitlines()
def read(path):
    return subprocess.check_output(['git', 'show', f'{revision}:{path}']).decode()
for root, extension in [('src', '.py'), ('src', '.js'), ('tests', '.py'),
                        ('scripts', '.py'), ('scripts', '.mjs'), ('docs', '.md')]:
    selected = [p for p in paths if p.startswith(root + '/') and p.endswith(extension)]
    contents = [read(p) for p in selected]
    print(root, extension, len(selected), sum(len(s.splitlines()) for s in contents))
    if root == 'tests':
        print('test declarations:', sum(
            isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith('test_')
            for s in contents for n in ast.walk(ast.parse(s))))
PY
```

F02の限定再現は次で行える。既存testのsetUpは入力/管理器の準備であり、対象メソッドは
Matplotlib確認で停止する。この実行は意図した問題再現で、製品テストのPASSとは数えない。

```bash
OPENBLAS_NUM_THREADS=1 UV_CACHE_DIR=/tmp/superfish-review-uv-cache \
PYTHONPATH=src:tests uv run --offline --no-project --python 3.12 python - <<'PY'
import importlib.util, unittest
from unittest.mock import patch
from test_gui_hphi import HphiGuiTests
original = importlib.util.find_spec
def without_plot(name, *args, **kwargs):
    return None if name == 'matplotlib' else original(name, *args, **kwargs)
suite = unittest.TestSuite([
    HphiGuiTests('test_real_http_assets_authentication_and_strict_actions')])
with patch('importlib.util.find_spec', side_effect=without_plot):
    result = unittest.TextTestRunner(verbosity=2).run(suite)
assert result.testsRun == 1 and len(result.errors) == 1
assert not result.failures and not result.skipped
assert 'GUI plotting requires the plot extra' in result.errors[0][1]
PY
```

結果はERROR 1/0.010秒。外側のassertは再現条件の一致を確認して終了0。
この依存不整合は未修正であり、RF-02へ引き継ぐ。

最終文書確認はPASS。新規/追加リンク44件、所見10件/計画10件の対応と依存の非循環、
記載した具体的なテスト名、JSON構文、上記の集計再現コマンド、`git diff --check`を確認した。
製品389ファイルのhashは基準値と一致し、製品/テスト/検証器/依存定義/CI/既存tasks.tsvは無変更。
数値validator、seed/full suite、実ブラウザー、Hosted CI、外部比較は今回未実行。
過去の受入証拠は調査に使ったが、今回の実行済みとして数えていない。

REVIEW-01は文書作成の受入条件を満たした。成果は所見と実行可能な計画の作成まで。
新しい外部参照・依存・物理採用判断はない。
原開発計画の全完了や、ここに列挙した修正の完了を意味しない。
