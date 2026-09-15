# 旧入力・出力・ブラックボックス比較

[全体索引と実行規則](README.md)に従う。本章のIDは親課題IDではなく、作業カードID。

各カードは原則1コミット。既存ファイルは調査・変更候補であり、全てを書き換える指示ではない。新設ファイルは本文で指定する。

## C01

### 旧曲線入力の変換仕様を確定する

- **親課題**：C00 / C02 / G03。**種別**：条件付き仕様。初期状態：未着手。
- **先行条件**：[B02](01-baseline.md#b02)
- **コミット件名案**：`docs: 旧曲線入力の変換仕様を確定する`
- **既存の入口・影響先**：`docs/LEGACY_INPUT.md`、`docs/COMPATIBILITY_BASELINE.md`、`src/superfish_ng/legacy_input.py`
- **実施内容**：確認できたNT=2/3の支持曲線・端点・枝・既定値・単位・角度・接線指定をnative円/楕円/双曲線へ対応させる。各項目の版/節と受理/拒否例を用意する。
- **受入条件**：既定値を推測せず、全受理例に独立の寸法/陰関数/接線/面積が定義される。資料欠落なら変換を公開せずC01の未確認行を保持する。
- **確認方法**：文書/仕様/監査は差分と根拠・リンク・依存を確認。検証カードは本文指定の専用実行を行い、[共通検証規則](README.md#検証と完了報告)で報告する。文書更新だけでFEMを再実行しない。

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

## C02

### NT=2/3のstrict読込と変換記録を追加する

- **親課題**：C02 / G03。**種別**：条件付き実装。初期状態：未着手。
- **先行条件**：[C01](06-compatibility.md#c01)
- **コミット件名案**：`fix: NT=2/3のstrict読込と変換記録を追加する`
- **既存の入口・影響先**：`src/superfish_ng/legacy_input.py`、`src/superfish_ng/conics.py`、`src/superfish_ng/cli.py`
- **実施内容**：確認済み部分集合だけ変換し、原入力の行/項目位置・明示値/既定値の出典・変換先を保存する。既存NT4/5と真空TM部分集合を保持する。
- **受入条件**：正常変換、枝/端点/単位誤り、未知/重複変数、不正形状を独立幾何で検査する。未対応変数を無視せず、旧初期部分集合の同一出力を確認する。
- **既存の検査候補**：`test_legacy_input`、`test_conics`、`test_curved_contour`。変更した契約に直接依存するケースを選ぶ。新機能の独立検査は別途追加する。
- **検査コマンドの出発点**：

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v test_legacy_input test_conics test_curved_contour
```

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

## C03

### 旧曲線変換の等価計算を検証する

- **親課題**：C02 / G03。**種別**：検証。初期状態：未着手。
- **先行条件**：[C02](06-compatibility.md#c02)
- **コミット件名案**：`test: 旧曲線変換の等価計算を検証する`
- **既存の入口・影響先**：`docs/LEGACY_INPUT.md`、`scripts/validate_curved_geometry_convergence.py`
- **実施内容**：旧入力からのNG Caseと独立作成したnative Caseで幾何・f・場・RFを比較する。Wineの対象例はC07に渡し、NG等価計算を旧版数値互換とは呼ばない。
- **受入条件**：元寸法/面積/体積/枝/接線と全保存量が一致する。幾何/FEM細分の証拠と旧入力の出典/配布可否を分けて記録する。
- **既存の検査候補**：`test_legacy_input`、`test_curved_saved`。変更した契約に直接依存するケースを選ぶ。新機能の独立検査は別途追加する。
- **検査コマンドの出発点**：

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v test_legacy_input test_curved_saved
```

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

## C04

### 旧テキスト出力とプローブの契約を固定する

- **親課題**：C03。**種別**：条件付き仕様。初期状態：未着手。
- **先行条件**：[B03](01-baseline.md#b03)
- **コミット件名案**：`docs: 旧テキスト出力とプローブの契約を固定する`
- **既存の入口・影響先**：`docs/INPUT_OUTPUT.md`、`docs/COMPATIBILITY_BASELINE.md`、`src/superfish_ng/sampling.py`、`src/superfish_ng/curved_sampling.py`
- **実施内容**：実際の後処理利用先ごとに必要なヘッダー・列・単位・桁・符号/位相・R/Q定義・線/弧/格子の標本位置を表にする。読込/書出の方向を明示し、バイナリ必須利用先にはテキスト移行の可否を記録する。
- **受入条件**：各出力例に読み手と期待量があり、未計算量/N/A表現が決まる。存在しない利用先への互換を約束せず、参照不足は未確認に残す。
- **確認方法**：文書/仕様/監査は差分と根拠・リンク・依存を確認。検証カードは本文指定の専用実行を行い、[共通検証規則](README.md#検証と完了報告)で報告する。文書更新だけでFEMを再実行しない。

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

## C05

### 必要なプローブ列とテキスト変換を実装する

- **親課題**：C03。**種別**：条件付き実装。初期状態：未着手。
- **先行条件**：[C04](06-compatibility.md#c04)
- **コミット件名案**：`fix: 必要なプローブ列とテキスト変換を実装する`
- **既存の入口・影響先**：`src/superfish_ng/sampling.py`、`src/superfish_ng/curved_sampling.py`、`src/superfish_ng/cli.py`
- **実施内容**：新設legacy_text.pyに確認済みテキストのreader/writerを追加する。必要な線/円弧/格子標本は元場APIを呼び、境界/材料界面の片側選択と未定義点を出力する。方向/形式ごとに別コミットC05-形式名に分ける。
- **受入条件**：独立既知場の全成分/複素位相/単位/桁の誤差、往復、不正ヘッダー/列/単位、N/Aを検証する。補間や表示平滑化で元場を置き換えない。
- **既存の検査候補**：`test_sampling`、`test_curved_sampling`。変更した契約に直接依存するケースを選ぶ。新機能の独立検査は別途追加する。
- **検査コマンドの出発点**：

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v test_sampling test_curved_sampling
```

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

## C06

### 旧後処理への受渡しを実証する

- **親課題**：C03。**種別**：検証。初期状態：未着手。
- **先行条件**：[C05](06-compatibility.md#c05)
- **コミット件名案**：`test: 旧後処理への受渡しを実証する`
- **既存の入口・影響先**：`docs/INPUT_OUTPUT.md`、`docs/COMPATIBILITY_MATRIX.md`
- **実施内容**：C04で特定した読み手にC05出力を実際に渡し、必要な図/列/数値処理を再現する。実行不能ならファイルと実行手順を残し未確認にする。
- **受入条件**：単なる自作reader往復に加えて対象読み手の成功証拠がある。f/場/RFの一致と、桁落ちの許容根拠、未対応バイナリの移行可否を記録する。
- **確認方法**：文書/仕様/監査は差分と根拠・リンク・依存を確認。検証カードは本文指定の専用実行を行い、[共通検証規則](README.md#検証と完了報告)で報告する。文書更新だけでFEMを再実行しない。

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

## C07-TM

### 機能別ブラックボックス比較を整備する：既存真空TMと曲線変換

- **親課題**：C04 / C00。**種別**：検証。初期状態：未着手。
- **先行条件**：[B03](01-baseline.md#b03)、[C03](06-compatibility.md#c03)
- **コミット件名案**：`test: 機能別ブラックボックス比較を整備する：既存真空TMと曲線変換`
- **既存の入口・影響先**：`scripts/compare_superfish.py`、`docs/SUPERFISH_COMPARISON.md`、`docs/COMPATIBILITY_BASELINE.md`
- **実施内容**：このコミットの対象は既存真空TMと曲線変換のみ。既存比較入口を使い、各確認済み機能の入力/設定/版/hash・モード対応・両側細分・実行上限/終了コード/失敗保存を版付きケース表へまとめる。各物理の実行はC07-親IDの別検証コミットとする。
- **受入条件**：各ケースのf・場・RF・表面量とF/I/O/N/Wの未実施を別判定する。旧結果再利用は新規実行数へ数えず、参照不能なら実行可能なデッキとUNVERIFIEDを残す。rawはignored out/のみ。
- **既存の検査候補**：`test_superfish_comparison`、`test_superfish_te_comparison`。変更した契約に直接依存するケースを選ぶ。新機能の独立検査は別途追加する。
- **検査コマンドの出発点**：

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v test_superfish_comparison test_superfish_te_comparison
```

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

## C07-TE

### 機能別ブラックボックス比較を整備する：軸対称TE

- **親課題**：C04 / C00。**種別**：検証。初期状態：未着手。
- **先行条件**：[B03](01-baseline.md#b03)、[D03](04-design.md#d03)
- **コミット件名案**：`test: 機能別ブラックボックス比較を整備する：軸対称TE`
- **既存の入口・影響先**：`scripts/compare_superfish.py`、`docs/SUPERFISH_COMPARISON.md`、`docs/COMPATIBILITY_BASELINE.md`
- **実施内容**：このコミットの対象は軸対称TEのみ。既存比較入口を使い、各確認済み機能の入力/設定/版/hash・モード対応・両側細分・実行上限/終了コード/失敗保存を版付きケース表へまとめる。各物理の実行はC07-親IDの別検証コミットとする。
- **受入条件**：各ケースのf・場・RF・表面量とF/I/O/N/Wの未実施を別判定する。旧結果再利用は新規実行数へ数えず、参照不能なら実行可能なデッキとUNVERIFIEDを残す。rawはignored out/のみ。
- **既存の検査候補**：`test_superfish_comparison`、`test_superfish_te_comparison`。変更した契約に直接依存するケースを選ぶ。新機能の独立検査は別途追加する。
- **検査コマンドの出発点**：

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v test_superfish_comparison test_superfish_te_comparison
```

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

## C07-planar

### 機能別ブラックボックス比較を整備する：平面TE/TM

- **親課題**：C04 / C00。**種別**：検証。初期状態：未着手。
- **先行条件**：[B03](01-baseline.md#b03)、[P09](03-planar.md#p09)
- **コミット件名案**：`test: 機能別ブラックボックス比較を整備する：平面TE/TM`
- **既存の入口・影響先**：`scripts/compare_superfish.py`、`docs/SUPERFISH_COMPARISON.md`、`docs/COMPATIBILITY_BASELINE.md`
- **実施内容**：このコミットの対象は平面TE/TMのみ。既存比較入口を使い、各確認済み機能の入力/設定/版/hash・モード対応・両側細分・実行上限/終了コード/失敗保存を版付きケース表へまとめる。各物理の実行はC07-親IDの別検証コミットとする。
- **受入条件**：各ケースのf・場・RF・表面量とF/I/O/N/Wの未実施を別判定する。旧結果再利用は新規実行数へ数えず、参照不能なら実行可能なデッキとUNVERIFIEDを残す。rawはignored out/のみ。
- **既存の検査候補**：`test_superfish_comparison`、`test_superfish_te_comparison`。変更した契約に直接依存するケースを選ぶ。新機能の独立検査は別途追加する。
- **検査コマンドの出発点**：

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v test_superfish_comparison test_superfish_te_comparison
```

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

## C07-hphi

### 機能別ブラックボックス比較を整備する：真空/内導体Hφ

- **親課題**：C04 / C00。**種別**：検証。初期状態：未着手。
- **先行条件**：[B03](01-baseline.md#b03)、[H13](02-hphi.md#h13)
- **コミット件名案**：`test: 機能別ブラックボックス比較を整備する：真空/内導体Hφ`
- **既存の入口・影響先**：`scripts/compare_superfish.py`、`docs/SUPERFISH_COMPARISON.md`、`docs/COMPATIBILITY_BASELINE.md`
- **実施内容**：このコミットの対象は真空/内導体Hφのみ。既存比較入口を使い、各確認済み機能の入力/設定/版/hash・モード対応・両側細分・実行上限/終了コード/失敗保存を版付きケース表へまとめる。各物理の実行はC07-親IDの別検証コミットとする。
- **受入条件**：各ケースのf・場・RF・表面量とF/I/O/N/Wの未実施を別判定する。旧結果再利用は新規実行数へ数えず、参照不能なら実行可能なデッキとUNVERIFIEDを残す。rawはignored out/のみ。
- **既存の検査候補**：`test_superfish_comparison`、`test_superfish_te_comparison`。変更した契約に直接依存するケースを選ぶ。新機能の独立検査は別途追加する。
- **検査コマンドの出発点**：

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v test_superfish_comparison test_superfish_te_comparison
```

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

## C07-material

### 機能別ブラックボックス比較を整備する：材料Hφ

- **親課題**：C04 / C00。**種別**：検証。初期状態：未着手。
- **先行条件**：[B03](01-baseline.md#b03)、[H16](02-hphi.md#h16)
- **コミット件名案**：`test: 機能別ブラックボックス比較を整備する：材料Hφ`
- **既存の入口・影響先**：`scripts/compare_superfish.py`、`docs/SUPERFISH_COMPARISON.md`、`docs/COMPATIBILITY_BASELINE.md`
- **実施内容**：このコミットの対象は材料Hφのみ。既存比較入口を使い、各確認済み機能の入力/設定/版/hash・モード対応・両側細分・実行上限/終了コード/失敗保存を版付きケース表へまとめる。各物理の実行はC07-親IDの別検証コミットとする。
- **受入条件**：各ケースのf・場・RF・表面量とF/I/O/N/Wの未実施を別判定する。旧結果再利用は新規実行数へ数えず、参照不能なら実行可能なデッキとUNVERIFIEDを残す。rawはignored out/のみ。
- **既存の検査候補**：`test_superfish_comparison`、`test_superfish_te_comparison`。変更した契約に直接依存するケースを選ぶ。新機能の独立検査は別途追加する。
- **検査コマンドの出発点**：

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v test_superfish_comparison test_superfish_te_comparison
```

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

## C07-static

### 機能別ブラックボックス比較を整備する：静的S01〜S05の確認済み範囲

- **親課題**：C04 / C00。**種別**：検証。初期状態：未着手。
- **先行条件**：[B03](01-baseline.md#b03)、[S01](07-static-and-integration.md#s01)、[S02](07-static-and-integration.md#s02)、[S03](07-static-and-integration.md#s03)、[S04](07-static-and-integration.md#s04)、[S05](07-static-and-integration.md#s05)
- **コミット件名案**：`test: 機能別ブラックボックス比較を整備する：静的S01〜S05の確認済み範囲`
- **既存の入口・影響先**：`scripts/compare_superfish.py`、`docs/SUPERFISH_COMPARISON.md`、`docs/COMPATIBILITY_BASELINE.md`
- **実施内容**：このコミットの対象は静的S01〜S05の確認済み範囲のみ。既存比較入口を使い、各確認済み機能の入力/設定/版/hash・モード対応・両側細分・実行上限/終了コード/失敗保存を版付きケース表へまとめる。各物理の実行はC07-親IDの別検証コミットとする。
- **受入条件**：各ケースのf・場・RF・表面量とF/I/O/N/Wの未実施を別判定する。旧結果再利用は新規実行数へ数えず、参照不能なら実行可能なデッキとUNVERIFIEDを残す。rawはignored out/のみ。
- **既存の検査候補**：`test_superfish_comparison`、`test_superfish_te_comparison`。変更した契約に直接依存するケースを選ぶ。新機能の独立検査は別途追加する。
- **検査コマンドの出発点**：

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v test_superfish_comparison test_superfish_te_comparison
```

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

## C07

### 機能別ブラックボックス比較を整備する（統合照合）

- **親課題**：C04 / C00。**種別**：監査。初期状態：未着手。
- **先行条件**：[C07-TM](06-compatibility.md#c07-tm)、[C07-TE](06-compatibility.md#c07-te)、[C07-planar](06-compatibility.md#c07-planar)、[C07-hphi](06-compatibility.md#c07-hphi)、[C07-material](06-compatibility.md#c07-material)、[C07-static](06-compatibility.md#c07-static)
- **コミット件名案**：`docs: 機能別ブラックボックス比較を整備する（統合照合）`
- **既存の入口・影響先**：`scripts/compare_superfish.py`、`docs/SUPERFISH_COMPARISON.md`、`docs/COMPATIBILITY_BASELINE.md`
- **実施内容**：各分割コミットの受入証拠を照合して親の残要件を更新する。コードの追加は各分割カードで実施する。
- **受入条件**：各ケースのf・場・RF・表面量とF/I/O/N/Wの未実施を別判定する。旧結果再利用は新規実行数へ数えず、参照不能なら実行可能なデッキとUNVERIFIEDを残す。rawはignored out/のみ。
- **確認方法**：文書/仕様/監査は差分と根拠・リンク・依存を確認。検証カードは本文指定の専用実行を行い、[共通検証規則](README.md#検証と完了報告)で報告する。文書更新だけでFEMを再実行しない。

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

## C08

### 新規変換と各物理の旧版比較を完了する

- **親課題**：C04 / C00。**種別**：監査。初期状態：未着手。
- **先行条件**：[C03](06-compatibility.md#c03)、[C06](06-compatibility.md#c06)、[C07](06-compatibility.md#c07)、[S06](07-static-and-integration.md#s06)、[L04](08-external.md#l04)
- **コミット件名案**：`docs: 新規変換と各物理の旧版比較を完了する`
- **既存の入口・影響先**：`docs/COMPATIBILITY_MATRIX.md`、`docs/COMPATIBILITY_BASELINE.md`、`docs/COMPATIBILITY_PLAN.md`
- **実施内容**：曲線変換、RF追加物理、静的材料/境界、必要な周辺機能の比較ケースをC07のドライバーへ追加する。原K行の全必須軸を数値/操作証拠へ対応させる。
- **受入条件**：未実施/対象外/失敗を合計PASSで隠さない。C00.VとC04を閉じるには対象版と全必須ケースが確認済みであること。外部待ちは未確認を保持する。
- **確認方法**：文書/仕様/監査は差分と根拠・リンク・依存を確認。検証カードは本文指定の専用実行を行い、[共通検証規則](README.md#検証と完了報告)で報告する。文書更新だけでFEMを再実行しない。

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。
