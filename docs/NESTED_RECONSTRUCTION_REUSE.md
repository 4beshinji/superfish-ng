# 曲線親子追跡で共通履歴を一度だけ再構築する

2026-09-14。N04残件2の、RF確認・追跡に要する処理時間を改善する。
対象は同じ元Caseと弦メッシュから履歴を真に延長した`nested_curved`。
異なる初期分割の比較や一般適応効率の受入ではない。

## 計測と受入条件

変更前`e445a05`の自作コードと保存済み回転楕円体の親/一様確認場を用いた
cProfileでは、RF指標全体2.713秒のうち`_nested_transfer`が2.003秒だった。
この時間にはプロファイラーの費用を含む。求積則の生成よりnative再構築が支配的だったため、
今回の変更をその重複除去に限定した。
元の計測は`out/quadrature-reuse-20260914/profile-before.log`に保持する。
この出力先名は調査開始時の仮称であり、求積実装を変更したという意味ではない。

受入条件は、同じ読込済み入力に対する転送行列・全幾何配列・係数・履歴・
追跡報告・RF指標の完全一致、独立質量積分の保存、strict入力と改変拒否の維持、
実行時間の測定による改善、保存追跡と適応計算の直接利用箇所の回帰である。

## 再構築と検査

従来は旧履歴を再構築し、新履歴を最初から再構築し、さらに旧空間から追加履歴を
再実行して転送行列を得ていた。同じ共通部分と追加部分をそれぞれ二度構築していた。
新処理は次の順序で同じnative操作を適用する。

1. 直接/鏡映の構成、履歴以外の元Case、元弦メッシュの一致と履歴の真の延長を確認する。
2. 両方の元メッシュを厳密に解析し、旧履歴だけを元メッシュから再構築する。
3. 旧解の全幾何配列・係数寸法・有限性・本質拘束・鏡映偶奇を照合する。
4. 追加のuniform/marked操作を一度ずつ実行し、新空間と合成転送行列を同時に作る。
5. 新解も同じ照合を行う。鏡映では再構築した半領域から全領域を別々に導出する。

入力の`solution.space`から幾何を構築したり、保存JSONの計算済み空間を信頼したりしない。
公開呼出しごとに元メッシュから再構築する。実行をまたぐキャッシュは追加しない。
旧levelsと順序付きuniform列の同値、固定split pattern、品質・要素予算、係数特徴数上限を保持する。
不正入力が複数の条件を破る場合、事前の履歴照合により最初の拒否理由が変わることはある。

最初の切り出しでは、新側のメッシュ解析を省略すると、JSONでは同じhashになる
tuple/listの型違反が通ることを追加テストで再現した。
新側の`mesh_from_dict`を保持して修正し、失敗ログを残した。
hash一致はstrict入力検証の代用にならない。二次幾何の重複構築だけを除去する。

質量内積、次数8の追跡求積、振幅正規化、QR/Cholesky、割当とクラスタ判定は不変。
RF随伴・局所残差作用・選択番号・五量の停止条件・ピーク区間・規格化も変更していない。
独立な次数12積分で、任意の粗いP2係数に対する
`P.T @ M_fine @ P = M_coarse`と定数場の転送を確認する。
これは表現された固定二次領域内の多項式質量保存であり、物理離散化誤差の上界ではない。

## 同一入力による比較

専用検証器は旧`nested_curved_tracking.py`だけを別名で読み、同じ数値ライブラリ・
RF/随伴コード・読込済みnative場に適用する。RF経路の旧呼出し差替えは検証器内だけ。
旧環境全体の再現ではなく、この再構築変更の比較である。
新しい固有値計算は行わない。solve直後とnative読込後のλの丸め差を完全一致の基準へ混ぜない。

```
git show e445a05:src/superfish_ng/nested_curved_tracking.py > out/NEW/nested_before.py
OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/validate_nested_reconstruction_reuse.py \
  --evidence out/curved-rf-goal-initial-20260909 \
  --baseline-module out/NEW/nested_before.py --out out/NEW/paired
```

