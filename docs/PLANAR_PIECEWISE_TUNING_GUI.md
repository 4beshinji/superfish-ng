# 区分形状調整GUI（P04-c、操作受入途中）

2026-10-02、基準 `9946fb5`。要求4の専用GUI輸送・フォームと所有保存地点を接続した。
Python操作の新1/旧5件はPASS。実ブラウザーの新版/旧版操作、新サーバー再生、
APIとの全元場照合、親P04全条件監査は未実施であり、本カード/親P04はIN_PROGRESS。

## 再現と変更

新版の実workerで初回試行を保存し、GUIの保存地点選択を呼ぶと、基準は相対trial名を
所有先なしで再生してValueErrorとなった。新操作テストの修正前実行は6.316秒ERROR、
session11909終了1。ログは `out/p04c-planar-gui-20261002/baseline.log`。

要求4の保存地点は[P04-b-cの所有選択](PLANAR_PIECEWISE_TUNING_WORKER.md)へ渡し、
投入時prefixの地点も検証して開く。元投入pathへの再アクセスは不要であり、要求/
判断/全nativeのhashと所有先を確認する。旧版の保存地点検査は従来どおり保持する。

元場取込はcheckpoint2だけ全trial snapshot（Project、完了job metadata、claim、
全native）を比較する。旧checkpoint1のhash集合は変えない。取込前後の元byte不変を
検査し、対象IDの実順位を使用する。

フォームの多項式変形には「断面全体に同じアフィン変形」と「元メッシュの頂点ごとに
変位を指定」を設けた。後者を読み込んだ場合も保持して要求4を生成し、明示した回復
方法を保存する。追加回復なしを選んだ場合は方法の指定を促して投入しない。
法則/追跡条件JSONは元文字列をstrictサーバーへ渡し、重複キーを再serializationで隠さない。
行列係数は無次元、頂点/平行移動係数はmという説明を表示する。

## Python操作と選択検証

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-ng-uv-cache \
  uv run --no-sync python -m unittest -v test_gui_planar_piecewise_tuning test_gui_planar_tuning
node --check src/superfish_ng/web/planar.js
```

session93859、6件160.930秒PASS、終了0。全395製品hashは開始/終了で一致。
新条件は要求4の厳密JSON保持、実workerの保存地点選択、元場の全NPZ配列とRF byte一致、
元job移動後の別job再開、継承prefixの選択、元投入envelope不変、結果再生、管理器再作成。
旧5件は要求の重複キー拒否、旧保存地点/回復/対象順位/元場取込、別job差替え拒否、
未確認周波数/取込拒否、投入envelope改変拒否を確認した。

証拠は同ディレクトリの `selected.log`、`implementation-before.json`、`api-acceptance.json`。
全worker/sessionは終端、製品src固定解除。unitはHTTP/ブラウザー操作検証の代用ではない。
FEM算術/数値許容差/canonical seedは変更しておらず、seed/全validateは実行していない。

## 次に必要な受入

- 実ブラウザーで要求4の法則/回復条件を保存して再読込し、同じProject/要求を維持する。
- 実調整/最終細分の成功とUNVERIFIED、実中止/保存地点選択/別job再開を操作する。
- 元場取込・表示とAPIの全native/Project/判断/RFを照合し、旧アフィン操作も確認する。
- サーバーを正常終了/再起動して保存結果/元場を復元し、所有ブラウザー/サーバーを回収する。
- P04-a、P04-b全子と本GUIの証拠を条件別に監査し、満たした場合だけP04-c/親P04をDONEとする。

新しい検証器は `scripts/browser-session.mjs` を使用する。既存
`verify_gui_planar_tuning.mjs` / `verify_gui_planar_tune_recovery.mjs` の共通操作を参考にし、
新版のpolygon Project/法則と所有prefixに合わせる。実行中は製品srcを固定し、
CURRENTへsession/出力/開始hashを記録する。

自作の既存フォーム/所有選択/専用元場取込を再利用し、外部資料/依存/legacy参照を追加しない。
