# ローカル開発と動作確認 — 2026-09-05

プロジェクトルートは `/home/sin/code/superfish`。seedを直下へ展開し、P0-00の環境整備と配布境界の修正を実施した。
この記録はローカル実行の検証であり、外部ソルバーや実測値との比較結果ではない。

## 配置・初回開発

- `src/superfish_ng/`、`tests/`、`docs/`、`examples/`、`scripts/`、`benchmarks/` をルート直下へ配置。
- `.venv/` にPython 3.12の開発環境と描画用依存を導入。CLI `superfish-ng` をeditable installした。
- 既存READMEを `README-legacy.md` として保存。既存環境や講義資料の移動・削除は行っていない。
- Gitを `main` ブランチで初期化。既存ローカル資産は `.gitignore` に列挙し、配布対象も明示した。
- `scripts/package.py` のルート全体の走査を、プロジェクトのファイル・ディレクトリ許可リストに変更。
  許可された場所のシンボリックリンク（ディレクトリ・リンク切れを含む）は読み込む前に拒否する。
- 配布の回帰テスト3件を追加。合成fixtureに対して元スクリプトが私的ファイルを混入することを再現し、修正版が合格することを確認。
- seed原本のmanifestは `benchmarks/seed/manifest.sha256` に保存。現在の作業ファイルのmanifestとは扱わない。

seed ZIPのSHA-256:

```text
d01e2a517e7d71aa1ed919c598399938186f506d3a29d78227df81882428e5fb
```

全77エントリのCRC検査と、展開直後のmanifest対象76ファイルのSHA-256検査が合格。

## 実行環境

Python 3.12.9 / NumPy 2.5.2 / SciPy 1.18.1 / Matplotlib 3.11.1。
Linux x86_64、`OPENBLAS_NUM_THREADS=1`。seedの固定バージョンと今回の環境は異なるため、実際の計算結果を比較した。
`requirements-reproduce.txt` はseed環境の記録として保存している。

## 検証結果

| 検査 | 結果 |
|---|---|
| 初期状態のunittest | 23件合格 |
| 変更後のunittest | 26件合格（既存23＋配布3） |
| `scripts/validate.py` | PASS、周波数・R/Q・Q0の全収束ゲート合格 |
| Pillboxの先頭6モード | 解析スペクトルとの許容差0.3%のゲート合格 |
| インストール済みCLIの例題実行 | pillbox 4モード、shaped cell 3モードを計算・出力 |
| 描画 | shaped cellの保存場からPNG生成、軸・凡例・見切れを目視確認 |
| 配布ZIP | 80ファイルのmanifestが合格。別ディレクトリに展開し、展開先のコードで26テストとpillbox 4モードの計算が合格 |

Pillbox TM010、`nr=nz=64`、4225節点での独立解析式との比較:

| 量 | FEM値 | 相対誤差 |
|---|---:|---:|
| 周波数 | 1147.426504 MHz | 1.0683e-6 |
| R/Q（accelerator） | 57.819843 Ω | 8.3640e-4 |
| Q0 | 34171.526655 | 9.9211e-7 |
| G | 301.990090 Ω | 4.5797e-7 |

seed同梱の `benchmarks/validation/` と同一条件の結果を比較した。
pillbox 6モードとshaped cell 3モードについて、周波数の最大相対差は2.67e-15以下、
R/Qは9.33e-15以下、Q0とGは5.11e-15以下、Epk/Eacc・Bpk/Eaccの推定値は2.51e-14以下だった。
FEM・RF実装を変更しておらず、この環境差による数値差は浮動小数点丸めの水準だった。
非円筒形状の角部ピーク値について収束保証を追加したものではない。

## 実行記録と再実行

今回の結果（`out/` はローカル保存・Git対象外）:

- `out/validation-baseline-20260905/`: 初回の検証。
- `out/validation-local-20260905/`: 変更後の検証。`validation.json` に環境・実行コマンド・source hash、
  `tests.log` に26件の結果、`pillbox_convergence.json` に解析値・誤差・合否を保存。
- `out/validation-local-20260905/shaped_cell.png`: 場の可視化。
- `out/pillbox-local-20260905/`、`out/shaped-local-20260905/`: インストール済みCLIによる実行。
  JSON・CSV・NPZ・各モードのVTKを保存。

```bash
cd /home/sin/code/superfish
source .venv/bin/activate
OPENBLAS_NUM_THREADS=1 python -m unittest discover -s tests -v
superfish-ng solve examples/pillbox.json --out out/pillbox-next
superfish-ng solve examples/shaped_cell.json --out out/shaped-next
OPENBLAS_NUM_THREADS=1 python scripts/validate.py --out out/validation-next
MPLCONFIGDIR=/tmp/superfish-matplotlib python scripts/plot_results.py out/validation-next/shaped_cell --out out/validation-next/shaped_cell.png
python scripts/package.py --out /tmp/superfish-ng-next.zip
```

再実行には未使用の出力パスを指定する。ZIPを別の空ディレクトリに展開した後は、
`python scripts/verify_manifest.py` でmanifestを検証できる。

配布検証では同じ`.venv`の依存ライブラリを利用し、`PYTHONPATH=src`で展開先のコードを指定した。
`superfish_ng.__file__` が展開先を指すことも確認した。別OS・別Python環境での動作確認ではない。

次の数値開発課題はP0-01（外部ソルバーによる独立照合）。この初回作業では未実施。
GUI、ParaView対話操作、外部ソルバー・実機との比較、Hosted CIは実施していない。
