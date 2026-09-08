# 通常RF結果の連続離散ピーク評価

2026-09-08、直前基準add9938。保存された直線P1/P2・二次曲線P2の結果から、
PEC辺全体の連続離散ピーク上下界を評価するAPI/保存/CLI/GUI。
元のRF推定値・保存形式・数値核・規格化規約は変更しない。

## 操作

通常の計算結果を開き、モードの順位を選び、「選択した保存場のピークを評価」を押す。
Epk [V/m]、Hpk [A/m]、Bpk [T]、Epk/Eacc、Bpk/Eacc [mT/(MV/m)]について、
元の保存RF推定値と連続離散上下界を並べて表示する。保存RFにない値は「未評価」、
有意な加速電場を確認できない規格化比は「未定義」。ゼロで埋めない。
角診断、保存エネルギー、Eacc、規約、対象場のhashを詳細欄で確認できる。

「検証済みピーク評価を保存」はサーバーが返したJSON文字列そのものを保存する。
ページ再読込後は同じ保存結果と順位を開いて評価JSONを読み込む。
別のジョブ/順位の文書は拒否する。結果・順位を変えると前評価を消去し、
以前のモードの応答が遅れて届いても新しいモードへ表示しない。
改変された評価・元場を拒否した場合は直前の検証済み評価を維持する。

```bash
OPENBLAS_NUM_THREADS=1 python -m superfish_ng assess-rf-peaks out/run \
  --mode 2 --out out/rf-peaks-new.json
python -m superfish_ng replay-rf-peaks out/rf-peaks-new.json
```

APIは `rf_peak_assessment.assess_rf_peaks(run, mode=0)`、`save_rf_peaks`、
`read_rf_peaks`、`replay_rf_peaks`。APIのmodeと文書mode_indexは0始まり、CLI/GUIは1始まり。
この保存結果内の順位を指定し、永続的な追跡IDを推定しない。
CLI成功の終了値0は離散場評価/再検証の成功であり、物理精度合格ではない。

## 数値と保存契約

schema_version=1、document_type=rf_discrete_surface_peak_assessment。
元場・Case・RF・完了manifestを検証し、直線はK/M・固有対・規格化・RFを再構築、
曲線は既存のnative readerで幾何・固有対・RFを再検証する。新しい固有値計算は行わない。
[直線極値](AFFINE_SURFACE_EXTREMA.md)・曲線極値の既存有理数/Bernstein評価を使う。
relative_tolerance=1e-6、max_boxes_per_edge=10000を明示保存し、探索失敗を標本値で代用しない。

E/Hの上下界からBをμ0倍、規格化比をEaccで割り、Bpk/Eaccはμ0×10^9/Eacc倍として
外向き丸めする。元のrfとconventionsを保持し、二つのR/Q規約、SI単位、peak phasorを変えない。
過去のNG曲線保存形式でピーク列がない場合も、保存場から評価できる。
この場合、加速電圧が有意かどうかは既存曲線RF核で再計算するが、元のRF列を書き換えない。
入力・文書の未知フィールド、JSON重複キー、不正な順位、文書/場の改変は拒否する。

statusは常に `DISCRETE_BOUNDS_ONLY`。mesh_convergence=UNASSESSED、
geometry_approximation_assessed=false、physical_error_bound=null。
元多角形または解析曲線の角診断を添えるが、診断の通過は物理的正則性の証明ではない。
再入角があっても有限要素内の離散場は囲い込めるため、離散上下界とSINGULAR_GEOMETRYを併記する。
物理ピークの細分評価は[表面収束評価](AFFINE_SURFACE_CONVERGENCE.md)・
[曲線収束評価](SURFACE_CONVERGENCE.md)・[版3適応](ADAPTIVE_SURFACE_STOPPING.md)の別経路。
単一メッシュ評価を収束済みとは扱わない。

## 検証

着手前618件中616合格・2 skip（366.787秒）。追加5検査PASS（7.984秒）。
直線P1/P2の保存エネルギー4倍→絶対ピーク2倍・規格化比不変を確認した。
曲線native再検証・CLIは固有値計算を禁止して確認。
再入角、文書/元場改変、GUIの別順位/重複JSON拒否、過去のNG曲線RF形式も検査した。
初回の改変テストが既存nullをnullへ変更していた点はテストデータを修正。
旧形式曲線のピーク列欠落で失敗することを確認してから対応した。

実Chrome13検査PASS: out/browser-rf-peaks-expanded-20260908/report.json。
評価・モード変更・JSON完全一致・保存再読込・別順位拒否・再入角・元場変更拒否を確認。
実際のサーバー応答の受渡しだけを遅らせ、モード変更後の古い応答の破棄も確認した。
初回out/browser-rf-peaks-initial-20260908は閉じた取込欄へのクリックで失敗し、
検査スクリプトに展開操作を追加して再実行。数値条件や本体UIのクリック判定は緩和していない。
ブラウザーの外部HTTP要求なし。3取込ジョブは再検証済み・全て終了し、検証用GUIも停止した。

独立検証入口は `scripts/validate_rf_peak_assessment.py --out NEW`。
P1/P2円筒×尺度1/2を実計算し、解析f/RQ/Gとピーク比の両区間端点、相似則を検査する。
曲線場は規格化エネルギー4倍の不変量と保存再検証を確認する。
一般形状の物理精度・幾何近似誤差・効率・物理誤差上界は未受入。

独立検証 out/rf-peaks-physics-initial-20260908/validation.json はPASS。
P1/P2円筒×尺度1/2の実FEMで、f 1e-4・RQ/G 0.005・ピーク比両区間端点0.01の基準を満たした。
P1の最大解析RQ差2.867e-3、最大ピーク比端点差1.485e-3。
P2は同じ順に6.556e-7、3.680e-7。相似則最大相対差2.743e-14。
曲線の規格化エネルギー4倍に対する絶対ピーク2倍/規格化比不変の差は0。
保存再検証もPASS。単一メッシュ評価の状態はDISCRETE_BOUNDS_ONLYを維持する。
検証中のソース変更なし、最終ソースhash一致。

最終標準検証 out/validation-rf-peaks-20260908 は623件中621合格・2 skip（375.473秒）、PASS。
benchmarks/validationの全9モード・19量で周波数差ゼロ、RF/エネルギー差最大8.882e-16。
標準・独立物理・ブラウザーの記録hashは最終ソースに一致する。
Hosted CIや新規Wine比較を実行したという主張はしない。
