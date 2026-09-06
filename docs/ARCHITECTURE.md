# アーキテクチャと拡張判断

## 現在の責務

| モジュール | 責務 | 依存先 |
|---|---|---|
| config.py | strict case v1/v2、単位/幾何/対称境界制約、canonical入力 | 標準ライブラリ |
| mesh.py | profile/段差から三角形、境界タグ、要素勾配・トポロジー検査 | NumPy、SciPy sparse |
| fem.py | Hφ=r u のK,Mを組み立て | mesh、SciPy sparse |
| solver.py | 平衡化、固有値、残差、直交性、エネルギー正規化 | fem、ARPACK |
| rf.py | 復元場、軸積分、表面積分、規約を固定したRF量 | mesh、定数 |
| symmetry.py | 対称部分領域のメッシュ・場を全空洞へ鏡映、残差検査 | mesh、fem |
| geometry.py | 短円弧の厳密パラメーター、弦近似、断面積 | NumPy |
| modes.py | 演習バンドのセル場/零交差による同定、分散フィット | NumPy、SciPy optimize |
| analytic.py | 独立解析解。solverから参照しない | SciPy special |
| io.py | JSON/CSV/NPZ/VTK、入力hash・環境メタデータ | solver出力、rf |
| cli.py | solve/converge、失敗コード、上書き拒否 | 上記API |
| scripts/validate.py | 実際の検証実行・比較・source hash | ローカルPython |
| scripts/plot_results.py | 保存結果から任意の図を生成 | Matplotlib |

Caseの点列は `(z,r)`、内部Mesh.pointsは `(r,z)`。
出力とモジュール名で区別し、将来のCADアダプターで入れ替え事故を防ぐ。

## 現在のPython API

```python
from superfish_ng import Case, solve
from superfish_ng.rf import quantities
from superfish_ng.io import save_run

case = Case.load("examples/pillbox.json")
solution = solve(case)
print(quantities(case, solution, mode=0))  # Pythonのmodeは0-based
save_run(case, solution, "out/my_run")   # caseはsolutionを解いたものを渡す
```

SolutionはMesh、K/M、固有値、周波数、u、残差、直交性を保持する。
巨大計算を想定したlazy/distributedデータ構造ではない。出力対象場はすべてローカルメモリに置く。
ループの主体はNumPyでバッチ化した要素積分。固有値のfactorizationはSciPyの疎行列処理に任せる。

## ADR-001: 参照用の縮約ソルバを最初に作る

決定: scalar u=Hφ/r、P1三角形、SciPyを実装する。
理由: 軸上・PEC・積分規約を検査でき、ローカル導入が軽く、コードを読んで物理式に対応づけられる。
不利: 高次曲線形状、任意メッシュ、並列、高精度表面場は自前拡張または移植が必要。
再検討条件: 外部比較での精度/自由度比、実利用形状でのメモリ/時間、cavsim2d等との重複。

## ADR-002: 最初のgeometryを正のR(z)に制限する

決定: 軸から外壁までの真空領域のみを扱う。
理由: メッシュと軸線を確実に生成し、内導体による別の位相空間・nullspaceを初期版へ持ち込まない。
不利: リエントラント形状の一部、垂直段差、穴、同軸、任意CADに対応しない。
再検討条件: 境界タグ付き非構造メッシュ、トポロジー検査、適切な検証ケースが揃うこと。

## ADR-003: 完成前のプラグイン抽象化を先に作らない

決定: 未実装MFEM/SLEPcクラスやfake adapterを同梱しない。
今後二つ目の実際に動くバックエンドができた時点で、
`geometry → mesh with tags → mode fields → RF postprocessing` を共通契約にする。
共通化するのはcase、単位、結果スキーマ、ベンチマーク。有限要素の内部DOF表現を無理に統一しない。
生産用の場評価APIには体積積分、境界trace、軸line probe、curl評価を要求する。
P1用の質量行列や `u=Hφ/r` をあらゆるバックエンドへ押し付けない。

## ADR-004: ファイルベースの再現性

JSON case v1、正規化した入力SHA-256、環境、規約、結果を保存する。
現状のcase_sha256は入力だけのhash。ソフトウェア全体の同一性を示すにはvalidationのsource hashまたはGit commitを併用する。
キャッシュを実装する場合はcase_sha256だけでは不十分で、solver/postprocessor版と依存環境を含める。
既存出力の上書きを避ける。原子的な完了manifestはP1-06で扱う。

## 性能上の限界

現時点のエビデンスは約8,500節点までの小規模ケース。
100万自由度・MPI・GPUに対応する設計や性能測定は行っていない。
サイズ増加時は疎行列factorizationのメモリが支配的になり得るため、実ケースで測定してからSLEPc等を選ぶ。
一様に細分するだけで特異角のピーク値が改善するとは期待しない。

## ADR-005: 垂直段差は共有半径格子のスラブメッシュで拡張する

