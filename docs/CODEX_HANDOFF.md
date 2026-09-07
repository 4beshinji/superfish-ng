# ローカルCodexへの引継ぎ

## N02の表示用分割・VTK — 2026-09-08

display.pyへP2の4分割表示データを追加し、write_vtkに接続。
二次多項式の場・面積・VTK値を検証。161 tests中159合格・2 skip、標準validate PASS。
P1のRF全量/hash/VTKバイト列は不変。次はsave_run/read_solutionへ次数・全係数・
接続情報を保持して移行し、plot_modeと追跡へつなぐ。N02全体は未完。

## N02のP2鏡映 — 2026-09-08

reflect_solutionを全中点の偶奇写像へ拡張。両端×電気/磁気対称について
独立全領域solveと周波数/RQ/損失の一致、場の偶奇、U/損失2倍を確認。
159 tests中157合格・2 skip、標準validate PASS、P1のRF全量/hashは不変。
次はP2保存/再読込/表示/追跡とBessel場・ピーク/誤差対DOF証拠を進める。
HIGH_ORDER_FIELDS.mdに記録。N02全体の受入とCase/CLI次数公開は未完。

## N02の表面積分とRF量 — 2026-09-08

quadratic_rf.surface_integrals_p2を実装し、rf.quantities/cell_fieldsへP2を接続。
既知多項式の損失/内部極値、3モードのRQ/G収束・Uスケーリングを検証。
158 tests中156合格・2 skip、標準validate PASS。P1 mode全量とhashは不変。
次はBessel全場/ピーク/誤差対DOFの証拠とP2保存・再読込・鏡映/描画/追跡統合。
HIGH_ORDER_FIELDS.mdを参照。Case/CLIのP2指定はまだ未公開でN02は未完。

## N02の軸電圧積分 — 2026-09-08

quadratic_rf.pyへ二次軸場の複素電圧/絶対値積分とP2解アダプタを追加。
低beta・部分区間・符号反転を独立積分で検査。155 tests中153合格・2 skip、
標準validate PASS。HIGH_ORDER_FIELDS.mdに式と証拠を記録した。
次はPEC表面損失/極値、quantities/cell_fields統合、その後保存/描画/鏡映/追跡。
N02全体と継続目標は未完。

## N02の場評価を開始 — 2026-09-08

HIGH_ORDER_FIELDS.mdにN02仕様と全移行箇所を記録。FieldSamplerは明示したP2空間の
6係数を保持し、from_solutionで次数整合を検証する。独立多項式/軸極限テスト合格。
152 tests中150合格・2 skip、標準validate PASS、P1の周波数/RFとhashは不変。
次は二次軸電圧の安定積分・PEC辺積分/極値。その後RF/保存/表示/鏡映/追跡を統合する。
N02は実装途中であり、全体の受入は未完。

## N01のP2固有値コア — 2026-09-08

N01.S/I/Vを受入。QUADRATIC_ELEMENTS.mdに独立積分・収束・再現手順を記録。
研究用high_order.solve_p2のみ公開し、P1用の場/RF/保存/鏡映はP2解を明示拒否する。
150 tests中148合格・2 skip、標準validate PASS。既存の円筒/成形セルのmode全量は直前と一致。
次はN02.Sで高次係数を保つ場評価・RF積分・保存・描画・鏡映・追跡を設計し、実装/検証する。
32項目・33親課題全体の目標は継続中。以下の古い開始点は履歴として読む。

## R01の加速量規約 — 2026-09-08

R01.S/I/Vのnative範囲を完了。ACCELERATING_CONVENTIONS.mdに仕様・再現・失敗履歴を記録。
v3 rfのactive_length_m、voltage_interval_m、phase_origin_mを追加し、旧既定値/hashを保持。
解析比較、鏡映写像、CLI/GUI/保存を更新。143 tests中141合格・2 skip、標準validate PASS。
最終GUIはout/gui-r01-browser-accepted-20260908、数値はout/validation-r01-final-20260908。
初回の区間外掃引拒否と撮影待ちFAILを保持する。旧入力の任意ZCTR等はまだ受け入れない。
次はN01.SのP2要素/解契約→N01.I/V、N02の場/RF/保存・表示への移行を進める。
N02受入まで高次RFを製品公開しない。C00の未確認行とC03/C04も継続対象。

