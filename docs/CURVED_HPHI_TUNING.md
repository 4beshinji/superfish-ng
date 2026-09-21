# 曲線Hφの調整実行と明示ID回復（H13-c、受入済み）

`run_curved_hphi_tune`は元Projectから曲線候補を作り、各候補を独立したFEMで解く。全二次領域上のE/H追跡で個別IDを確認した場合だけ、その元周波数を探索に渡す。`assess_curved_hphi_tune`は順序付き元FEMから候補・対応・決定を再構築する。利用者が作成した追跡reportを証拠として受け取らない。

本APIはメモリ上の実行。所有保存、プロセス中止/再開、CLI/worker/GUIは後続H13-d/eで接続する。`max_new_trials`は完了したtrial境界で今回の実行を止める指定で、永続checkpointや途中FEMキャンセルではない。

## 要求と予算

専用format `superfish_ng_curved_hphi_tune`、版1、無次元`deformation`に限定する。元`CurvedHphiCase`のProject、全P2形状則、上下限、目標Hz、目標/粗細差の各許容値、parameter許容値、最大探索回数、初期IDと対象ID、追跡controls、最終細分段数、要素/DOF/求積点予算、明示`identity_recovery`（なしはnull）を要求する。旧直線調整版の読取仕様は変更しない。

JSON型、有限数、bool、未知キー、重複キー、正の増加bounds、IDと計算guard、元物理、全形状節点を厳密に検査する。形状生成/FEMより前に最終/比較メッシュの要素・DOF・元chartのpair数・最大求積点数を検査する。回復controlsも独立に同じ予算検査を受ける。scalar射影の256列上限も明示検査する。上下限の形状を検証し、途中候補の妥当性は生成時にも検証する。

## 探索と受入

最初の候補も自己比較によって個別ID・有限スペクトル・guardを確認する。上下限を計算し、対象IDの周波数で目標を挟めば二分する。探索候補の比較親は最初の確認候補、最終細分の親は採用した探索候補とし、どちらも元Projectの形状則から独立生成する。

追跡が未確認、個別IDが不明、E/H位相不一致、guardとの連結などの場合、周波数と目標誤差はnullにして停止する。比較予算例外は`MESH_LIMIT`、そのほかの比較拒否は`UNVERIFIED`。元の周波数に尺度補正や転送係数による代用を行わない。

探索で目標許容値を満たしても、同じ完全二次領域を細分して新しいFEMを解く。最終周波数が目標許容値内か、採用探索候補との周波数差が別のmesh許容値内かを別判定する。両方を満たした場合だけ`TUNED`、それ以外は`REFINEMENT_FAILED`。二メッシュ差は離散化誤差上界でもRF収束保証でもない。bracket不足・反復数上限・parameter幅上限も独立した終了理由として保持する。

## 明示回復

`identity_recovery`は`latest_resolved_trial`または`fixed_trial`と専用controlsを指定する。通常比較がPASSで、なお個別IDが不明なID集合を持つ場合だけ回復へ進む。guardで未確認になった比較をanchorで迂回しない。

anchorは現在より前で、実際に個別IDを確認できた候補だけ。探索/最終細分の親とanchorは別のindexで記録する。anchorから現在候補の元E/Hを新たに比較し、個別IDが解決され、かつ継承した全ID集合のメンバーと一致する場合だけ回復成功とする。真の縮退や比較未分解を、cluster閾値変更だけで解決したことにはしない。成功時も連続経路の一意なbranch保証は主張しない。

## 検証記録・来歴

証拠は`out/h13-curved-tuning-20260921/`。初期redは新API欠落であり、既存FEMの数値誤答ではない。最初の製品実行試験は、テスト生成値にNumPy scalarが残っていたため厳密JSON検査で拒否された。テスト側を通常のJSON数値へ直し、製品側の型検査は維持した。

新試験は`test_curved_hphi_tuning test_curved_hphi_tuning_recovery`。穴付き実FEMの一様/非一様変形、目標/粗細差の別判定、解析TEMの周波数とcos場、真の縮退停止、未来anchor拒否、guard迂回禁止、元係数/周波数の改変拒否を対象にする。分割実行の終端と失敗を含む記録は以下に示す。

関連は旧直線調整要求、旧回復の形状/予算契約、新曲線候補の構築前予算検査。標準実行は`OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-uv-cache uv run --no-sync --python .venv/bin/python python -m unittest -v <modules/cases>`。既存FEM/seed TM/物理許容差は変更しない。全suite/所有保存/Hosted CI/GUIの受入ではない。

既存の二分決定核、厳密JSON型検査、回復policy/ID集合整合検査を使用し、曲線形状・同P2細分・元E/H追跡へ接続した。独立解析対照は既存の同軸Bessel根とTEM式で、ソルバー代用ではない。新外部資料・依存・legacy参照なし。

## 検証中に確認した拒否と対処（2026-09-22）

