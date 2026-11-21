# 境界再メッシュの生成文書とStudy GUI

2026-10-13 JST、ADD-N04-boundary-remesh-05 **DONE**。
先行保存APIは `432fb97`。[固定仕様](CURVED_BOUNDARY_REMESH_SPEC.md)の05を対象とする。
独立幾何・解析場・RF精度の専用6求解は06で別途受入する。
全136カードは87 DONE/2 IN_PROGRESS/47 PLANNED、原123は76/2/45。次は06。

## 操作と保存範囲

曲線形状のメッシュ切替Studyで「元の二次形状を保ってメッシュを自動生成」を開く。
設定例の版を選び、「選んだ設定例を入力」を押した場合だけraw JSONを置き換える。
版1は初期弦メッシュのサイズ、版2は元P2境界を制限分割した最終メッシュのサイズを指定する。
境界辺数・seed/最終反復予算、弦の長さ/面積と曲線弧長/実面積の違いを表示する。

生成成功時は元Projectを保ち、現在の切替値で固定計画をStudyに反映する。
seed→最終の要素/境界辺数と、最終最大弦長・弦面積・最小弦角・P2隅角を表示する。
幾何一致の判定をRF精度へ昇格しない。生成文書の物理誤差上界はnullを維持する。

保存対象は**最後に検証を終えた元Project・設定・計画・全検証値**である。
編集後の値が必要なら再生成する。保存文書の読込はraw JSONをサーバーで完全再生し、
正規化と途中変更検査が完了してから元Project・全履歴・設定を復元する。
Studyの形状法則は別に保持し、復元計画には現在の切替値を用いる。Study全体も従来の保存入口で保存できる。

HTTPの既存 `generate-curved-remesh-plan` は省略時に従来の裸planを返す。
明示 `format: "document"` だけ完全文書を返し、新 `replay-curved-remesh-generation` は
文書を元入力から全再構築する。未知形式・raw重複・改変・予算違反を拒否する。
準備/生成/ファイル読込/再生/正規化の各非同期区間で入力が変わった場合は結果を反映しない。

## 対象を絞った検査

`tests/test_gui_curved_boundary_remesh.py` の2件は20.833秒、終了0。
実HTTPで両版の既定plan/完全文書/再生API一致、重複・改変・型・NaN・上限・認証拒否を確認した。
全solve入口を禁止し、生成/再生がジョブやFEMを作らないことも確認した。

実Chromeは次の42操作を分割して確認した。全reportで外部通信0、製品源変更0。

| 検査 | 結果 |
|---|---|
| 新 `verify_gui_curved_boundary_remesh.mjs` | 20項目PASS。設定例の明示操作、版2の完全生成/ダウンロード、重複/予算/改変拒否、設定/Project/履歴変更時の古い生成応答拒否、ファイル/再生/正規化中の変更拒否、版1/2復元、Study保存、実worker2点 |
| 無変更 `verify_gui_curved_harmonic_study.mjs` | 21項目PASS。版1生成・裸plan読込、元法則/Study復元、実worker2点、実場追跡/完全再生、逐次/適応要求、旧固定領域Study |
| 新しいHTTP serverとChromeで保存文書を復元 | 1項目PASS。元Project・設定・固定計画・Study定義完全一致、新FEM0 |

新旧画面と再起動画面のPNGを保存し、新版/復元後のラベル・測定値・制限説明・保存導線を目視確認した。
全browser/server/thread/所有worker handleは終了した。

## 保存場の照合

GUIの通常Studyと適応workerの元2点は、元Project/初期mesh・各10 NPZ配列・全mode/RF値が一致した。
公開readerによる再構築前後の各native全9ファイル、計36ファイルのbyteを保持した。
両経路間にはJavaScriptの `1.0 → 1` 表記によるCase JSON・CSV・results/Case SHA・completion SHA差がある。
この表記差を隠して全ファイルの経路間byte一致とは呼ばない。場配列と数値は完全一致した。

## 実workerの中止・管理器再生成・再開

`scripts/validate_curved_boundary_remesh_workflow.py` で元2点の実FEMを保存し、
BISECT後のPAUSED checkpointを作成した。新しく起動した所有workerをLinuxのSIGSTOPで
queued状態に固定し、execution未作成を確認して公開cancelを呼んだ。実processは終了コード-9で終端した。
これは実workerの計算開始前の中止であり、FEM途中の回復や異常クラッシュ回復の証拠にはしない。

JobManagerを閉じて再生成し、cancelled状態の保持を確認して、元checkpointから別workerを再開した。
新しい中点0.5の1 FEMだけを追加し、元の最大深さでSTOP/UNVERIFIEDとなった。
元2点の全24ファイルと各10配列は完全保持した。さらに管理器を作り直して完了結果を検証し、
solve禁止で適応全結果を完全再生、3 nativeを公開readerで再構築した。
初期要素は26/8/26、最終要素146/84/146、境界24/28/24。追跡・RF精度を確認済みへ書き換えない。

初回の保存パス誤記を修正した後続runは361.139秒、handle70886終了0/PASS。
元2 FEMを再利用し、後続新1 FEM、中止時FEM0、全所有process終端。
GUIの新旧各2 FEMと合わせ、本工程は**計7新FEM**、06の専用6 FEMは未実行である。

再現入口は `OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-uv-cache
uv run --no-sync python scripts/validate_curved_boundary_remesh_workflow.py --out out/<new-directory>`。
既に完了した同じ2点のcheckpointは `--checkpoint <adaptive-study-results.json>` で再利用できる。
出力先は必ず新規ディレクトリとし、旧成果物を上書きしない。

## 来歴と範囲

rawは `out/n04-boundary-remesh-gui-20261013/`、worker初回は
`out/n04-boundary-remesh-worker-20261013/`、後続は
`out/n04-boundary-remesh-worker-resume-20261013/` に保持する。
操作/失敗log・全1457源・全7 native/63保存fileのSHAを
`out/n04-boundary-remesh-gui-20261013/acceptance.json` と `native-output-sha256.json` に結合した。
初回worker検査の `solution.npz` パス誤記によるERRORと、旧GUI並行起動の作業領域ロック拒否を保持する。
実保存先 `solution/fields.npz` に検査側を修正し、完了済み2点の再求解を避けて再開した。
旧GUIは専用領域へ変更し、求解前に停止した起動だけを補った。
初回1457源からの変更は検査スクリプトのパス修正/既存checkpoint再利用だけ。
後続runの全1457源は前後byte不変だった。元1454対象のうち製品変更は
`gui.py`、`web/app.js`、`web/index.html` の3ファイルだけで、例READMEの追補は検証後の文書変更として分ける。

変更はHTTP/ブラウザーの操作・表示・保存adapterと検証入口に限る。
生成器・幾何/FEM・RF・追跡・保存核と許容差を変更しない。
03の独立幾何/Green/行列/尺度と04の全保存再生の成功証拠を再利用する。
新seed/full/legacy実行0、新依存/外部コード/外部サービス0。
親N04の残件と全goalを維持する。
