# 可逆アフィン変換と異なる内部メッシュの平面追跡 開発経過

最終状態：明示多角形の厳密に可逆な宣言アフィン変換（せん断・異方尺度・鏡映・回転の合成を含む）と独立内部メッシュの元電場追跡を限定受入。要求/結果版6、余因子によるTE移送、正逆の元電場積分、完全保存再生・CLI/実worker/GUI・所有履歴を接続した。追加9unit、独立解析26条件、実Chrome9項目、標準全体とseed回帰を確認した。証拠と契約は[PLANAR_AFFINE_REMESH_TRACKING.md](PLANAR_AFFINE_REMESH_TRACKING.md)。以下の経過は実装判断の記録である。

## 背景

[相似変換＋独立内部メッシュの合成追跡](PLANAR_SIMILARITY_REMESH_TRACKING.md)（版5）は、宣言相似変換で前の境界節点列を厳密に写し、内部だけを独立に再メッシュする追跡を限定受入した。残件は「境界密度独立の一般合成・せん断・鏡映・任意変形・曲線・親P02」である。本工程はこのうち、厳密に可逆な一般アフィン写像（せん断・異方尺度・鏡映を含む）を版6として扱う。前版の要求/結果/再生の意味は変えない。

## 受入条件

- 要求/結果版6、写像名 `polygon_affine_remesh`。`linear_xy` は有限2x2で厳密有理行列式が非零。旧版1〜5は不変。
- 宣言変換を前の境界節点列へ適用した結果、またはその厳密な逆評価を現在へ適用した結果が、binary64で完全一致すること。行列積・成分演算の両順を受理し、推定や許容差拡大をしない。向き反転時はポリゴン順序と三角形頂点順を正の向きへ正規化し、元のbarycentric座標で場を評価する。
- TEの現在の横電場は有効変換の余因子 `adj(E)=det(E)E^{-1}` で前枠へ戻す。TMはスカラー不変。3次/5次積分、正規化Gram、PSD、guard、縮退部分空間は版5と同じ意味を保つ。
- 反射は等長として周波数一致・解析Gram恒等を独立解析で確認する。異方矩形はCartesian解析則を照合する。せん断は厳密モーメントと多項式移送で確認し、厳密固有周波数や物理収束を受入に含めない。
- 保存/worker/CLI/履歴/GUIを接続し、改変・資源上限・誤宣言・非正則・境界不一致を拒否する。標準全体・seed回帰・旧版回帰を確認する。

## 実装

- `planar_tracking_affine_remesh.py`：`PolygonAffineRemeshMapping`（`linear_xy`、`translation_xy_m`、`inverse`、`max_candidate_tests`、厳密行列式符号、`transform_mesh`、`_scalar_transform_mesh`、`current_to_previous_linear`）と `polygon_affine_remesh_overlay`。向き反転時の正規化とbarycentric列の復元を行い、厳密交点分割は版4のsame-domainヘルパーを共有する。
- `planar_tracking.py`：要求/結果版6、写像の受理、余因子の受渡し、説明・スコープ・`physical_mapping`（宣言、`current_to_previous_linear`、`signed_determinant`、向き）を追加。
- `planar_tracking_jobs.py`・`model.py`：workerの事前検証、capabilityの版と説明、限界文の更新。
- GUI：写像選択「明示多角形：可逆アフィン変換＋異なる内部メッシュ」、a・b・c・d入力、移動・逆向き・候補上限、要求/結果の往復とURL復元。

## 試験と検証

追加9unitは、厳密JSONと版往復、行列積・成分順と反射の境界認識、独立内部・モーメント、向き反転のbarycentric復元、誤宣言・境界不一致・資源上限の拒否、余因子移送の点別恒等式（P2多項式）、反射の周波数一致と実FEM PASS、異方矩形の解析則と順位交差、縮退guard、保存workerと2段階の所有履歴を確認する。

独立解析（`scripts/validate_planar_affine_remesh_tracking.py`）は、右二等辺三角形の解析固有関数による反射（8条件）、矩形解析則による異方尺度（8条件）、順位交差（2条件）、せん断の多項式移送と厳密モーメント（8条件）、6つの拒否条件を別経路で確認した。反射は解析恒等残差最大2.221e-16、P2最終FEM cross最大1.038e-4、異方P2周波数最大8.785e-5、せん断P2移送2.908e-16。TM順位交差は帯域外像のためUNVERIFIEDを保持した。

GUIは実Chromeで、反射＋独立内部の追跡、宣言・余因子・向き反転の保存、要求/結果往復、元場の取込/表示、逆向き、履歴2段、不正写像の維持、URL復元の9項目を確認した。外部HTTP 0、実行中のsource不変を確認した。

標準検証は `out/validation-planar-affine-remesh-final-20260911` に保存した（956件、954合格、2skip、1513.289秒、source 548件不変）。seed9モード19量は周波数差0・最大相対差8.882e-16。既存の `.manager.lock` のResourceWarningは前段からの未解決事項として保持する。

## 残件

境界密度を独立に選べる一般の再メッシュ合成、非線形・多値変形、異なる多角形形状、曲線断面、親P02全体と全計画は未完である。二状態の数値対応を連続経路の同一性や物理誤差上界と扱わない。
