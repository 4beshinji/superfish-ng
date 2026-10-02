# 区分形状調整GUI（P04-c-a受入）

2026-10-02、製品 `c81782d`。要求4の専用GUI輸送・フォームと所有保存地点を接続した。
Python新1/旧5件、実Chrome新版11/旧アフィン5/新サーバー復元4項目を分割PASS。
独立APIの同一4試行と全native50配列/Project/要求/判断/RFが一致した。
P04-c-aはDONE。単独追跡版9/10と所有履歴操作、親P04監査はP04-c-bで継続する。

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

## 実ブラウザーと独立APIの受入

証拠根は `out/p04c-planar-browser-20261002/`。製品395ファイルを開始から監査終了まで固定した。
検証器は共通 `scripts/browser-session.mjs` を使い、Chrome153/Node24.18、外部要求0で実行した。

| 条件 | 成功証拠と範囲 |
| --- | --- |
| 要求4のProject/法則/回復方針・SI保持 | `browser-4/report.json`、保存して再読込、完全な要求一致 |
| strict拒否 | 明示回復欠落はjobを割り当てず、重複法則キーはstrictサーバーで拒否 |
| 成功/最終細分 | PAUSED2から別jobでTUNED4、目標/mesh両gate、継承prefixの選択 |
| 所有地点/再開 | 同一checkpointを2回再読込、実中止の確認済み1試行を選択し別jobのPAUSED2へ再開 |
| 未確認 | 真の正方形縮退はUNVERIFIED、周波数null、対象場取込/再開を無効化 |
| 元場取込/表示 | 対象IDの実順位1、元polygon、U′=1 J/m、加速R/Q等N/A、実三場描画 |
| 旧アフィン版2 | `legacy-browser/report.json`の5項目、要求保存/再読込、PAUSED2からTUNED3、対象場描画 |
| サーバー復元 | `restarted-browser/report.json`の4項目、成功最終結果/元場、継承prefix、未確認nullを新server/新profileで復元 |
| 独立API一致 | `api-success/`の別実FEM4試行（61.034秒）とGUI4試行、取込元場を `native-audit.json` で照合 |
| 物理対照 | 最終TE10は解析141078803.7647059 Hz、相対差1.0703275159507086e-6（固定gate3e-6未満） |
| 元byte/資源 | 原prefixと再開prefixの全snapshot一致、実中止prefixの判断/native一致、395製品hash不変、browser/server終端 |

監査は4試行の全fields/mesh NPZ各10配列と最終取込10配列（計50）、Project/Case/全RFを完全一致で比較する。
要求/全判断・順序・statusも一致。保存元の再読込では専用readerが各nativeを物理復元する。
GUIダウンロードはruntime ownerを示す再生envelopeであり、単独所有disk形式ではない。
これらの再生は `replay_planar_tune`、workerの相対所有結果は `read_planar_tune` を用いる。
監査器は新固有値問題を解かない。APIとGUIの一致だけを一般離散化誤差保証とはしない。

`target-field.png`、`legacy-affine-field.png`、復元の`restored-field.png`を目視し、対象順位/単位/RF/三場表示を確認した。
新版11項目session1506、旧版5項目session53127、復元4項目session25370は全終了0。
API session83901、native監査session33079も終了0。server90303/76968はSIGINT正常終了0。
所有browser stateのslotディレクトリは空。sandbox内psをホスト不存在の証明には使用しない。

## 実行と失敗記録

```sh
node scripts/verify_gui_planar_piecewise_tuning.mjs --url LAUNCH_URL --out NEW_DIRECTORY \
  --workspace JOBS --request SUCCESS_JSON --cancel-request CANCEL_JSON --unverified-request UNVERIFIED_JSON
node scripts/verify_gui_planar_affine_tuning.mjs --url LAUNCH_URL --out NEW_DIRECTORY \
  --workspace JOBS --request AFFINE_JSON
node scripts/verify_gui_planar_piecewise_tuning.mjs --url NEW_LAUNCH_URL --out NEW_DIRECTORY \
  --resume-report PRIOR_REPORT
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src UV_CACHE_DIR=/tmp/superfish-ng-uv-cache \
  uv run --no-sync python scripts/validate_planar_piecewise_gui.py \
  --root out/p04c-planar-browser-20261002 --browser out/p04c-planar-browser-20261002/browser-4 \
  --api out/p04c-planar-browser-20261002/api-success --out NEW_AUDIT_JSON
```

最初のsandbox内loopback bindはEPERM/終了2。昇格したローカルサーバーで実操作した。
browser初回session99585は起動待ちReferenceError、2/session7873は旧errorの誤判定、
3/session84849はファイル応答前の次入力による正しいstale拒否で終了1。各ログ/reportを保持し回収済み。
検証器の読込待ちをAPI応答counterへ修正し、同じ製品でbrowser4成功。製品のstale保護は保持する。
初回audit/session42718はruntime exportへowned-disk readerを誤用して終了1。
監査器だけをruntime replayへ修正し、session33079で同じ結果の全照合がPASS。
数値許容差・製品srcはこの操作受入中に変更していない。seed/全validateは実行していない。

自作の既存フォーム/所有選択/専用元場取込/検証器を再利用し、外部資料/依存/legacy参照を追加しない。