## O01の保存完了管理 — 2026-09-08

O01.S/I/Vのローカル契約を完了。SAVE_COMPLETION.mdに仕様と受入を記録した。
save_runは出力先を排他予約し、内部一時領域で全ファイルを作り、非置換hard linkで
完了マーカーを最後に公開する。read_solutionは全必須出力のhashを検査し、旧形式も読む。
Job取込の外部meshコピー漏れを修正し、新しい直接保存の完了証拠を区別して保持する。
137 tests中135合格・2 skip、out/validation-o01-accepted-20260908がPASS。
R01の加速量規約とN01/N02、C00調査、C03/C04は未完。次はR01.Sから進める。

## C02限定AF読込の受入 — 2026-09-08

LEGACY_INPUT.mdのC02初期部分集合を仕様・実装・検証まで完了。
import-afはnr/nz/modes/導電率/正規化を明示必須とし、DX/FREQ等の無適用を診断に記録する。
単一REG・全PEC・軸接続真空TM・直線/段差/NT4/5短円弧のみ受理。その他は位置付き拒否。
128 unittest中126合格・2 skip、out/validation-c02-final-20260908がPASS。
保存AF2形状からの新規NG4計算と既存SFO照合はout/c02-import-acceptance-20260908。
新規旧計算・場全体/表面ピークの受入ではない。C00/C03/C04と汎用旧入力は未完。
次はR01の加速量規約、またはO01の直接保存完了管理を仕様化して実装する。

## C01共通契約の受入 — 2026-09-07

C01.S/I/V完了。仕様・実行証拠・再現はMODEL_CONTRACT.md。
v3 modelとcapabilities/migrate-caseを実装し、v1/v2のhashと既存解を保持した。
Project/Study/GUI/鏡映/外部meshの保存でmodelを失わず、追加物理は計算前に拒否する。
122 unittest中120合格・参照環境専用2 skip、標準validateとChrome 8操作検査PASS。
最終証拠はout/validation-c01-final-20260907、out/gui-c01-browser-final-20260907。
次はC02.SでDXのNG指定への写像、FREQ等の探索指定、未指定導電率/正規化の扱いを
明記し、確認済みAF部分集合のstrict読込と変換記録を実装する。C00調査は未完了のまま継続。

## 互換開発goal開始 — 2026-09-07

ユーザーが32対応項目・33親課題の完遂をgoalに指定。作業checkoutは
`/home/sin/code/agent/reserch/superfish-ng`。C00の最新記録はCOMPATIBILITY_BASELINE.md。
全32項目の受入軸、限定TM辞書と未確認事項、保存出力のAutomesh/Fish/SFO/SF7版、
参照ファイルhashを記録した。C00.Vは未完了。次はC01.Sの共通契約とC02.Sの
メッシュ/探索/未指定RF設定の変換契約を具体化し、C00の追加ツール調査も継続する。
開始時114 unittest中112合格・参照環境専用2 skip。今回の旧計算再実行はなし。
以下の計画整備のみを対象とした指示より本節を優先する。

## 現在の入口 — 2026-09-07 計画整備

最新指示は「実態に合わせて計画更新→互換対応表→作業分割」。このターンは計画を整備する。
計画整備v0を完了。[COMPATIBILITY_MATRIX.md](COMPATIBILITY_MATRIX.md)のK01〜K32と
[COMPATIBILITY_PLAN.md](COMPATIBILITY_PLAN.md)の.S/.I/.Vを次の作業単位とする。
次はC00の版・入力集合の確定→C01.Sの共通契約。高次要素へ直ちに飛ばない。
表のH/Uは対象版未確認、Xは互換必須集合外。仕様調査未完を互換完成と混同しない。
[IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md)と[BACKLOG.md](BACKLOG.md)を正本とし、
以下の履歴内の「次は…」やseed開始プロンプトより優先する。
製品基準1f5cd84で114テスト中112合格・2 skipを再確認。物理範囲や製品コードの変更はない。
P1-03は平坦z端で完了、P2-04はGUI範囲で完了。一般追跡・tune・直接保存の原子的完了は残る。

