# 平面RFの追跡付き周波数調整

2026-09-15：[専用GUI](GUI_PLANAR_TUNING.md)を接続・限定検証した。以下のGUI未接続表記は以前の段階の記録。

2026-09-15 JST、開始HEAD `e4fb07d`。D02/P2-02の「他物理の調整」のうち、
平面RFの実FEM・電場追跡・保存再開・最終細分をAPI/CLIへ接続する。
受入条件は、解析可能な寸法–周波数関係、実順位交差でのID保持、縮退時の周波数未評価、
範囲/予算/入力検査、失敗時の前回保存保持、目標と最終細分差の別判定である。

## 入力と計算

専用`PlanarProject`を使う`superfish_ng_planar_tune`要求版1。
既存の軸対称Caseへ変換せず、平面TEのHz/平面TMのEz、xy面積測度、ピーク位相、
単位長エネルギーJ/mと損失W/mを保持する。加速R/Qは非該当である。
共有するのは`tuning._decision`にある物理非依存の二分探索判定のみ。
幾何生成・固有値計算・場比較・native保存は既存の平面専用経路を使用する。

| 項目 | 契約 |
|---|---|
| `project` | 専用PlanarProject。矩形または明示単純多角形、TE/TM、P1/P2 |
| `parameter` | `uniform_scale`（無次元）、矩形の`/case/geometry/width_m`または`height_m`（m） |
| `bounds` / `parameter_tolerance` | 正の増加2値、同じ変数単位での二分停止幅 |
| `target_hz` / `frequency_tolerance_hz` | 目標cutoff周波数と正の許容差 |
| `max_trials` | 探索試行上限。受理候補の最終細分試行は別途最大1回 |
| `initial_ids` / `mode_id` | 初期の正周波数prefix帯域に付ける一意IDと対象ID。計算モード数より少なくし、上側guardを保持 |
| `controls` | PlanarTrackingControlsの全項目。場overlapと有限細分空間の分離診断を使用 |
| `refinement_levels` / `max_triangles` | 最終1〜8段の一様細分と要素予算。矩形はnx/nyを倍増、多角形は元番号の適合4分割 |
| `mesh_frequency_tolerance_hz` | 同じ対象ID・同じ形状の探索/最終細分周波数差の正の上限 |

各試行の形状を元要求から独立に生成する。矩形はnormalized_rectangle、
多角形は実試行値の比から導出した原点相似写像を使う。
最終細分は受理候補を親として比較し、異なる候補や最後に計算した形状を誤って基準にしない。
同じ物理電場の全成分を積分し、追跡bandと上側guardの重なり・未解決部分空間を検査する。
全個別IDが確認できなければUNVERIFIEDとなり、その試行には周波数値を渡さない。

最終判定は目標周波数の許容差と粗細周波数差の両方を要求する。
TUNEDはこの離散診断を満たす状態であり、連続形状間の枝同一性・物理誤差上界・大域的根の保証ではない。
一般アフィン/非アフィン形状法則、個別ID回復、専用GUIへの調整接続は後続。workerは[専用検証](PLANAR_TUNING_WORKERS.md)で接続した。
既存の平面Study/追跡GUIがあることを新調整GUIの完成とは扱わない。

## 保存とCLI

APIは`execute_planar_tune(request, directory, max_new_trials=None, checkpoint=None)`、
`read_planar_tune(path)`、`replay_planar_tune(document)`。
出力先は新規作成のみ。全試行のProject・native場・manifest・hash・実追跡・探索順序を再検証する。
前回の保存と要求が一致するPAUSED状態のみ再開可能。
実計算/検証/保存の例外時はFAILED記録を残し、失敗を周波数評価として利用しない。
入力の数値をJSON形式へ正規化し、NumPyの数値型由来の判定値を保存できない問題も防ぐ。

