# 曲線Hφの元E/H場比較（H12-a、受入済み）

[H12-bの三水準診断と親H12監査](CURVED_HPHI_CONVERGENCE.md)も受入済み。

`curved_hphi_field_grams`は[H11の完全二次比較領域](CURVED_HPHI_COMPARISON.md)を使い、各nativeの元E/Hを元要素内で評価する。電場と磁場を混ぜず、それぞれprevious self、cross、current selfのGramを返す。調整や追跡ID、三水準の受入判定はここでは行わない。

## 検証と体積移送

入力は真空`CurvedHphiSolution`に限定する。Case・全二次幾何・DOFを再構築し、元の最低正周波数スペクトルと係数を検証する。正半径qの静的循環零空間は除外されたまま、軸接続uでは正則軸DOFを保持する。元spaceを変えた入力や、周波数/規格化を変更した保存場を拒否する。

`previous_cells/current_cells`の明示native制限と共通分割はH11の契約どおり。各積分点の3D測度は各側の`2*pi*r*det(DG)*det(DT)`で、全穴を除く元の領域を積分する。crossでは固定円筒成分に両体積密度の平方根を掛ける。これは現在領域への単位的L2移送と同じ内積であり、非一様写像をMaxwell解の座標変換や解析周波数倍率として扱わない。

二つの求積次数で各Gramを比較（正規化差1e-10）、元K/Mから得るE/H内積の再現（1e-8）、結合Gramの半正定値を別々に検査する。元の係数符号、周波数順位、蓄積エネルギー、RFを変更しない。electricの単位はV² m、magneticはA² m、peak exp(+i omega t)規約を保持する。

既定次数はmax(16, 両Caseの次数+4)、比較次数はさらに+4。明示次数は2〜36。pair・共通三角形・モード数・総積分点数を制限し、積分場配列は三角形群へ分割して保持する。全点×全モード×全成分の巨大な一括配列を作らない。格納分割で積分点を省略しない。予算/求積/元Gramの検査失敗は比較成功として返さない。

従来の直線比較APIは曲線を暗黙に受理せず、この専用APIと完全二次対応の指定を案内する。

## 独立検査

- 既知ベクトル場E=(0,1), Hφ=rを、合成shearと全穴を持つ両q/u領域で積分する。矩形から直接求めた∫2πrと∫2πr³に照合する。これは積分核だけの試験で、非固有場を公開APIへ通していない。
- 非一様shearと2倍の寸法では、既知場のelectric self倍率8、magnetic self倍率32、cross平方根倍率を独立に検査する。
- 両q/uの実FEMについて、二尺度のf倍率1/2と各self Gramの2U/ε₀、2U/μ₀、モード別正規化内積を検査する。
- 直線極限と独立native細分を、既存直線HφのE/H Gramに照合する。
- 保存nativeから再構築した非一様写像を正逆に比較し、crossの転置一致と元5ファイルのhash不変を確認する。係数/周波数/space改変、予算不足、低次数の求積不足を拒否する。

## 実行記録（2026-09-21）

`out/h12-fields-20260921`にrawを保持する。変更前は未実装APIのimportで失敗。初期4件は15.411秒PASS、追加1件は5.184秒PASS、両handle終了0。

既存`test_curved_hphi_saved test_hphi_field_overlap test_hphi_convergence test_curved_hphi_comparison`の20件は66.586秒PASS、終了0。公開APIと物理式を変えずに格納batchを追加したため、新6件を再検査中（`bounded-storage.log`）。独立既知積分を1三角形ずつ処理する対照も含む。旧比較/保存/診断コードはこの格納変更の影響を受けない。

実行方法は`OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-uv-cache uv run --no-sync --python .venv/bin/python python -m unittest -v <modules/cases>`。新モジュールは`test_curved_hphi_field_overlap`。新規外部資料・依存・legacy参照なし。既存K/MのMaxwellエネルギー、独立合成shear、直線極限を使用する。seed TM・solver・許容差は変更していない。全suite/Hosted CI/GUI受入の証拠にはしない。

親H12のguard/順位判定と三水準f・場・RF診断はH12-bに残る。H12-aのGram再現を物理精度や親H12全体の受入とは扱わない。

格納batch変更後の新6件は21.882秒PASS、終了0。全検証handle終端。H12-aを受入、次はH12-b。
