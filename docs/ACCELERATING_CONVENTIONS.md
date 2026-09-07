# R01: 加速長・電圧区間・位相原点

2026-09-08仕様。v3 caseのrfに任意のactive_length_m、voltage_interval_m=[a,b]、
phase_origin_mを追加する。3つは独立した指定で、既定はL、[0,L]、0。
明示値は保存し、未指定値は既存canonical入力へ追加しない。v1/v2への新キーは拒否する。
Pythonで新指定を与えたCaseは明示Model付きv3へ昇格する。

active_length_mは正の有限値。[a,b]は有限な実数で0≤a<b≤L。
phase_origin_mは有限な実数（区間外も可）。bool/null/未知キーは受理しない。
入力値の変更でFEM場・周波数・蓄積エネルギー・壁損失を変えない。

V=∫[a,b] Ez_quadrature(0,z) exp(i ω(z-z0)/(βc)) dz。
Eacc=|V|/active_length。TTF=|V|/∫[a,b]|Ez_quadrature|dz。
R/Q二定義は|V|²/(ωU)、|V|²/(2ωU)を保つ。Uは常に入力領域全体のエネルギー。
Epk/Bpkも全実PEC面の推定値で、Epk/Eacc等の分母だけが指定に従って変わる。
積分端は軸メッシュ節点である必要はなく、区分線形場を端点で切って厳密に積分する。
位相原点は全体の複素回転で適用し、数値的に表現できない位相引数はエラーとする。

位相原点をΔずらすとVがexp(-iωΔ/(βc))倍となり、|V|/RQ/TTFは不変。
active lengthだけを変えるとEaccとそれを分母に持つピーク比だけが変わる。
near-zero電圧の判定は同じ区間の絶対値分母に対する既存1e-12基準を保つ。

新指定のある出力にvoltage_interval_start_m/end_mとphase_origin_mを保存し、
active_length_mには実際の加速長を出す。旧指定なしのRF辞書とhashは変更しない。
保存規約・円筒解析比較・GUIでも同じ設定を使い、読込時に黙って全長へ戻さない。

対称鏡映は明示加速長を2倍にする。明示電圧区間は対称面に接する場合に限り
鏡映した連続区間へ拡張する。z_min鏡映では[a,b]=[0,b]を[L-b,L+b]へ、
z_max鏡映では[a,L]を[a,2L-a]へ写す。対称面に接しない区間は二つに分かれるため拒否する。
明示phase_originは元領域の座標に追随し、z_min鏡映でLを加算、z_maxでは維持する。
未指定の場合は従来通り全空洞の[0,2L]、加速長2L、位相原点0。

受入は独立積分との比較、位相回転/加速長スケール不変量、低β・節点間で切った区間・
符号反転場のTTF、円筒解析とFEMの分離、半/全領域、保存・CLI・GUI往復。
位相回転/スケーリング検査は相対1e-12、区分線形の独立積分は絶対値分母を尺度に1e-10。
円筒FEMのf/RQ/Gは既存の個別ゲートを維持する。表面ピークの収束保証を追加しない。

## R01.S/I/V受入 — 2026-09-08

仕様c91d69d、実装7d621e6。test_accelerating_conventions.pyの6検査を追加。
未実装時の4検査の失敗を先に確認し、入力・区分線形積分・解析参照・保存・GUIを実装した。
全体位相回転と加速長スケーリング、符号反転場の任意区間積分、低β相当の大きな波数、
円筒p=0/1/3・β=0.03の独立quadrature、CLI保存後の円筒解析比較がPASS。
半領域鏡映は、鏡映場を使わず同じ全領域メッシュで固有値問題を解き直した結果とも一致した。

初回の半/全比較で異なる対角線を持つ生成メッシュを使った際、6.30e-7の差を検出した。
この同一離散化の検査では全領域メッシュを揃えて再計算し、許容差は維持した。
異なるメッシュ間の収束保証をこの一致だけから主張しない。

数値証拠: `out/validation-r01-final-20260908/validation.json`、PASS。
143 unittest中141合格・NGSolve参照環境専用2 skip。
O01の最終保存結果と円筒/非円筒の全modes辞書・case hashが完全一致。
既存の標準検証・基準・許容差は変更していない。

GUI証拠: `out/gui-r01-browser-accepted-20260908/report.json`、8操作検査PASS。
加速長71 mm、電圧区間[13,39] mm、位相原点−8 mmを入力し、計算、解析比較、
Project/Case書出、再読込、Study設定のSI往復を検証した。未編集値のSI精度も保持する。
外部リクエストなし、実行中のソース変更なし。レポートhashを現製品コードと再照合した。

初回 `out/gui-r01-browser-20260908/` は79 mmの区間端が40 mm掃引ケースの外に出るため拒否された。
39 mmへ変更した検査の `out/gui-r01-browser-valid-20260908/` は数値/保存操作まで通ったが、
撮影時のスクロール待ちでFAIL。検査スクリプトでfocusを外し、撮影位置を待機中にも指定して再検証した。
両失敗記録を保持し、入力制約・数値ゲートを緩めていない。人による操作性評価・他OSは別受入。

再現（出力は新しい名前、GUIは別端末）:

```bash
OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/validate.py --out out/validation-r01-new
.venv/bin/python -m superfish_ng gui --workspace out/gui-r01-new --no-browser
node scripts/verify_gui.mjs --url '表示されたlaunch URL' --out out/gui-r01-browser-new --acceleration yes --io yes
```

R01のnative F/I/O/N/Wを受入。C02の旧入力は依然BETA=1/KMETHOD=1/ZCTR=中央の部分集合であり、
旧の任意ZCTRや位相指定の変換を受け入れた意味ではない。対応範囲の拡大はC02/C03/C04で別検証する。
