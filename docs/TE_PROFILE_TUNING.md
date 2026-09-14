# TE一般profileの周波数調整

2026-09-15、開始HEAD `ee65a15`。D02他物理調整の非円筒TE経路を接続する。
受入条件は実FEMの形状変更、独立Maxwell尺度則、保存再開、TE物理・元セクター順位の保持、
最終細メッシュの目標差と粗細差の独立判定、実GUI/native一致である。

要求版1/2/3/7（7はprofile）で、正半径の区分線形profileとnormalized_profileを使用できる。
EφにR(z)/Rmaxを掛ける[体積重み付き追跡](TE_PROFILE_TRACKING.md)を採用する。
同じ端条件の閉PEC、一対称面の半領域、その鏡映結果を扱う。旧normalized_cylinderは一定半径のみ。
各生成候補の検証、TE native reader、N/A加速量、保存hashと失敗時の先行checkpoint保持は従来どおり。
曲線・階段形状、宣言変形のない明示メッシュ、組立は未対応。FEM核・RF核・許容差は変更しない。

新2テストは、全座標の寸法連動と局所半径のexp式を実FEMで変更する。
閉PEC/半領域/鏡映を2試行で止めて再開し、非細分試行のf×scale一定、N/A、最終細分を確認する。
局所半径例は同一FEMのpilotを目標とする経路検証であり、解析精度の独立証明とはしない。
初期baselineは未接続guardで失敗。接続後nr12/nz18では目標の10kHz条件を細分後に満たさず、
REFINEMENT_FAILEDとなった。診断の粗細差は59671.224Hz。nr32/nz48へ増し、許容差を維持して成功。
新2件51.729秒、関連48件94.247秒の分割検証がPASS。
関連範囲はTE tune/profile tracking、既存tune/coupled/polynomial/expression、GUI tune、tuning Jobs。

専用原寸/倍寸の鏡映局所半径式は各4試行、8実FEMでTUNED。
周波数・G・Q0・UとEφ/Hr/Hzの尺度則を別に検査し、最大相対差3.9337e-14。
TEの両R/QはN/Aを保持した。検証driverは初回の定数キー誤記をFEM前に訂正し、ログを残した。
Chromeは11項目PASS、4実FEM、外部通信0、製品336SHA不変。
保存再生、改変拒否、元要求復元、最終場取り込みとN/Aを確認し、結果画面を目視した。
最終粗細差3664.3188Hz、元セクター順位を表示する。

直接実行とGUIの全4試行、取り込み最終場の計5組で全native配列・全RF一致。
元81ファイル保持。全3GUI Jobがcomplete、専用サーバーはSIGINTで終了0。
成功比較12実FEMとは別に粗い診断4FEM、目標設定pilot2FEMを実行した。unit内部のFEMは別。
証拠はignored `out/te-profile-tuning-20260915/` の各log、native-validation.json、
fidelity.json、browser/report.json、gui-terminal-jobs.jsonと保存結果。

全suite/seedを再実行せず、hosted CIは観測していない。新たな外部資料・依存・旧実装資産は使用していない。
曲線TEの追跡/調整、非円筒の専用個別ID回復例、他物理調整とD03は残る。D02全体の受入ではない。
