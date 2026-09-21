# 材料Hphiの所有追跡履歴と明示ID回復

最新進捗：[独立所有履歴](MATERIAL_HPHI_HISTORY.md)と[材料調整CLI/worker](MATERIAL_HPHI_TUNING_OPERATIONS.md)の基本操作検査まで成功。回復/最終細分の所有操作統合とGUIは残る。以下の初期段階の記録は当時の検査範囲を示す。

2026-09-22、H16-c。`MaterialHphiTrackingHistoryRequest`は順序付きの材料追跡pair、最大step数、任意の過去snapshot回復指定を宣言する。隣接pairの元native五ファイルが全bytes一致し、前段のIDまたはID集合を後段がそのまま継承することを要求する。各pairを材料E/H・有限スペクトルから再計算する。

`MaterialHphiIdentityRecoveryRequest`は過去の個別IDが確認済みのsnapshotと完全な材料比較要求を指定する。継承比較がPASSの未解決ID集合である場合だけ回復を試みる。履歴所有側でanchorの位置、元native hash、宣言IDを照合し、独立したanchor比較が継承集合を保つ場合だけ個別IDを採用する。元pairの未解決結果と回復eventを両方保持する。guard未確認や真の未解決集合を順位で埋めない。

`execute_material_hphi_history`は全pairの要求・Project・native・結果・manifestを新規出力へ所有コピーする。`read_material_hphi_history`は全祖先と回復を再生する。`extend_material_hphi_history`と`JobManager.extend_material_hphi_history`は既存履歴を変更せず、新規出力へ祖先ごとコピーして延長する。`JobManager.start_material_hphi_history`も専用workerを使う。最大step数到達または最終UNVERIFIEDなら延長を拒否する。

CLI:

```
execute-material-hphi-history REQUEST --steps PAIR... --out NEW_DIRECTORY
extend-material-hphi-history HISTORY NEXT_PAIR --out NEW_DIRECTORY
replay-material-hphi-history DIRECTORY
```

検証対象は保存された離散snapshot間の対応であり、縮退を通過する連続経路の枝IDや連続体誤差の保証ではない。

## 検査と来歴

`test_material_hphi_tracking_history`で非真空一様材料epsilon_r=4、mu_r=9の順位交換を用いる。独立したTEM場cos(pi*z/L)との材料質量内積一致を検査し、未解決集合・回復・guard拒否・native連続性・予算を分離する。所有移動、実延長worker、管理器再起動、元祖先bytes、回復結果改変拒否、公開CLIの実行/再生/予算拒否も対象。

新API未実装のImportErrorを確認してから実装した。公開CLI1件は74.797秒PASS、隣接する既存Hphi CLI/保存kind検査2件は7.725秒PASS（いずれも終了0）。`out/h16-material-history-20260922/`にtool終端記録を保存した。回復履歴3件は615.826秒PASS/終了0。新4件は分割検証であり、全handle/worker終端を確認した。全suite・seed validator・GUIは実行していない。既存自作の曲線履歴所有構造を材料専用比較へ接続した。新外部資料、依存、legacy参照なし。元FEM coreとseed TMは変更していない。H16-cの調整CLI/worker・回復操作、およびH16-d GUIは別工程として残る。