- `after-json-fixed.log`：初期3件のうち要求/guard検査は成功。一様変形したn=2穴付き例は最終粗細差1,608,644.0638 Hzで、宣言した相対0.001相当の目標/mesh許容値を両方超えた。`REFINEMENT_FAILED`が正しい動作で、テストの成功期待を修正した。物理許容値は変更しない。初期3件の実行は299.649秒、終了1。
- `nonuniform.log`：n=2の軸方向20%変形は個別ID未確認（93.525秒、終了1）。`nonuniform-diagnostic-run.log`と`nonuniform-trial-1.json`で、電場の対角overlapが約0.896/0.896、磁場が約0.900/0.899で既定0.9を下回ることを確認した。guard群の越境ではなく個別場の対応不足であり、周波数はnull。追跡閾値は緩めず、成功受入用の変形区間を10%にする。
- `mesh-diagnostic.log`：同じ相対0.001基準で元メッシュを細かくした。一様1.1倍時の粗細差はn=3で875,565.85 Hz（不合格）、n=4で578,119.81 Hz（その例の606,674.74 Hz許容値内）。非一様形状にも余裕を持たせるため、成功受入例はn=5で検証する。
- `nonuniform-refined.log`：n=5比較空間は既定2,000,000求積点予算を超え、FEM前に拒否した（36.998秒、終了1）。予算を4,000,000へ明示増加して再実行する。物理許容値や点の間引きは変更しない。
- `recovery-json-fixed.log`：直線極限の明示二次幾何による解析TEM回復と真の縮退停止の2件、280.391秒、終了0。探索/最終細分のanchor分離、cos場overlap>0.999、未来anchor拒否を含む。
- `reader.log`：厳密読取・元係数/周波数改変拒否の追加1件、55.179秒、終了0。`related.log`：旧要求/回復予算と曲線候補予算の5件、8.320秒、終了0。

実際に曲げた例の回復は`curved-recovery.log`で未確認となり、期待したTUNEDに未達（263.521秒、終了1）。`curved-diagnostic.log`では各trialの元nativeと全診断を保存して拒否理由を調べる。この未達は成功の証拠とはしない。後述の診断でテストの物理的前提を調べ、成功例も独立に確認した。

`coarse-refusal.log`は、粗い穴付き例の正しい最終不合格と二つのgateの独立性を確認（1件、242.592秒、終了0）。同じ実測trialに対する決定核の検査であり、目標を後から変更した履歴を調整成功とは扱わない。

`curved-diagnostic.json`では、shear=1/64 m⁻¹の値0.99候補は探索時のanchor回復に成功していた。しかし直線TEM式の目標から約899,610 Hzずれており、次の探索へ進んでいた。`curved-target-diagnostic.log`で、元nativeのTEM状モードと直線cos場をshear移送した対照のoverlapは約0.99363、直線TEM式との相対周波数差は約0.000374と測定した。曲線固有場を厳密な直線TEMと同一視したテスト期待が不適切だった。

曲線回復の成功受入例では、同じshearを保ち、明示boundsを[0.8,1.12]、通常側の保守的cluster幅を0.06とする。anchor側のcontrols、overlap/求積/物理許容値は不変。値0.96付近の元曲線FEMから、独立cos対照でTEM状場を確認して目標を定める。これは合成試験の数値目標の指定で、実行器が解析式や補正値でFEMを代用するものではない。直線TEM式は近似対照として相対1e-3、移送cos場はoverlap>0.999を別検査する。実行記録は`curved-fem-target.log`。

`curved-fem-target.log`：実曲線の探索/最終細分でのID回復1件、180.451秒、終了0。候補ごとの近似TEM周波数/cos場、実中点が弦上にないこと、anchor index [1,2]と元個別IDを確認した。未達だった直線式目標の実験は上記のとおり別証拠として保持する。

## H13-c条件別監査（受入済み）

| 元カードの条件 | 現在の証拠と判定 |
|---|---|
| 元Projectからの明示曲線形状変数 | [全P2形状則](CURVED_HPHI_SHAPE.md)：全頂点/中点、元Project不変、二尺度・二次shear、厳密要求を確認済み |
| 加速座標 | 同資料：端点/位相原点の明示移送、beta保持、軸外拒否。最終細分でも同一経路を保持 |
| 同P2領域での最終細分 | [元候補/比較空間](CURVED_HPHI_TUNE_TRIALS.md)：二段root chartの完全被覆・丸め・質量保存と、穴付き実FEMの探索→最終細分IDを確認済み |
| 過去確認anchorによるID回復 | 解析TEMと実曲線で探索/最終細分の回復、親とanchorの分離、未来anchor拒否を確認済み |
| 未確認周波数を評価しない | guard、真の縮退、20%変形のoverlap不足で周波数/目標誤差をnullにして停止 |
| 穴付き実FEMの目標/粗細差を別判定 | 粗い例のREFINEMENT_FAILEDと別gateを確認。n=5非一様10%変形は`nonuniform-budgeted.log`でTUNEDを確認（1623.573秒、終了0） |

全行の証拠を確認し、H13-cを受入とする。H13-d/eの所有保存・中止/再開・CLI/worker/GUIは本監査に含めず、親H13/全goalは継続する。


## 最終記録

`nonuniform-budgeted.log`：穴付きn=5、非一様な軸方向10%変形の実FEM調整1件、1623.573秒、終了0。値1→1.1→1.05→同1.05の最終細分でTUNED。元領域の体積は変形値に比例し、周波数の推測尺度補正は1のまま、最終参照幾何は採用した元候補と一致した。目標/mesh許容値は元周波数×0.001を維持した。4,000,000点は計算予算で、求積点の省略や数値許容値の緩和ではない。

新8件の成功証拠は、`after-json-fixed.log`内の要求/guardの2件、`reader.log`1件、`coarse-refusal.log`1件、`nonuniform-budgeted.log`1件、`recovery-json-fixed.log`2件、`curved-fem-target.log`1件。最初の集約実行には失敗があるため、集約全体が成功したとは扱わない。失敗理由を独立測定し、物理条件に合う試験期待・明示入力を修正した後、該当ケースの成功を確認した。数値製品コードは初回追加後に変更していない。関連5件は`related.log`で成功。全handleの終端を確認し、待機時間を理由に同じ試験を重複起動していない。

本受入はH13-cのメモリ上の調整契約まで。次は全元Project/nativeと追跡・回復履歴を所有して保存するH13-dへ進む。全suite、リリース、Hosted CI、GUIの受入を主張しない。