出力先は未使用の場所を用意する。旧モジュールは本プロジェクトの自作ソースに限定する。
今回の最終証拠は`out/nested-reconstruction-reuse-20260914/paired-final/validation.json`。
45.855秒、3形状×各3回の旧/新交互計測がPASS。数値テストとの同時実行は避けた。
全報告と転送が完全一致し、両対称半領域を鏡映した転送/追跡も完全一致した。
質量形式の相対差最大1.5531e-15、定数転送の最大差0。

| 保存場 | 親/確認DOF | RF旧中央値[s] | RF新中央値[s] | RF旧/新 | 再構築旧/新 |
|---|---:|---:|---:|---:|---:|
| 合成回転楕円体 | 391/1501 | 1.80848 | 1.17957 | 1.5332 | 2.0025 |
| 電気対称半球 | 89/329 | 0.36355 | 0.24247 | 1.4994 | 1.9790 |
| 磁気対称半球 | 120/451 | 0.51465 | 0.34165 | 1.5064 | 1.9859 |

公開追跡全体の旧/新比は順に1.7639/1.7275/1.7390。
これはローカル3観測の中央値であり、一般形状や適応全工程の速度保証ではない。
旧モジュールSHA256は`d2cf14caa0a7e2b497d50432f1b5d22381284ff2f4acd1e06ea5d7c2061cd2e5`、
`e445a05`のgit内容と一致する。検証中のソース系とnative入力は不変。
strict解析補修前の比較も`paired/`に保持し、最終証拠と区別する。

## 回帰と検証範囲

最終実装に対する対象は41unit、全てPASS。単一の全件実行ではなく、次の2実行の合計である。

- `test_nested_curved_tracking`：9件7.377秒。共通marked→uniform履歴への追加、
  独立質量形式/定数保存、両側の形状/係数/拘束、同hash型違反、鏡映偶奇、保存/クラスタ/予算を確認。
- 直接利用箇所：32件121.162秒。
  `test_curved_rf_goal_indicator`、`test_curved_adaptive_refinement`、`test_curved_adaptive_symmetry`、
  `test_curved_rf_adaptive_refinement`、`test_curved_prefix_reuse`、`test_rf_surface_refinement_policy`、
  `test_saved_mode_tracking`と`test_frozen_curved_refinement`の
  `test_nested_tracking_replays_an_appended_frozen_marked_step`を実行した。
  実FEM・全五量の個別ゲート・確認直後の再開・元親への局所分岐・改変拒否・CLI/JobManagerを含む。

初回の対象12件8.447秒PASSはstrict解析補修前。
追加した型違反1件は0.421秒でFAIL、補修後の9件へ含めた。
初回と補修後を混ぜて最終単一全件PASSとは記録しない。

既存専用検証器も最終実装で実行した。

```
OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/validate_nested_curved_tracking.py \
  --source-root out/curved-indicator-selection-set-20260908 \
  --out out/nested-reconstruction-reuse-20260914/native-tracking
```

円筒・楕円・双曲線の両尺度、18既存native場/12追跡組の全再検証と実CLI/replayがPASS。
追加の固有値計算はなく、両個別ID・次数12/8の質量形式・円筒解析五量を確認した。
質量形式の相対差最大1.2878e-15、五量尺度差最大1.0326e-13。
円筒の解析差最大はf=3.347e-7、RQ=2.340e-4、G=5.552e-7、E比=2.751e-4、B比=2.264e-4。
元の許容差を全て維持した。32unitとこの専用検証は並行したため、単独性能計測とは扱わない。
最終比較と専用検証の1045ソース系SHAが一致し、各実行中の全ソース・native入力が不変だった。
全コマンド・終了状態・ファイルSHAは`out/nested-reconstruction-reuse-20260914/acceptance.json`。

変更は曲線親子追跡の内部構築順に限定される。FEM/求積/定数/seed TM経路は変更していない。
直接利用箇所と専用物理不変量で影響を限定し、今回は全件`validate.py`・seed・ブラウザー・
Hosted CI・新Wine比較を実行していない。過去の検証を今回の全件合格へ読み替えない。

新規外部資料・依存・旧資産参照はない。既存のP2制限と独立積分を使った実装内の共有改善である。
一般再メッシュ、一般収束・精度/効率、N04全体と全計画は未受入。
