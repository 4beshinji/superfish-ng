# 相似変換と異なる内部メッシュの合成追跡 開発経過

最終状態：宣言相似変換の境界節点列を厳密に写し、内部だけを独立に再メッシュした平面追跡を限定受入。要求/結果版5、正逆の元電場積分、完全保存再生・CLI/実worker/GUI・所有履歴を接続した。追加8unit、独立解析16条件、実Chrome9項目、標準全体と既存数値回帰を確認した。証拠と契約は[PLANAR_SIMILARITY_REMESH_TRACKING.md](PLANAR_SIMILARITY_REMESH_TRACKING.md)。以下の経過は実装判断の記録である。

## 背景

[宣言相似写像](PLANAR_SIMILARITY_TRACKING.md)は相似な形状の追跡を、[同じ多角形の独立再メッシュ](PLANAR_REMESH_TRACKING.md)は同一領域の独立メッシュをそれぞれ限定受入した。両計画の残件に「形状変更との合成」があり、本工程はその合成を版5として扱う。前版の要求/結果/再生の意味は変えない。

## 最初の設計と浮動小数の反例（2026-09-11）

最初の試作は、前のメッシュ全体を宣言変換し、現在のメッシュと厳密交点分割する方式だった。境界の角（辺）は変換後も一致するが、辺上の中間節点の像は、変換後の両端を結ぶ弦の上にbinary64で厳密には乗らない。二つのメッシュの境界折れ線が互いに最大数ulpずれるため、有理数クリッピングでも境界に微小スリヴァーが残り、`intersections do not exactly cover every original element` で拒否された。再現は `out/planar-similarity-remesh-boundary-sliver-20260911` に保存した。失敗は実装の座標順・変換式の問題ではなく、独立に構成した二つの境界多角形を厳密に同一とみなせないことによる。

許容差を足す案は、このPJの「小さな領域差を許容差へ吸収しない」方針に反するため採用しなかった。代わりに、宣言変換後の前の境界節点列と現在の境界節点列がbinary64で完全一致することを要求し、内部の節点・対角線・接続だけを独立とする。これで両側の三角形の和集合は点集合として同一になり、厳密被覆が成立する。

以前の相似写像版3は、同じ次数・接続の四分割や変換後のメッシュ全体を既知の構築式と完全照合していた。版5は境界だけを厳密照合し、内部は任意の有効メッシュを許す。境界密度は独立に選べないことを制限として明記する。

## 実装

- `planar_tracking_similarity_remesh.py`：`PolygonSimilarityRemeshMapping`（`scale`、`rotation_radians`、`translation_xy_m`、`inverse`、`max_candidate_tests`）と `polygon_similarity_remesh_overlay`。境界サイクルを厳密比較し、厳密交点分割は既存のsame-domainヘルパーを共有する。
- `planar_tracking_remesh.py`：交差分割本体を `_same_polygon_overlay` へ切り出し、版4の挙動・エラー・候補予算の意味を変えずに再利用する。
- `planar_tracking.py`：要求/結果版5、写像の受理、TEベクトルの `current_to_previous_rotation`、回転不変の有限細分診断、物理写像メタデータ。
- `planar_tracking_jobs.py`・`model.py`：workerの事前検証、capabilityの版と説明。
- GUI：写像選択、尺度・角度・移動・逆向き・候補上限の入力、要求/結果の往復とURL復元。細分回数欄は合成方式では非表示。

## 試験と検証

追加8unitは、厳密JSONと版往復、境界・内部の独立認識、正逆・成分演算順、モーメント積分、誤宣言・境界不一致・資源上限の拒否、実FEMの周波数/回転/RF相似則、縮退guard、保存workerと2段階の所有履歴を確認する。

独立解析は右三角形の解析固有関数を宣言写像で前の枠へ戻し、正規化Gramが恒等であること（最大残差2.221e-16）と、FEM側の正規化Gram・周波数・G・Q・壁損失を別経路で照合した。P2最終水準の最大FEM Gram誤差1.038e-4、周波数相対誤差3.335e-4。粗い水準の誤差は保持した。

GUIは実Chromeで、独立内部メッシュの追跡、宣言と物理写像の保存、要求/結果の往復、元場の取込/表示、逆向き、履歴2段、不正写像の維持、URL復元の9項目を確認した。外部HTTP 0、実行中のsource不変を確認した。

標準検証は `out/validation-planar-similarity-remesh-final-20260911` に保存した（947件、945合格、2skip、1514.373秒、source 544件不変）。既存のTM/TE/平面回帰とsource hashも同実行で照合する。既存の `.manager.lock` のResourceWarningは前段からの未解決事項として保持する。

## 残件

境界密度を独立に選べる一般の再メッシュ合成、せん断・鏡映・任意変形、曲線断面、親P02全体と全計画は未完である。二状態の数値対応を連続経路の同一性や物理誤差上界と扱わない。