以下は日付付きの実施履歴。テスト件数・実行環境は各時点の値を保持する。

## 互換性拡張の再開 — 2026-09-07

ユーザーは可能な範囲で互換拡張を進め、区切りごとのローカルコミットを指示した。
P0-01のNGSolve独立照合を完了。仕様と再現はINDEPENDENT_COMPARISON.md。
通常環境の基準101テストは合格。検証専用venvは
`/tmp/superfish-ng-independent-20260907`。本体の依存・FEM・RFは変更していない。
次はP0-02のタグ付き非構造メッシュ。旧入力互換や物理範囲拡張の完了ではない。

同日P0-02/P0-03も完了。`solve case.json --mesh mesh.json --out ...` と
`solve(case, mesh_data=...)` を追加。仕様・受入はMESH_INPUT.md。
114件中112件合格・参照環境専用2件skip、標準数値検証PASS、既存周波数差ゼロ。
次の数値拡張候補はP1-01。メッシュの読込で対応物理範囲は増えない。

## 汎用GUI・共通入出力の計画 — 2026-09-06

ユーザー依頼に基づき [GUI_IO_PLAN.md](GUI_IO_PLAN.md) を作成した。
例題専用の処理を作らず、対応物理範囲の汎用操作を提供し、KEK対象操作と例題外の
合成ケースで受け入れる。追加機能・抽象化は全体品質への寄与で判断する。
追加指示でG0〜G5の受入完了を `/goal` に設定した。ADR-009/010により
Project・JobManager・保存結果読込・Study・ローカルGUIを共通化した。
新規Web/Qt依存なし。形状編集、旧結果取込、掃引/収束/比較/分散を実装済み。
32数値受入、101 unittest、別環境へ展開したwheelのGUI計算/描画がPASS。
G0〜G5の技術的受入を完了。実行証拠・対象外・主観評価の未実施はGUI_ACCEPTANCE.md、
操作はGUI_GUIDE.mdを参照。
`python -m superfish_ng gui --workspace out/gui-workspace` で起動する。
既存の半端部バンド同定を任意形状へ適用しない。一般mode tracking・tuneは本計画の対象外。

## 境界・局所メッシュ改善 — 2026-09-06

任意のv2 mesh設定で境界辺と角周辺の内部辺を実長制御する。既定は従来経路。
設定仕様はINPUT_OUTPUT.md、検証数値と制約はPHYSICAL_MESH_REFINEMENT.md。
最終9計算は `out/physical-mesh-final-20260906/`。1 mm固定点変化26.14%→2.21%、
PEC接線比7.95%→1.52%。節点約3.25倍であり同コスト優位の証明ではない。
円弧には境界サイズのみ対応。P1電場復元と鋭角特異性は変わらない。

## 角部診断の追加 — 2026-09-06

ユーザーの質問を受け、P1-04の切り分け評価を実施。
[SURFACE_FIELD_DIAGNOSTICS.md](SURFACE_FIELD_DIAGNOSTICS.md)に新規計算と解釈を記録する。
鋭角のEpkは細分で上昇するため、過去のNG–Wine差14.8%を有限厳密値の誤差と解釈しない。
実装本体は変更していない。現checkoutには過去out/がなく、ユーザー許可でWine比較環境も新設した。
NG25計算（元の19＋真空側固定点6）とWine鋭角/接線円弧各4段階を完了。
最終参照は `out/surface-wine-arcs-20260906/report.json`、図と集約値は
`out/surface-wine-report-final-20260906/`。鋭角の生結果は検査して再利用した。
Wine最細の鋭角ピーク変化17.48%、丸み対照ピーク変化2.81%を未収束として残す。
丸み対照のNG–Wine差は1.21%。今回の診断をP1-04全体の完了やEpk精度保証と呼ばない。
78テストと `out/validation-surface-final-20260906/` の既存数値検証は合格。
Wineランタイムは `/tmp/superfish-wine-runtime/`。一時領域の掃除後は再作成が必要。

