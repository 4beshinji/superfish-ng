# 平面曲線の実FEM調整と元native再生

P09の専用調整API。P09と全123カードgoalは継続する。
`planar_curved_tuning.py` は元Cartesian P2 Projectから全検索試行を生成し、
元二次領域を固定して最終uniform細分を実求解する。
軸対称の重み/場/電圧規約を流用せず、共有するのは物理非依存の二分決定 `_decision` だけ。

## 要求と周波数の採用

format `superfish_ng_planar_curved_tune` / schema_version 1。
完全な版3 Project、dimensionless `deformation`、全closed intervalのproper affine法則、
元正帯prefixの初期IDと選択ID、元E/H追跡controls、最終level/全予算、
目標周波数・目標差許容値・粗細差許容値を明示する。余分なkey/不正型/他物理を拒否する。
固定U′、peak phasor、σ、元全六節点/PEC、per-length RF/N/A metadataは元Project/nativeに保持する。

要求時に最終native mesh、共通場比較の全sample、各側guardの全mesh/sample/dof、
元chartの自己・交差pair予算を検査する。回復controlsにも同じ最終予算を適用する。
予算不足ではFEM/出力directory作成前に拒否する。実比較で新たに未解決/予算不足になれば
元nativeを保持したUNVERIFIED試行とし、frequency_hz/target_error_hzはnullで停止する。

初回も元E/Hと有限guardを比較して全個別IDを確認する。
以後は実parent試行の元場から追跡し、個別IDが確認された元固有周波数だけを探索に渡す。
周波数順位をID名へ読み替えず、部分空間PASS/個別未確定だけでは周波数を選ばない。
optional recoveryは `fixed_trial` または `latest_resolved_trial` と完全controlsを持つ。
anchorは実prefix内の過去・完了・全個別ID確認済みtrialへ束縛し、
継承元場とanchor元場を再比較して全ID集合の整合を確認する。真の縮退やguard失敗は迂回しない。

最終細分でも同じ追跡/回復を行い、独立した二条件を判定する。

- 最終周波数と明示targetの差が `frequency_tolerance_hz` 以下。
- 最終周波数と採用した検索parentの差が `mesh_frequency_tolerance_hz` 以下。

両方を満たすとTUNED。一方でも未達ならREFINEMENT_FAILED。
粗細差は診断であり連続問題の誤差上限ではない。小さい固有残差も空間誤差の証拠にしない。
このAPIはRF/表面peakの収束証明を発行しない。

## 保存と再開

`execute_planar_curved_tune(request, new_directory, max_new_trials=None, checkpoint=None)` は
各実native jobと `checkpoint-NNN.json` を新directoryへ保存する。
checkpointは完全要求、絶対native path、全八source hash、元chart/追跡/回復/決定を持つ。
`replay_planar_curved_tune` / `read_planar_curved_tune` は全prefixから元Project、実正帯、
全場/RF、試行形状と有理chart、追跡/anchor/選択周波数/決定を再構築し、保存結果全体と照合する。
再hashされた別の有効nativeでも、要求から再生成した試行Projectと異なれば拒否する。

PAUSEDからの再開は既存checkpointを検証し、別directoryへ新試行を追記する。
失敗は `failure-NNN.json` として新実行に保存し、先行完了checkpoint/nativeを変更しない。
失敗記録を周波数評価として扱わない。実行中は各appendで全先行native hashと製品実装hashを照合する。
所有コピー/相対path移動は[専用所有API](PLANAR_CURVED_TUNING_SAVED.md)で後続受入した。
独立追跡履歴、process取消し、CLI-worker/実GUIは続く必須範囲。

## 限定検査と来歴

独立不変量を先に指定したAPI未実装のModuleNotFoundErrorを
`out/p09-planar-curved-tuning-20261007/baseline.log` に保存した。
円TMは16二次sectorから二回細分した元Domainを尺度1〜1.4で検索し、最終はもう一回固定境界細分。
targetは既存Bessel根による真円TM基底の尺度1.2遮断周波数。
実FEMを解析式へ置き換えず、最終絶対差<1e-4、目標差1e-3 target、粗細差2e-4 targetを事前指定した。
検索1/1.4/1.2→最終1.2、別directory再開・全元native再生・先行全byte保持の1件は465.316秒PASS。
元log `initial-circle-test.log` と全raw `initial-acceptance/` を保持する。
最終4,781,070,789.776281 Hz、真円targetとの差132,129.975863 Hz、
採用検索meshとの差208,643.630763 Hz。絶対相対差約2.764e-5で指定<1e-4を満たす。