測定された必要性: セミナーflat-noseの入力には同一zの異なるrがあり、従来profileは入力段階で拒否した。
決定: v2のstepped_profileを追加し、軸連結・z非減少の外壁という制約を維持した適合スラブメッシュを実装する。
垂直面を正確に保ち、面積・境界包含・位相構造・解析積分で検査する。従来profileの経路は維持する。
新しい依存ライブラリは追加しない。連結性検査に既存SciPyのcsgraphを使用する。
不利: 一般CADやz方向に折り返す輪郭には対応しない。複数の頂点半径は全スラブの格子を増やす。
再検討条件: 円弧近似の点数が格子を過大にする、強い傾斜で細長い要素が増える、適応細分が必要になる場合。

## ADR-006: 生成HTMLは既設headless Chromeで統合検証する

必要性: 静的リンク監査ではmode選択イベントや実際の画像表示を証明できず、デスクトップ用Orca CLIも起動できなかった。
決定: Node 22の標準WebSocketとChromeの公開プロトコルで、一時プロファイルのheadlessテストを追加する。
既存デスクトップの操作ではなく、生成したローカルHTMLのキーボード操作・画像・リンクに検査を限定する。
PythonアプリにWeb frameworkを導入せず、npm依存も追加しない。Chrome/Nodeは任意の検証ツールとして別途必要。
失敗fixtureで検査自体のFAIL経路を確認し、UI合格と数値合格を別に報告する。

## ADR-007: 周期セルの場の対称性を保つ任意の交差分割

測定された必要性: rounded7のnr=64で、同じ形状の0モードセル振幅が1.0000から0.9901へ
一方向に傾いた。πモードも約0.8%の傾きを持ち、小さいR/Qの細分変化は9.53%だった。
決定: v2で四辺形中心へ4分割するcrossedを選択可能にする。従来diagonalとv1 hashを維持する。
頂点・三角形集合の鏡映不変性、Pillboxの偶奇性・解析RF量、周期セル0/π等振幅を独立に検査する。
同じnr=64でセル振幅のばらつきは約1.3e-10以下になった。固有場を平均・補正していない。
不利: 同じnr/nzでも節点・要素数が増える。非一致高さ列のfanや一般非対称形状の誤差は消えない。
新規依存はなく、既存P1弱形式と積分をそのまま使用する。R/Qの収束は別ゲートで判定する。

## ADR-008: 参照側の追加細分はモードごとの履歴として保持する

必要性: 7セルの全NG–Wine差が基準内でも、πモードだけ参照側R/Q/TTFの最終細分が未達だった。
決定: 同じ物理モードの追加DXと生参照を明示できるようにし、元の全バンド細分結果を上書きしない。
追加AF/SEGの一致と厳密に小さいDXを検査し、追加の符号付き場を含む全バンドの一対一同定をやり直す。
最終判定・図は各モードの最後の参照に対応させ、そのDX・直前との変化・出力hashを記録する。
不利: 最終参照のメッシュサイズがモード間で異なる。全バンドを同じ追加DXで解いたとは表示できない。
同定テンプレートで場を置換・平均化せず、1%のRFゲートも変えない。新規依存や物理ソルバー変更はない。

## ADR-009: ローカルブラウザーGUIと別プロセス計算

2026-09-06、GUI_IO_PLAN G0。既存Case/FEM/保存場のMatplotlib描画を使い、
Python標準のThreadingHTTPServerと同梱HTML/CSS/JavaScriptでローカル操作を提供する。
追加Webフレームワーク、Qt、npm依存は導入しない。描画には既存plot extraを使用する。
Tkはimportできたが、この環境ではDISPLAYがなく最小ウィンドウが起動しなかった。
デスクトップ方式の操作性能は未測定。Qtを追加する必要性は現時点で示されていない。

ブラウザー試作は半径65 mm・長さ90 mmを実際の入力操作で設定して計算・描画した。
ページ読込143 ms、solveとplot合計0.919秒、計算中の状態取得2.15〜6.78 ms。
独立plotの最大RSSは115832 KiB、実時間1.83秒（その試行ではBLASスレッド数未固定）。
本実装の最小導線は半径65 mm・長さ95 mm、2モードの入力・計算・表示・不正入力保持がPASS。
Chrome 152.0.7977.82 / Node 23.11.1 / Python 3.12.3、Linux headlessでの測定である。
結果: `out/gui-g0-browser-20260906-retry/`、`out/gui-first-browser-20260906/`。
初回はsandboxのsocket制限、試作の最初のEnter操作試験は計算開始せず失敗した。
loopback起動の実行許可と実クリック検証で再試行し、成功を確認した。失敗をUI合格に数えない。

計算はsubprocessで画面から分離する。JobManagerが固有ディレクトリ、状態、
中止と再起動時の中断判定を管理し、manifestのファイルhashで完了後の欠落を検出する。
既存save_runの保存形式・直接APIは変更せず、管理対象ジョブのsolution/内で利用する。
公開サーバー用途には使わない。127.0.0.1限定、Host/Origin確認、起動時のセッションtoken、
静的ファイルの許可リスト、外部資産を使わないCSPを持つ。URLは起動したユーザーだけで扱う。
GUIの計算完了はメッシュ収束済みを意味しない。

参照: [Python http.server](https://docs.python.org/3/library/http.server.html)、
[Python tkinter](https://docs.python.org/3/library/tkinter.html) の公式API文書。
ソース実装のコピーなし。http.serverをインターネット向けサービスへ転用する設計ではない。
