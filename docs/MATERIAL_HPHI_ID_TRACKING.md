# 固定材料E/Hによる個別ID・部分空間追跡

2026-09-22。H15-cの専用Python追跡APIを実装。H15全条件の統合監査は継続中。仕様は[固定材料契約](MATERIAL_HPHI_TRACKING.md)、数値基盤は[元E/H](MATERIAL_HPHI_FIELDS.md)、[質量射影](MATERIAL_HPHI_PROJECTION.md)、[有限スペクトル](MATERIAL_HPHI_SPECTRAL_RESOLUTION.md)。

`MaterialHphiTrackingRequest`版1は元二領域間の`comparison`、各元側から細分比較空間への`previous_resolution`/`current_resolution`という三つの完全な材料比較宣言を持つ。有限スペクトル用の二宣言はsame_domainのみ。各宣言の元partitionを実固有解と厳密照合する。全材料/領域のID全単射、固定epsilon_r/mu_r、全穴・界面の条件を引き継ぐ。

要求は追跡する正順位prefix数、既存個別IDまたは継承ID集合、比較次数、HphiTrackingControls、求積点/界面処理予算を明示保持する。未知キー、boolの版/整数、重複ID、個別IDと集合の同時宣言を拒否する。保存は新規ファイルのみで、元入力を上書きしない。

`track_material_hphi_modes(previous,current,request)`は元低順位正スペクトルを再検証し、計算済み上側guardを要求する。guard不足の入力はValueErrorで拒否し、個別IDを返さない。元領域ごとの有限スペクトル群と、材料重み付き元E/Hの部分空間対応を別に計算する。

電気・磁気の両対応集合が一致し、単一モードの係数位相も一致した場合だけ個別IDを付ける。周波数は各側の実FEM値を使い、幾何尺度による補正を推測しない。guardに接する群、射影/逆演算子未確認、不完全・曖昧な対応、E/H不一致ではUNVERIFIEDとして全個別IDをnullにする。継承集合は対応が成功しても勝手に分解せず、位相を単一値として付与しない。

返り値は版付き結果辞書で、元Case、三宣言、E/H Gram、有限スペクトル診断、guard、未確認理由、継承集合、位相を保持する。元場・規格化・RFを書き換えない。連続経路のID保証、連続問題の誤差上界、表面peak精度を示すものではない。所有履歴/調整/CLI/worker/GUIはH16の範囲。

## 検査と残る監査

`out/h15-material-tracking-20260922/before.log`で未実装APIのredを確認。`initial.log`は新3件、32.603秒PASS。`numbering-related.log`は番号/ID/native追加1件＋有限スペクトル関連3件、32.551秒PASS。新4件は分割実行証拠であり全suiteではない。全handle終了0。

- 二層TEMの低順位モードを独立分離解に照合し、全空間2倍尺度のf/2、E/H個別ID、元係数の不変、共通係数の符号反転を検査。
- guardに接する群ではUNVERIFIED/個別ID null。曖昧な継承集合は集合のまま保持し、位相を付けない。
- 要求の厳密保存読込・上書き拒否、元partition不一致、改変係数、未計算guard、求積予算不足を拒否。
- 正半径/穴付き軸で節点・セル逆番号、材料/領域列挙逆順と明示ID改名を施し、正逆追跡・cross転置・元native全ファイルbytes・全RFの不変を検査。

親H15を完了とする前に、追跡の独立再メッシュ、P1/P2真空極限、実縮退/順位交換、非一様写像、既存の片側界面物理・二層専用validatorとの条件別証拠を監査する。現時点の個別成功をこれら全部の受入と読み替えない。

既存自作のE/H二重判定・部分空間対応・guard群の構造を再利用し、材料専用のGram/有限K/M診断を接続した。新外部資料・依存・legacy参照なし。共有solverやseed TMの変更はなく、当該新検査と直接利用先を対象とし、全suite受入は主張しない。
