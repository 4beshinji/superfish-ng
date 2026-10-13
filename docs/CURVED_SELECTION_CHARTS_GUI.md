# 異なる初期接続への選択移送：GUI版2

2026-10-13 JST、ADD-N04-selection-charts-05 **DONE**。開始commit `4665561`。
引き継いだ未コミットのGUI二源と検証器を完成した。親N04と全計画goalは継続。
次は06の専用幾何・行列・6求解と保存/API/CLI/GUI受入。

境界の対応で「共通参照座標を明示」を選ぶと、変更前/現在の初期頂点順の二chartと
三角形上限を入力できる。参照座標と選択番号はraw JSONのままstrict server readerへ渡す。
版2は全文書を検証してから現在の対象段階へ選択を反映し、既存履歴操作でmarked段階を追加する。
入力Projectを保存移送文書から自動置換しない。参照被覆PASSは物理精度の保証ではない。

保存移送の再読込は全chart/組数/三角形予算を復元する。版1読込では新版欄を消去し、
旧方針へ戻る。検査中のchart/予算・対象Project/段階・手動選択変更は完了応答の適用を拒否する。
JSON欄は専用controls内で全幅表示とし、図と欄の目視確認を行った。

| 確認 | 結果・範囲 |
|---|---|
| 新版実Chrome | 43操作PASS、外部要求0・製品源不変。二policy、空contained、SVG番号/選択、全文書API一致、raw重複/非有限/float・bool ID、全域予算、途中応答、保存改竄、版1/2復元、marked履歴/保存を確認。FEM禁止guard四入口は全0 |
| 元版1検証器 | 無変更の18操作PASS、外部要求0・製品源不変。新worker求解1回、保存/RFと6656要素Canvas選択を確認 |
| HTTPと直接利用先 | 新transport2＋既存`test_gui_curved_mesh_selection`4の6個別PASSを分割受入。初回6件中5 PASS、NaN fixtureがchart配列長の拒否に命中した1 FAILを保全。座標内部へNaNを入れ直し、その1件だけ0.883秒・終了0 |
| 元nativeとの照合 | 全10 NPZ配列（全係数/f/P2節点/接続/タグ等）と全mode/RFが完全一致。mesh/軸CSV/VTKのbyte一致。Case JSON値一致。旧保存とのint/float表記差によるCase SHA・CSV beta表記とLinux kernel版の差を別記し、全ファイルbyte一致とは呼ばない |
| 差分・終端 | 元1440源の他1437はbyte不変。変更はapp.js/index.html/style.css、新源は検証器とtransport test。別作業の`scripts/review_scientific_validity.py`追加を監査で区別し、編集/コミット対象にしない。現snapshot1443/1229 Python源。両server/全worker/全browserは終了、browser slotは空 |

初回のProject比較はGUIの明示既定値（diagonal/0）と省略表記の差で停止した。
strict normalizeのProjectを比較する検証器へ修正した。続くpreview応答包みの取り違えと
keyboard focus式の引用符ERRORもrawへ保全し、製品の物理/数値/許容差を変更しなかった。
監査の過剰な全文書/byte一致要求は、上記の実差分を確認して数量・配列・metadataを別報告した。
成功済みunit/FEMを件数・hash更新のために再実行していない。

rawは`out/n04-selection-charts-gui-20261013/`。元20261008のfixture/失敗も保持する。
`acceptance.json`、`audit.py`、分割unit log、`browser-layout`43項目/画像、
`browser-v1`18項目/画像/全保存場、`server-terminal.json`とsource SHAを保存した。

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-uv-cache \
  uv run --no-sync python -m unittest -v \
  test_gui_curved_selection_charts test_gui_curved_mesh_selection
node scripts/verify_gui_curved_selection_charts.mjs \
  --url-file <起動URLファイル> --sources <独立Project/mesh/API文書のfixtureディレクトリ> \
  --out <未使用出力先>
```

検証のlocalhost bindはsandboxでPermissionErrorとなるため、許可されたローカルHTTP環境を使用した。
新科学核・依存・文献・旧資産参照なし。新seed/full/legacy/専用validator0。
06の新移送先markedの6専用求解・物理受入を05のGUI幾何証拠で代用しない。