```sh
python -m superfish_ng tune-planar examples/planar/tuning.json --out out/planar-tune-new --max-new-trials 2
python -m superfish_ng resume-tune-planar out/planar-tune-new/checkpoint-002.json --out out/planar-tune-rest
python -m superfish_ng replay-tune-planar out/planar-tune-rest/checkpoint-004.json
```

CLI終了0はPAUSED/TUNED、未確認・未達等は1。例は合成矩形で、実機構造ではない。

## 検証

新`test_planar_tuning`4件は修正後30.200秒PASS。
初回25.833秒では3件成功、三角形1件がNumPy由来boolのJSON保存で失敗した。
入力正規化と書込前シリアライズを追加し、同じ4件で再検証した。

- TE矩形の幅0.18→0.22 m、高さ0.2 mで実順位を2→1へ追跡し、独立式c/(2a)で最終周波数を検査。
- 同じ保存場で別の1 Hz粗細要求がREFINEMENT_FAILEDとなり、目標達成とは分離されることを確認。
- 正方形への合流はUNVERIFIED、周波数/誤差ともnull。再生も一致。
- 入力/帯域guard/予算の拒否、保存改変・終端再開拒否、注入した計算失敗で前のcheckpointを保持。
- 直角二等辺三角形TMの原点2倍相似と4倍面積、独立Dirichlet式c√5/(2a)、最終細分・保存再生を確認。

直接利用先の`test_tuning`、`test_planar_tracking`、`test_planar_study`は24件20.748秒PASS。
計算核や共有判定の変更はなく、新機能とCLI分岐の影響をこの範囲で検査した。
full validator/seedを新たに実行していない。従来fullの結果を今回の全件合格とは表示しない。

専用記録は`out/planar-tuning-20260915/`、携帯可能な要求と集約結果は
[benchmark](../benchmarks/tuning/planar-tuning-20260915.json)。
矩形TEの幅0.30/0.34 mから二分点0.32 mを求め、最終細分まで4試行。
2倍寸法も同じ探索順序で0.64 mへ到達し、両方とも保存再開/再生後TUNED。
独立解析式に対する最終周波数相対差は両尺度で約3.202454e-6。
粗細周波数差は21891.756382226944 Hzと10945.87819135189 Hz。
目標/粗細の許容差は元寸法200 kHz、倍寸法100 kHzとして事前に宣言した。

相似2倍で周波数1/2、同じJ/m正規化でスカラー係数・E/Hが1/2、U/G不変、
Q0が√2倍、壁損失が2^(-3/2)倍となることを全4試行・3モードで確認した。
係数成分ごとの初回検査（相対/絶対1e-10）は、ほぼ零の6成分で失敗した。
最大絶対差1.648e-10に対し場振幅は約7000であり、成分ごとの相対値を物理誤差とは扱わない。
初回`run.log`と成分ごとの場比較失敗`verify-and-cli.log`を保持した。
別検証器で同じ8保存解を再利用し、質量内積ノルムとE/Hそれぞれのベクトル振幅に正規化した場差を
1e-10で検査した。後者は全要素の重心の実場で確認し、全点一様誤差上界とは呼ばない。
質量ノルム相対差の最大は1.479147e-14、E/Hベクトル場の最大正規化差は3.302069e-14。
RF尺度則の最大相対差は2.664536e-15。
初回成分検査の合格とは記載せず、benchmarkにもfalseを保存した。計算核・許容差の変更はない。

CLIは新規2試行で停止し、再開で二分/最終細分の2試行を追加、保存再生も終了0。
API/CLIの4組40 NPZ配列と全3モードのRF量が完全一致した。
専用固有値計算はAPI8＋CLI4＝12（unit内の計算は別）、108保存ファイルを保持。
全専用プロセスは終端回収済み。実行中の製品337ファイルSHAは不変。専用GUIは未接続である。

既存の平面物理・追跡数学と合成例を利用し、新しい外部資料・旧コード・依存は導入していない。