## 現在の優先目標（2026-09-05更新）

ユーザー指定の [セミナー4資料の例題計算・可視化](MILESTONE_SEMINAR.md) は完了。
最終結果は `out/seminar-suite-final-20260905/index.html`、受入監査は [MILESTONE_ACCEPTANCE.md](MILESTONE_ACCEPTANCE.md)。
9数値ジョブ・69テスト・7ページ検査がPASS。全NGは新規計算、Wineは入力・hashを検査して再利用した。
最終suite.jsonはPASSかつsource_changed_during_run=false。継続待ちの計算プロセスはない。
以下の個別試行・失敗も履歴として保持する。次の機能拡張はユーザーの次の指示で選ぶ。
Wine版SUPERFISHとの3形状の基本モード照合は完了し、[比較結果](SUPERFISH_COMPARISON.md) を保存した。
S1の全領域TM010/TM011・長さ掃引・図・CSV・HTMLとWine/SF7照合は実装済み（[記録](SEMINAR_PILLBOX.md)）。
S1の半領域の電気／磁気対称境界・全空洞鏡映も完了。`seminar_symmetry.py` で再現可能。
段差・円弧、4/7モード同定と分散曲線も実装済み。[記録](SEMINAR_MULTICELL.md)を参照。
flat4はNG nr=128/256/512とWine dx=0.05/0.025/0.0125/0.01で全照合・収束PASS。
`out/seminar-flat-ready-20260905` とheadless検査 `out/gallery-test-flat-ready-20260905` が最終結果。
rounded4はNG・形状近似・Wine3段階の全検査合格（`out/seminar-rounded4-wine-comparison-20260905`）。
rounded7は任意のcrossed分割を追加し、nr=64/128/256で全量PASS。
`out/seminar-rounded7-crossed-native-20260905` と `out/seminar-rounded7-crossed-geometry-20260905` を参照。
円弧半領域の鏡映にも対応したが、対称反射だけのR/Q改善試験は不成功。失敗試験も保存済み。
rounded7のWine3段階は `out/seminar-rounded-wine-20260905/rounded7` で完了。
full-end切断面を実装した `scripts/seminar_end_cells.py` も追加。初回検査はflat/halfのR/Qだけ1.1521%でFAIL。
追加nr=384で変化0.32373%を確認し、`out/seminar-end-cells-ready-20260905` の最終レポートはPASS。
`out/gallery-test-end-cells-ready-20260905` で全8選択肢・51リンク/画像のheadless検査も合格した。
Pillbox/rounded4/7のHTMLはheadless Chromeの実キー入力で検証済み。Orcaの既存デスクトップ操作は行っていない。
S6の `scripts/seminar_suite.py` と入口HTML生成を実装し、`out/seminar-suite-20260905` の全NG計算・全7画面検査は終了。
全体FAILの原因は7セルπモードのWine側R/Q細分1.98217%とTTF。NG–Wine差は全モード合格。
RAM設定で追加DX=0.01/0.011 cmはSFO生成前に失敗。ローカルSF.INIのStoreTempDataInRAM=Noを使う
`out/seminar-rounded7-wine-extra-20260905/disk-dx0.01/mode7` が正常終了。既設SF.INIは変更していない。
πの追加R/Q細分変化0.658403%、NG–Wine差0.757236%で合格。元の未達履歴は消さない。
モード別追加細分の検証を実装し、`out/seminar-suite-final-20260905` で全NGを再び新規計算してPASS。
参照は既存Wine生出力を検査して再利用し、必要なrounded7出力は最大14400秒の読取専用待ちを明示した。
開始時のsource/tests/scripts/examples hashと終了時の一致を確認した。今後も一括実行中にはソースを編集しない。
最終suite.json、全子レポート、参照ファイル、画面とリンク先のhashも再監査した。
追加参照を含む比較はfinal_legacy_modesを読む。legacy[-1]は追加前の履歴であり、πの旧FAILが意図的に残る。
操作手順と判定仕様は [SEMINAR_SUITE.md](SEMINAR_SUITE.md)。
以下の開始プロンプトはseed時点の記録で、次課題P0-01の優先順はこの更新で置き換える。

