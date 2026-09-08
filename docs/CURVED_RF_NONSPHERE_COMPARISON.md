# RF適応版5の非球形・両尺度対照

2026-09-09。RFA-6の検証記録。合成回転楕円体の固定二次写像領域を対象とする。
測定された実機形状ではない。解析体積は独立な幾何検査であり、RF量の絶対誤差上界ではない。

## 条件と再現

`scripts/validate_curved_rf_nonsphere.py` は[既存版4対照](CURVED_NONSPHERE_COMPARISON.md)の
受入済みvalidationと両尺度reportの一致・hashを記録し、例題requestの一致を確認する。
版番号と全solve回数上限以外は変えない。軸方向半径0.16 m、半径方向0.08 m、
尺度2は全長を2倍・規格化エネルギーを4倍にする。初期80要素の写像は同一。
周波数1e-4、R/QとG 0.005、Epk/EaccとBpk/Eaccの区間差0.01を維持する。

```sh
OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/validate_curved_rf_nonsphere.py \
  --out out/curved-rf-nonsphere-expanded-20260909 \
  --reference out/curved-nonsphere-spatial-search-20260909 --max-events 48
```

出力先は毎回新規にする。referenceは以前の自作FEMで検証済みの数値reportであり、
今回のコードで参照場を再計算したとは扱わない。追加一様対照は各尺度164,481自由度。
五量を独立に比較し、全イベントの親子Ritz、積分確認、固定領域体積、尺度則も検査する。
分岐する確認解と局所解を、実行順で直接Ritz比較してはいけない。

計測は初期plan生成から最終checkpoint保存までの全workflow。
不採用確認のsolve、RF選択、追跡、再構築、保存、診断用体積積分を含む。
solve単独の合計も別記する。過去の版4・一様確認時間は参考比較であり、
同一プロセスで交互に測った速度試験ではない。

## 上限12回の結果

`out/curved-rf-nonsphere-initial-20260909` は両尺度ともLEVEL_LIMIT。
版5では不採用の確認も全solve上限へ算入するので、版4の12採用水準とは異なる。
12回の最後は2,032要素の確認、最後の採用解は508要素。
尺度1/2の時間は124.582/124.566秒。全イベント構造一致、Maxwell五量差の最大5.089e-13。
未達を成功へ変更せず、初回validationと実出力を保持した。

## 48回上限の結果

検証中。許容差・要素上限を維持し、実solve回数の予算だけを増やす。
尺度1の途中から、別作業ツリーでGUI費用表示の実ジョブ・実Chrome・標準回帰を並行した。
長い確認後評価の所在を調べるためGDBを一度接続したが、この環境ではPythonスタックを
取得できず直ちにdetachした。これらを含む観測時間であり、専有環境の速度試験ではない。
全体の親N04、一般形状精度、一般効率の受入はこの限定対照と区別する。