strict/全予算のFEM前拒否、真のTE doubletのnull停止、試行失敗時の先行全byte保持の
3件は12.675秒PASS。元log `safety-test.log`、raw `safety-acceptance/`。
非円形TEの実検索/最終は両gateを満たしたが、追加反射検査の絶対coefficients差1e-9が失敗した。
固定U′の約7e4 A/m振幅に絶対値を指定した検査の誤りで、相対L2差は最大約4.085e-13。
周波数/mesh/追跡/求積の許容値は維持し、無次元parity差<1e-10へ検査を修正した。
元 `te-test.log`（2件323.370秒、1FAIL/有効nativeの異試行・保存周波数改変拒否1PASS）と
`te-acceptance/` の全rawを保全した。修正後は同じcheckpointを完全物理再生して検査し、
新FEMを重複実行しない。再開の先行prefix再構築一回/失敗保全も合わせた2件313.356秒PASS、
`corrected-replay-test.log` / `corrected-replay-acceptance/`。

TEは主軸π/7の合成楕円（.018,.020 m）を一方の主軸だけ.0208 mまで変形する。
最終1024セルの同じ元FEM作用素を独立dense generalized eigensolverで解き、
TE定数kernelを確認して最低正帯4,230,213,276.305762 Hzをtargetとした。
実疎FEMは4,230,213,276.306658 Hz、粗細差30,077.812368 Hz。
これは独立アルゴリズムによる有限作用素の対照であり、楕円連続問題の解析周波数ではない。
継承の保守的gap .08で残る二ID部分空間を、元試行0の既定controlsによる完全E/H比較で解決する。
検索と最終の両方で実rankがeven-x/odd-xからodd-x/even-xへ交換した。
反射された元coefficientsの相対L2差を無次元不変量とする。

実上位guard重なりの回復迂回禁止/null停止は追加1件3.370秒PASS（`guard-test.log`）。
checkpointの欠落key/非objectに対するKeyError/TypeErrorを別に再現し、
元 `checkpoint-parser-before.log` を保持した。完全keys検査をrequest参照より先に行い、
不正checkpoint/要求・全予算の2件0.886秒PASS（`checkpoint-parser-after.log`）。
完全prefix物理再構築の結果を再開状態へそのまま渡し、重複再構築だけを除いた。
一回の完全再生・全元hash再検査は保持する。入力keys順の最終修正はvalid replayの数値処理を変えない。

新8種類＋関連11種類を分割受入。成功全suiteや19件一括実行と表現しない。
circle/TE実行中は製品sourceを固定し、終端を確認してから再開処理を修正した。
最初の製品sourceも `initial-tuning-source.py` としてignored rawに保持する。
最終 `tuning-acceptance.json` は元410製品/全123カード台帳不変、全文書anchor、
両実例の全native八hashと選択IDに対応する元native周波数、終端log/sourceを照合する。
既に完全物理再生した成功証拠を使い、新FEM/物理再構築0。
同じ元最終データのterminal controllerへmesh許容値1 Hzを与えると両実例がmeshだけ未達、
円のtarget許容値1 Hzではtargetだけ未達となることも別に確認する。
これはgate分離の反例であり、異なる要求で新しい調整全体を実行したという意味ではない。

実行は全て既存lock環境の次のprefixを使う。

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python -m unittest -v <selected cases>
```

新8種類は `tests/test_planar_curved_tuning.py` の各caseを上記logごとに選択した。
`SUPERFISH_CURVED_TUNING_TEST_ROOT` で各logに対応する未使用raw保存rootを指定する。
TE修正検査だけは `SUPERFISH_CURVED_TUNING_REUSE_REPORT` に元 `checkpoint-003.json` を指定し、
同じ完全nativeの公開read/replayを検査した。通常のunitは実FEMを実行する。

新製品は専用調整1モジュール。元410製品/科学kernelを変更しない。
共有二分決定の既存調整/回復と直接利用する試行生成は
`test_planar_tuning test_planar_tuning_recovery test_planar_curved_tuning_trials` の11件109.769秒PASS。
元logは `related-test.log`。全suiteを先に実行せず、変化した専用APIと直接利用元を選択した。
既存自作の元P2形状/細分/有理chart、Cartesian E/H比較/有限guard/ID回復、
native物理再生と二分決定を使用する。新外部資料・依存・legacy参照なし。
合成円/楕円は測定構造ではない。full/seed/GUI検証は今回実行していない。
