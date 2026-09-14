# TE一般profileの体積重み付き追跡

2026-09-15 JST：[TE一般profile調整](TE_PROFILE_TUNING.md)をnormalized_profileへ接続。
非円筒の連動寸法・局所半径式、閉PEC/半領域/鏡映、保存再開と最終粗細判定を検証。
新2件51.729秒＋関連48件94.247秒PASS。専用尺度8FEM、Chrome11項目/4FEMがPASS。
5組native全配列/RF一致、元81ファイル保持。曲線TE・他物理調整とD03は残り、全goal ACTIVE。


2026-09-15、開始HEAD `103958e`。D02一般TE形状調整の前提として、
直線で区分線形の正半径profileにnormalized_profileを接続する。
受入条件は独立積分による重み確認、実FEM尺度則、端条件・物理の厳密な区別、native再生である。

写像は z=Lζ, r=ρR(Lζ)。軸対称体積要素は2πLR²ρ dρdζなので、
実EφにR/Rmaxを掛け、共通測度ρ dρdζで比較する。
定数2πLRmax²と真空誘電率は各モードの正規化で消える。両形状の軸方向節点の和集合で積分区間を分ける。
これは電場の点ごとの引き戻しで、連続的な物理枝や離散化精度を証明しない。

閉PEC、同じ側・種類の一対称面、その鏡映部分スペクトルを扱う。
通常/鏡映の混在、異なる端条件、TE/TM混在、曲線・階段形状は拒否する。
鏡映の比較は全領域profileを用い、順位は元セクター順と明記する。
TE native readerを用い、Hφへの読み替えはしない。TMの従来写像と円筒写像は保持する。

新4テストは、Eφ=rの独立解析overlap (7/3)/sqrt(31/5)、同一直線上の余剰節点、
非円筒のMaxwell尺度則と積分次数8/12、左右・電気/磁気対称・P1/P2の鏡映、native再生を検査する。
初期baselineはHφキーへの誤到達、対称面拒否、専用module不在で失敗した。
実装後の関連40件28.674秒は39成功、旧TE未対応写像テスト1失敗。
代替paired_meshに必須vertex_pairsがなく先行検査で拒否されたため、same_domainへ入力を訂正し当該1件が成功。
これは分割検証であり、単一40件PASSとは記録しない。許容差は変更していない。

専用 `out/te-profile-tracking-20260915/validate.py` は非円筒P1/P2・各原寸/倍寸の4実FEMを保存。
f、G、U、Q0、Eφ/Hr/Hz尺度を別に照合し、最大場差1.6431e-14、RF差8.5488e-15。
加速量N/A、native追跡再生も確認。解析積分とMaxwell尺度則は既存公開数理の直接導出で、外部資料は追加していない。
証拠は同outのbaseline.log、selected-tests.log、repaired-test.log、independent.jsonとnative保存。

FEM核・RF核は変更せず、関連利用先を検査した。全suite/seed/GUIは再実行していない。
hosted CIは観測していない。一般profileのTE tune接続、曲線TEと他物理の調整は引き続き必要。
