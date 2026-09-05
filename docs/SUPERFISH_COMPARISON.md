# Wine版SUPERFISHとの照合 — 2026-09-05

既存Wine環境のAUTOFISHを実行し、独立したSuperfish-NGのFEM計算と比較した。
円筒2形状と合成非円筒1形状について、各ソルバーで3段階のメッシュを使用。
周波数・Q0・G・R/Q・通過時間係数・軸上電場および最終2メッシュ間の変化は、設定した受入基準を満たした。
角を持つ非円筒の表面ピーク電場には約14.8%の差が残り、ピーク電場の精度検証は未完了。

## 実行環境と条件

- Wine 10.0、既設 `C:\LANL\AUTOFISH.EXE`。SFOが出力した版は **7.17、2006-01-13 release**。
  インストーラー名の7.20と内部プログラムの版表示を区別する。
- Python 3.12.9 / NumPy 2.5.2 / SciPy 1.18.1。`OPENBLAS_NUM_THREADS=1`。
- 真空・軸対称m=0 TMの基本モード、全外壁PEC、β=1。
- SUPERFISHの銅抵抗率は1.72410 microOhm-cm = 1.72410e-8 Ω m。
  NGの導電率をその逆数に設定。SFO変数表のRHO単位表記だけに依存せず、末尾の明示単位を使用。
- NGの `nr=24,48,96`。`nz`は空洞の縦横比から設定。
  SUPERFISHの `dx=0.4,0.2,0.1 cm`。各コードが独立にメッシュを生成する。
- 全金属面をFieldSegmentsへ列挙して端板の損失も算入。
- 元の例題・既存の計算結果は上書きしていない。比較用入力を `out/` 内に作成した。

## 規約の統一

既存pillbox例題は `ZCTR=0` のためSFOが半セルとして扱い、T=0.2124791と報告していた。
今回は空洞全長をモデル化し、`KMETHOD=1, BETA=1, ZCTR=L/2` を明示した。
同じ `dx=0.2 cm` の再実行で周波数1529.88482 MHzは維持され、全セルのTは約0.7474598となった。
これは物理場の変更ではなく、通過時間積分に用いるセル・位相の定義を揃えた結果。

比較する量は次の定義に固定した。

| 量 | 定義 |
|---|---|
| 加速電圧 | SFOのE0 × 全長 × abs(T+iS) |
| R/Q accelerator | abs(Vacc)² / (ωU) |
| R/Q circuit | abs(Vacc)² / (2ωU) |
| Q0 | ωU/P。丸められた末尾Qより高精度な変数表のU・P・fから算出 |
| G | Rs × Q0 |
| 軸上電場 | 両者を蓄積エネルギー1 Jに換算し、固有ベクトルの全体符号を揃えてL2比較 |

SFOが書き出した軸上電場も別途Simpson積分し、SFOの加速電圧と0.1%以内で整合することを確認。
計算ソースの参照・翻訳・逆解析は行っていない。

## 最細メッシュでの結果

相対差は `abs(NG / SUPERFISH - 1)`。

| ケース | SUPERFISH f [MHz] | NG f [MHz] | 周波数差 | Q0差 | R/Q差 | 軸上Ez L2差 |
|---|---:|---:|---:|---:|---:|---:|
| Pillbox R75 mm / L80 mm | 1529.896590 | 1529.901098 | 0.000295% | 0.00756% | 0.06414% | 0.03397% |
| Pillbox R100 mm / L200 mm | 1147.423660 | 1147.425824 | 0.000189% | 0.00475% | 0.02079% | 0.01088% |
| 合成necked cell | 1271.757800 | 1271.817617 | 0.004703% | 0.00656% | 0.01369% | 0.02924% |

| ケース | SF Q0 | NG Q0 | SF R/Q [Ω] | NG R/Q [Ω] | SF G [Ω] | NG G [Ω] |
|---|---:|---:|---:|---:|---:|---:|
| R75 / L80 | 22909.564 | 22911.295 | 220.788053 | 220.646450 | 233.780863 | 233.798874 |
| R100 / L200 | 34170.299 | 34171.921 | 57.806802 | 57.794784 | 301.975541 | 301.990166 |
| necked cell | 31842.726 | 31844.813 | 95.394515 | 95.381458 | 296.260354 | 296.286742 |

実行前に設定したゲートは周波数0.1%、Q0/G/TTF 0.5%、R/Q 1%、軸上Ez L2 1%。
両ソルバーの最終2メッシュ間の変化も各量の同じ閾値以内であることを要求した。
基準を通すためのソルバー補正や許容差変更はしていない。
円筒2ケースは解析式とも比較し、JSONに両ソルバーの解析誤差を記録した。

## 未解決の表面ピーク電場

合成necked cellのEpk/EaccはSUPERFISH=2.42008、NG=2.77785で、NGは14.78%大きい。
折れ線角部のピークはメッシュ・片側微分・場の補間に敏感で、周波数やRF積分量の一致をもって正確とは判断しない。
この量は今回のPASSゲートに含めていない。丸め半径を固定した形状で個別に収束を調べる必要がある。
一方、円筒2ケースのEpk/Eacc差は0.009%未満だった。
今回の結果は3ケースの基本モードに限定され、多セル全モードや実機測定との一致を主張しない。

## 実行記録と再実行

正式な読み取り直し済み集約結果は `out/superfish-comparison-report-20260905/comparison.json`。
同ディレクトリの `comparison.png` に周波数・R/Qのメッシュ変化と軸上Ezの重ね描きを保存した。
生出力は `out/superfish-comparison-final-20260905/<case>/level-<n>/superfish/`。
対応するNGのJSON/CSV/NPZ/VTKは同階層の `ng/` にある。
集約レポートはSFOのバージョン行を再読して訂正し、数値が元の計算記録と全一致することを確認した。

```bash
source .venv/bin/activate
OPENBLAS_NUM_THREADS=1 python scripts/compare_superfish.py --run-legacy --out out/superfish-comparison-next
MPLCONFIGDIR=/tmp/superfish-matplotlib python scripts/report_superfish_comparison.py out/superfish-comparison-next --out out/superfish-report-next
python -m unittest discover -s tests -v
```

比較用スクリプトは既存の `run-superfish.sh` とWine環境を必要とする。
通常のNG計算・unittestはWineを実行せず、追加4テストは合成SFO fixtureで規約変換を検証する。全30件合格。
生のlegacy入力・出力・実行形式は配布ZIPに同梱しない。
