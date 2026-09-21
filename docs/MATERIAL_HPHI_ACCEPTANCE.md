# H15固定材料比較・追跡の条件別受入

2026-09-22。H15-a/b/cと親H15を受入。正値実数・等方・無損失の固定材料、直線P1/P2、正半径q/軸接続u、全穴・全材料界面というH14の範囲に限る。材料係数変更、曲線材料、複素/体積損失は追加していない。調整・所有保存/履歴・CLI/worker/GUIはH16に残り、P04/全計画を完了とはしない。

## 条件と実証

| 必須条件 | 対応する実装と証拠 |
|---|---|
| 完全な材料/領域対応、全界面・穴・元片側セル | [H15-a](MATERIAL_HPHI_COMPARISON.md)。7unitで独立面積/体積/界面長、正逆非一様写像、番号/ID改名、同係数別領域も保持。1 ULP界面ずれ、係数変更、不完全/誤対応を拒否 |
| 元E/Hのepsilon/mu重み、独立積分、正定性 | [元場Gram](MATERIAL_HPHI_FIELDS.md)。別Gauss/Vandermonde、元K/M、自己対角2U、joint Gram、二次数求積。非一様密度のcrossも独立積分 |
| q/uの材料質量射影、静的q、軸DOF | [質量射影](MATERIAL_HPHI_PROJECTION.md)。新6unitで定数質量、全行列独立積分、多項式保持、粗視化損失、直交条件/Pythagoras、ゼロ列/underflow/予算拒否。真空行列への置換なし |
| 実材料K/Mの有限スペクトル | [有限診断](MATERIAL_HPHI_SPECTRAL_RESOLUTION.md)。dense比較固有値と固有基底残差、二層解析帯域/radial guard、尺度則、元解不変。定数q核を保持し、区間/射影未確認を隠さない |
| E/H一致による個別ID、集合とguard | [追跡API](MATERIAL_HPHI_ID_TRACKING.md)。二つの場で集合と位相を別照合。未計算guard拒否、guard交差時UNVERIFIED、継承ID集合を勝手に分解しない |
| 一様材料のf/E/H/B則 | 元`test_material_hphi`のepsilon=4/mu=9対照をH15-bで実行済み。新尺度検査では二層P1/P2のE/H/Bをs^(-3/2)で直接照合し、f/2は追跡検査で確認 |
| 真空極限 | H15-bのP1/P2・正半径/軸の場Gram・質量に加え、今回の専用材料solveと真空solveの追跡ID、guard、有限区間を照合 |
| 二層の実FEM/界面/場/RF | 独立二層解の3モードとradial guard、正逆/尺度/番号変更の実材料追跡。今回専用validatorの8二層例24モードでf、体積E/H L2、各領域エネルギー、全壁/壁別RFと細分改善を別判定。実FEMの片側H/法線D trace、製造区分多項式の片側微分/接線E・材料metadataも検査 |
| 独立再メッシュ/非一様写像/正逆 | 穴付き正半径/軸、区分epsilon=2/5・mu=3/7、独立対角分割、穴の半径方向区分移動で全IDとcross転置を確認。元領域ごとの比較空間を使用 |
| 実順位交換/縮退 | epsilon=4/mu=9の専用材料solveでTEM/Bessel解析周波数と照合。実順位交換でID順序を反転、解析縮退では集合だけを保持。正逆双方で確認 |
| 元native/RF/SI規約 | 節点/セル番号・材料/領域列挙・明示ID改名を含む追跡前後で全nativeファイルbytesと元全RF不変。壁mu0/二つのR/Q/N/Aは既存元解規約のまま。新規周波数/固有場を射影から捏造しない |
| 厳密入力と計算予算 | 三つの完全比較宣言、元partition binding、元低順位スペクトル再検証、未知キー/bool/重複ID/変更係数拒否。DOF、点、モード、界面上限で黙って省略しない |

## 今回の実行記録

共通runnerは`OPENBLAS_NUM_THREADS=1 PYTHONPATH=.:src:tests UV_CACHE_DIR=/tmp/superfish-uv-cache uv run --no-sync --python .venv/bin/python python`。

- `-m unittest -v test_material_hphi_tracking_integration`の初期2件：`out/h15-material-integration-20260922/initial.log`、158.654秒PASS/終了0。後から追加した尺度/界面検査を含む3件一括実行と読み替えない。
- `-m unittest -v test_material_hphi_tracking_crossing`の新2件：同ディレクトリ`crossing.log`、26.504秒PASS/終了0。
- `-m unittest -v test_material_hphi_tracking_integration.MaterialHphiTrackingIntegrationTests.test_original_material_scale_amplitude_and_one_sided_interfaces test_material_hphi.MaterialHphiTests.test_original_piecewise_polynomials_and_one_sided_material_metadata`：`amplitude-interface.log`、追加1件＋関連1件、2.230秒PASS/終了0。
- `scripts/validate_material_hphi_rf.py --out out/h15-material-physical-audit-20260922`：`physical.log`と出力`report.json`、48.095秒PASS/終了0。独立材料24例72モード＋二層8例24モード、24Case往復。最大相対差f=4.49e-14、片側場=2.82e-14、RF=1.61e-15（独立離散参照との差。二層連続解誤差とは別）。

全handle終端。validator実行中はsrc/tests/scripts/examplesを固定し、記録hashの一致を確認。終了後の追加は尺度/界面unitだけで、`physical-source-audit.json`が製品実装不変を確認する。既存H15-a/b/cの分割成功記録も各専用文書に保持し、同じ検査を数や完了文言のために再実行していない。

## 判断と来歴

追加した今回のsrc変更はなく、専用材料APIに対する不足していた統合・独立物理検査を追加した。独立Bessel/TEM数学と二層解は既存自作検証器のものを再利用し、新規外部資料・依存・legacy参照なし。共有FEM core/seed TMへの影響がないため、限定unitと材料専用validatorを実行した。全suite・release受入・GUI操作の証拠とはしない。

H15の対応は二つの離散物理状態間の元E/H対応であり、連続変形経路でのID一意性、連続固有値の認証区間、表面peak誤差保証を主張しない。H16はここで確認した材料契約を保って実調整、最終細分、中止/再開、全native/回復状態、UIのN/Aを接続する。
