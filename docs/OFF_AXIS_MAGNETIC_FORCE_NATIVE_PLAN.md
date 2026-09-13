# S05: 軸を含まない軸対称磁気力の保存・CLI

2026-09-13 JST。後続限定課題。未実装・未受入。

[軸方向力API](OFF_AXIS_MAGNETIC_FORCE_PLAN.md)の成功した線形スカラーOffAxisMagnetostaticCase P1/P2 nativeを、専用保存/再読込とCLIへ接続する。元5ファイルのSHA、ψの基準/係数、材料・電流・境界と求積次数を実FEMで検証する。平面力の[N/m]報告、軸接続r=0、B-H/反跳・曲線・失敗nativeを読み替えない。

要求は対象region IDs、元頂点のP1重み、必須virtual_work=nullまたは2..8個の正で厳密減少するtranslation_steps_m。トルク原点、断面回転、半径方向力などの未知フィールドを拒否する。力は全周Fz[N]のみ。応力の全セル寄与、元求積/+4診断、真空重み遷移を報告へ保持する。

仮想仕事を指定した場合は全±z変位Case、固定r座標/外部境界、積分電流∫Jphi dr dz[A]、全周ポテンシャル/エネルギー/源境界仕事[J]と係数SHA、刻みと−dΠ/dz[N]を保存する。nullを0や検証合格へ変換しない。求積・メッシュ・重み・差分の違いは精度上界ではない。

専用要求/報告version 1を厳密parseし、元native外に完全JSONを一時作成して非上書き公開する。明示元nativeから再求解し、応力/全変位を含む完全JSONを再計算・比較する。元/要求/報告の途中改変、単位/求積/基準ψ/Case/ポテンシャル/係数の改変、リンク、上書きと出力中断を拒否する。

CLIはanalyze-off-axis-magnetic-force RUN --request REQUEST --out REPORTとreplay-off-axis-magnetic-force RUN REPORT。完了0、不正入力/保存/改変2。軸対称の全周量、P1/P2、r>0と線形限定のcapabilitiesを明示する。平面の既存コマンドと材料失敗終了1は不変。

受入は非零の有限電流Lorentz力、電流/外部磁場反転、尺度/ψ基準変更、線形磁性体body、求積次数と仮想仕事あり/null、API/CLI全JSON/バイト一致、元ファイル不変を含む。標準回帰と既存周波数/RF差を確認後、専用保存API/CLIだけを限定受入する。軸接続・B-H/反跳の力、GUI受渡し、S05/全計画は未完。