## 開始プロンプト

以下をそのままCodexへ渡せる。

```text
このSuperfish-NGリポジトリを継続開発せよ。
AGENTS.md、README.md、docs/PHYSICS.md、docs/PROVENANCE.mdを最初に読み、
ローカルでテストとscripts/validate.pyを実行して初期状態を確認すること。
旧SUPERFISHのソースやバイナリは参照・使用せず、公開された数学と
明示的なライセンスを持つ現代のOSSだけを使用する。

次の目標はdocs/BACKLOG.mdのP0-01「外部ソルバでの独立照合」である。
同じ幾何形状・境界・phasor・単位・R/Q規約を固定し、NGSolve等で
独立に計算して比較する。参照ソルバを導入できなければ、比較済みとは
主張せず、実行可能な比較用入力と未実行の理由を残すこと。
その後P0-02の境界タグ付き非構造メッシュ対応へ進む。

科学的な回帰を起こさず、小さなコミットで進めること。
周波数だけを解析値に合わせてRF量の精度を保証したことにしない。
変更内容、検証結果、未解決事項、次に実行するコマンドを最後に報告せよ。
```

## 現在の動作経路

`Case.load → make_mesh → assemble → solve → quantities → save_run`。
式と積分は `src/superfish_ng/fem.py` と `rf.py`、独立解析解は `analytic.py`。
テストは `unittest` 69件。seedの主要数値は `benchmarks/validation/`、最新照合は `docs/SEMINAR_PILLBOX.md` と `docs/SEMINAR_MULTICELL.md`。
出力は別の新規ディレクトリへ作る。既存ベンチマークを直接上書きして初期値を失わないこと。

## 直近の注意点

- P1のuはr³重みのエネルギーでは良好でも、軸上Ezの点値収束はより遅い。
- 自由度は節点u=Hφ/r。VTKに出すHφはrを掛ける。軸上uを0にしない。
- 電場のP1微分を節点平均で平滑化すると見た目は改善してもピーク値が偏る。未評価の平滑化を設計指標に混ぜない。
- 無限に鋭い角を持つ形状ではEpkのメッシュ独立値が存在しない可能性がある。丸め半径を仕様にする。
- 既定のactive lengthは全長。多セルやビームパイプ追加時に自動流用しない。
- seedのQR/直交化はeigshに任せ、物理的な勾配nullspaceを除去したことにはしない。現在のTM縮約に3D機能を足す際に再設計する。
- `save_run`は出力ディレクトリを新規作成するが、ディスク書込み全体のトランザクション化は未実装。途中失敗したディレクトリは完了扱いしない。

## 環境の再現

通常は `pip install -e .`。納品時のPython 3.12系に揃える場合は
`pip install -r requirements-reproduce.txt` の後 `pip install -e . --no-deps`。
このファイルはプラットフォームごとの依存ハッシュを固定したlockfileではない。
OS・BLAS・CPUや縮退モードの基底は変わり得る。期待値は許容誤差で比較する。

CIはLinux/Python 3.10と3.12を対象とする定義を同梱したが、納品時の実行実績はローカルPython 3.12のみ。
依存環境を整えたユーザーPCでのテスト結果を次の記録として保存する。

## 完了報告の基準

新しいバックエンドは、関数がimportできるだけでは完了ではない。
入力ケース、出力、参照値、誤差、実行バージョン、未対応条件を記録して初めて完了とする。
外部参照値が入手できないときはその事実を示し、架空のSUPERFISH/CST比較表を作らない。

最新メッシュ改善の検証: 82テスト、`out/validation-physical-mesh-final-20260906/` PASS。
seed周波数差ゼロ、RF相対差最大6.67e-16。既存ベンチマークの更新なし。
