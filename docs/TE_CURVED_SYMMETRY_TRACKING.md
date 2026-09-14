# TE曲線の対称領域・鏡映比較

2026-09-15 JST、開始HEAD `625267b`。D02の曲線TE対称/鏡映接続のうち、
同一二次領域比較とアフィンProject変換を対象とする。
受入条件は両側の対称セクター一致、Eφと実体積重み、元セクター順位の保持、
全領域の場との一致、Maxwell尺度則、native保存再生および未対応変換の拒否。

TE曲線P2の半領域計算・鏡映・native読取は既存機能である。
今回、`curved_same_domain`と`affine_remesh`の一律拒否を、同じ端条件と
高々一つの対称端を要求する検査へ置換した。直接場と鏡映場の混在は拒否する。
鏡映場は全領域の体積で比較し、順位は元の対称セクター内の周波数順として保存する。
既存の直接閉PECレポートには新しい対称メタデータを追加しない。

`transform_curved_project`も固定RFの対称Projectと鏡映指定を保持する。
対称面を保存するため、比較・Project変換とも軸方向せん断は厳密にゼロを要求する。
二次境界の全被覆・パラメータ・係数一致と元メッシュ/履歴検査は維持する。
tune、Study、harmonic、piecewise/partitionの外側の未対応検査は残る。
本変更をそれらの利用経路やGUIの受入とは数えない。

## 検証

生記録は`out/te-curved-symmetry-tracking-20260915/`。
最初の起動は保存再生関数の名前違いによるimport errorでFEM未実行。
修正後の実装前2テストは旧拒否で5 errorsと、その帰結の順位収集1 failureを再現した。
同一領域接続後2件13.770秒PASS、アフィン変換を追加した最終3件18.547秒PASS。

新`test_te_curved_symmetry_tracking`はz_min/z_maxと電気/磁気対称の4組を検査する。
半領域と鏡映の粗細追跡、混在拒否、native再生/改変拒否に加え、
倍寸での周波数・全係数・U/G/Q0/壁損失の尺度則を分離する。
全領域FEM行列を別のdense固有値解法で解き、周波数と質量重なりを照合する。
これは独立した固有値解法との照合であり、別定式化や離散化精度の証明ではない。
尺度則と鏡映時のU/壁損失2倍、G/Q0不変は独立した物理不変量である。

関連チェックは分割で実行した。

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=tests:src .venv/bin/python -m unittest \
 test_curved_same_domain_tracking test_curved_affine_remesh_tracking \
 test_te_reflection test_curved_project_remesh test_te_curved_tracking
# 27 tests, 39.086 s, PASS
OPENBLAS_NUM_THREADS=1 PYTHONPATH=tests:src .venv/bin/python -m unittest \
 test_curved_project_transform test_te_jobs
# 14 tests, 6.134 s, PASS
```

専用native検証は4対称条件の原寸/倍寸で半領域8実FEMと鏡映保存、
全領域dense固有値計算4回を実施した。全8Jobの再読取と4保存比較の再生がPASS。
104ファイルのhash保持、尺度差最大4.007e-15、全領域周波数差最大5.996e-15を確認した。
質量重なりは丸め誤差内で1。電気対称の元順位1は全領域順位2、磁気対称は順位1であり、
対称セクター順位を全スペクトル順位へ読み替えていない。
[集約記録](../benchmarks/tuning/te-curved-symmetry-tracking-20260915.json)を保存した。

FEM組立や固有値解法は変更していない。full/seed validator、GUI、hosted CIは今回未実行。
新規外部資料・旧コード・旧バイナリは利用せず、既存の独自合成曲線fixtureとTE定式化を使う。
次はこの基盤をTE対称アフィンtune/Studyへ接続し、実利用経路を検証する。
D02と全計画goalは進行中のまま。
