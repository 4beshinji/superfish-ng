# 幾何・表面場・適応細分の精度と費用

[全体索引と実行規則](README.md)に従う。本章のIDは親課題IDではなく、作業カードID。

各カードは原則1コミット。既存ファイルは調査・変更候補であり、全てを書き換える指示ではない。新設ファイルは本文で指定する。

## N01

### 幾何・表面場の受入ケースを固定する

- **親課題**：G03 / N03。**種別**：仕様。初期状態：未着手。
- **先行条件**：[B01](01-baseline.md#b01)
- **コミット件名案**：`docs: 幾何・表面場の受入ケースを固定する`
- **既存の入口・影響先**：`docs/G03_CURRENT_AUDIT.md`、`docs/SURFACE_CONVERGENCE.md`、`docs/CURVED_RF_NONSPHERE_COMPARISON.md`
- **実施内容**：既存球/楕円の成功を保持し、滑らかな非球形と丸めた再入形状、鋭角対照を追加する検証入力を定める。幾何3水準×各FEM3水準、場対応、独立参照の要否と参照入手経路を決める。
- **受入条件**：f 1e-4、R/QとG 0.5%、ピーク比1%の既存目標を維持し、場は専用仕様のゲートを引用する。形状ごとの基準値・独立性・限界を固定し、鋭角に有限ピークを要求しない。
- **確認方法**：文書/仕様/監査は差分と根拠・リンク・依存を確認。検証カードは本文指定の専用実行を行い、[共通検証規則](README.md#検証と完了報告)で報告する。文書更新だけでFEMを再実行しない。

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

## N02

### 幾何と表面場の独立比較器を拡充する

- **親課題**：G03 / N03。**種別**：実装。初期状態：未着手。
- **先行条件**：[N01](05-accuracy.md#n01)
- **コミット件名案**：`feat: 幾何と表面場の独立比較器を拡充する`
- **既存の入口・影響先**：`scripts/validate_geometry_surface_convergence.py`、`scripts/validate_surface_convergence.py`、`scripts/validate_curved_geometry_convergence.py`
- **実施内容**：新しい合成ケースを入力指定で受け付け、幾何差/FEM差/求積差/元場対応/ピーク上下界を別報告する。存在する参照は来歴を検査して再利用し、欠けた参照はUNVERIFIEDとする。
- **受入条件**：故意のピーク未収束・場不一致・幾何未確認で適切に失敗する。元の楕円成功報告の判定と一致し、検証器が自分の出力を独立参照として使わない。
- **既存の検査候補**：`test_surface_convergence`、`test_affine_surface_convergence`。変更した契約に直接依存するケースを選ぶ。新機能の独立検査は別途追加する。
- **検査コマンドの出発点**：

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v test_surface_convergence test_affine_surface_convergence
```

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

## N03

### 非球形と丸め形状の物理精度を検証する

- **親課題**：G03 / N03。**種別**：検証。初期状態：未着手。
- **先行条件**：[N02](05-accuracy.md#n02)
- **コミット件名案**：`test: 非球形と丸め形状の物理精度を検証する`
- **既存の入口・影響先**：`scripts/validate_geometry_surface_convergence.py`、`docs/G03_CURRENT_AUDIT.md`、`docs/SURFACE_FIELD_DIAGNOSTICS.md`
- **実施内容**：N01の各系列を専用validatorで実行する。必要な独立現代ソルバー/許可済みブラックボックス比較は別環境と別成果物にし、両側細分を記録する。製品修正が必要なら最小の失敗不変量を再現する修正コミットを挟む。
- **受入条件**：各滑らかな例で連続2区間のf/場/RF/ピークと幾何不変量を満たす。失敗例と費用を保持し、未達を閾値緩和で解消しない。独立参照なしなら物理参照の行を未確認に残す。
- **確認方法**：文書/仕様/監査は差分と根拠・リンク・依存を確認。検証カードは本文指定の専用実行を行い、[共通検証規則](README.md#検証と完了報告)で報告する。文書更新だけでFEMを再実行しない。

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

## N04

### N03とG03の受入範囲を確定する

- **親課題**：N03 / G03。**種別**：監査。初期状態：未着手。
- **先行条件**：[N03](05-accuracy.md#n03)、[C03](06-compatibility.md#c03)
- **コミット件名案**：`docs: N03とG03の受入範囲を確定する`
- **既存の入口・影響先**：`docs/G03_CURRENT_AUDIT.md`、`docs/SURFACE_CONVERGENCE.md`、`docs/IMPLEMENTATION_STATUS.md`
- **実施内容**：G03の構築10/診断13までの既存証拠、旧NT=2/3変換、N03の幾何/FEM/独立参照を要件表へ対応付ける。新設N03_ACCEPTANCE.mdに一般保証でないことと適用範囲を記録する。
- **受入条件**：旧入力、滑らかな表面量、特異/未確認表示の必須行に証拠がある。離散ピーク上下界を連続問題の誤差上界とは呼ばない。
- **確認方法**：文書/仕様/監査は差分と根拠・リンク・依存を確認。検証カードは本文指定の専用実行を行い、[共通検証規則](README.md#検証と完了報告)で報告する。文書更新だけでFEMを再実行しない。

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

## N05

### 適応細分の精度対費用の比較条件を固定する

- **親課題**：N04。**種別**：仕様。初期状態：未着手。
- **先行条件**：[N01](05-accuracy.md#n01)
- **コミット件名案**：`docs: 適応細分の精度対費用の比較条件を固定する`
- **既存の入口・影響先**：`docs/ADAPTIVE_REFINEMENT.md`、`docs/CURVED_ADAPTIVE_REFINEMENT.md`、`tests/test_adaptive_refinement_cost.py`
- **実施内容**：円筒/球の既存対照に加え、局所細分が必要な滑らかな形状を選ぶ。同じ初期領域/次数/量/精度目標で、一様と適応のDOF・壁時計・メモリ・全域確認費用を比較する。
- **受入条件**：以前の球で適応優位がなかった事実を残す。精度達成と効率改善を別条件にし、比較回数・測定環境・予算を実行前に固定する。普遍的優位を完了条件にしない。
- **確認方法**：文書/仕様/監査は差分と根拠・リンク・依存を確認。検証カードは本文指定の専用実行を行い、[共通検証規則](README.md#検証と完了報告)で報告する。文書更新だけでFEMを再実行しない。

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

## N06

### 適応と一様細分の比較を実行する

- **親課題**：N04。**種別**：実装。初期状態：未着手。
- **先行条件**：[N05](05-accuracy.md#n05)
- **コミット件名案**：`feat: 適応と一様細分の比較を実行する`
- **既存の入口・影響先**：`scripts/validate.py`、`src/superfish_ng/curved_residual_indicator.py`、`src/superfish_ng/curved_rf_adjoint.py`
- **実施内容**：新設scripts/validate_adaptive_efficiency.pyで固定ケースの一様/適応を同じ条件で比較する。選択/追跡/求積/保存/全域確認の時間を測り、ボトルネックを特定する。
- **受入条件**：両経路の独立物理精度と費用を報告する。誤差対DOF曲線と誤差対時間を分け、前処理を片側だけ除かない。未達/予算超過も出力する。
- **既存の検査候補**：`test_adaptive_refinement_cost`、`test_curved_adaptive_refinement`。変更した契約に直接依存するケースを選ぶ。新機能の独立検査は別途追加する。
- **検査コマンドの出発点**：

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v test_adaptive_refinement_cost test_curved_adaptive_refinement
```

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

## N07

### 測定された適応処理の不足を修正する

- **親課題**：N04。**種別**：条件付き実装。初期状態：未着手。
- **先行条件**：[N06](05-accuracy.md#n06)
- **コミット件名案**：`fix: 測定された適応処理の不足を修正する`
- **既存の入口・影響先**：`src/superfish_ng/curved_residual_indicator.py`、`src/superfish_ng/curved_rf_adjoint.py`、`src/superfish_ng/curved_marked_refinement.py`
- **実施内容**：N06の失敗または律速がある場合に限り、指標・選択・再構築共有の一箇所を選び修正する。新しい計算法なら独立不変量を先に追加する。複数原因はN07-原因名の別コミットに分ける。
- **受入条件**：同じケース/精度目標で前後比較し、場/RFと親子質量保存を維持する。改善が不要/得られない場合は採用なしの判断を記録し、数値目標を緩めない。
- **既存の検査候補**：`test_curved_marked_refinement`、`test_curved_refinement`、`test_curved_adaptive_refinement`、`test_adaptive_refinement_cost`。変更した契約に直接依存するケースを選ぶ。新機能の独立検査は別途追加する。
- **検査コマンドの出発点**：

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v test_curved_marked_refinement test_curved_refinement test_curved_adaptive_refinement test_adaptive_refinement_cost
```

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

## N08

### 適応の一般ケース・保存・N04受入を確認する

- **親課題**：N04 / O02。**種別**：実装。初期状態：未着手。
- **先行条件**：[N07](05-accuracy.md#n07)
- **コミット件名案**：`feat: 適応の一般ケース・保存・N04受入を確認する`
- **既存の入口・影響先**：`docs/CURVED_ADAPTIVE_REFINEMENT.md`、`docs/ADAPTIVE_REFINEMENT.md`、`src/superfish_ng/gui_adaptive_refinement.py`
- **実施内容**：変更した選択/停止が保存再開とGUIにも一致することを確認し、N04_ACCEPTANCE.mdを作る。既存固定履歴・選択移送・大規模表示の証拠は再利用する。
- **受入条件**：対象物理量の精度/費用/全域確認、上限未達表示、実中止再開を記録する。効率の改善範囲と悪化範囲を明示し、要件未達なら親を閉じない。
- **既存の検査候補**：`test_gui_adaptive_refinement`、`test_adaptive_refinement_jobs`、`test_curved_adaptive_refinement`。変更した契約に直接依存するケースを選ぶ。新機能の独立検査は別途追加する。
- **検査コマンドの出発点**：

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v test_gui_adaptive_refinement test_adaptive_refinement_jobs test_curved_adaptive_refinement
```

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。
