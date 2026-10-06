# 平面曲線の元E/H追跡核

2026-10-07、P09の専用二状態API leaf。P09はIN_PROGRESS。
先行の[完全比較分割](PLANAR_CURVED_COMPARISON.md)、[元E/H内積](PLANAR_CURVED_FIELD_COMPARISON.md)、
[固定境界有限guard](PLANAR_CURVED_SPECTRAL_RESOLUTION.md)を使う。
共通追跡版1〜10/CLI/所有履歴/回復/調整/GUIにはまだ接続していない。
専用APIの受入だけでP09の円/非円形調整・両周波数gate・所有再開条件を閉じない。

`planar_curved_tracking.py` の `PlanarCurvedTrackingRequest` はstrict専用版1。
完全な二次比較Domain、両nativeの有理参照chart（nullは同一セルのunit chart）、
正のtracked prefix数、元個別IDまたは完全なID集合partition、controlsを保存する。
入力chart/groupはコピーし、保存は新規ファイルだけを作る。全余分key/版bool/不正数値/偏波混在を拒否する。
`track_planar_curved_modes` は各側に一つ以上の実上位guard modeを要求する。
最低正帯/元全配列/K/Mを再検証し、元f/phasor振幅/符号/全RFを変更しない。

EとHの元自己/交差Gramから別々にnormalized featureを作り、既存の数学的な
subspace割当とprincipal overlapを適用する。有限区間の重なり/周波数近接から群を作り、
継承ID集合と統合する。E/Hの旧・新rank集合/ID集合が同じであることを検査し、
一次元では両phasorに同じ符号を要求する。E/H片側だけの成功は受入しない。
真の縮退や継承した複数ID群は、subspace PASSでも個別IDはnullのまま保持する。
元のrankをidentityの代わりにしない。

有限群がtracked prefixから上位guardへ越境、inverse未解決、割当曖昧、E/Hの割当/符号不一致なら
結果をUNVERIFIEDにし、全current_mode_idsをnull、全matchをUNVERIFIEDにする。
予算不足はstatus=UNVERIFIEDを持つ専用例外で停止し、部分結果を受入しない。
これは明示写像における二つの有限snapshotの対応で、連続path identity・連続誤差・surface peak保証ではない。
固定Cartesian成分のL2 transportなので、幾何回転だけを宣言してvector frame回転を黙って追加しない。

controlsの数値閾値はoverlap .9、assignment margin .1、relative gap .001、
relative singular value 1e-8、cluster link .7。数値margin floorは
max(1e-10,32ε×共通三角形数×high次数²)を報告し、要求marginの下限にする。
面積次数は標準16、4〜28、場はlow/high+4、各side guardは指定次数で組み立てる。
資源予算は名称で単位範囲を明示する：pairは各完全比較2,000,000、
共通三角形250,000、各side細分250,000セル/250,000 native DOF、元Gram modes256。
場の二次数/両側を通した点予算2,000,000と、各side細分組立の点予算2,000,000を別に保存する。
一つの総追跡予算とは主張しない。各比較内部のpairと場内の点数は累積し、元セル/次数でリセットしない。

## 独立対照と分割受入

最初に実TE/TMの二尺度/元負phasorの検査を作成し、API不在のModuleNotFoundErrorを
`tracking-baseline.log` に保持した。元数値回帰の失敗ではない。
新6＋旧14、20件11.565秒PASS（終了0）。条件は、二尺度解析f×1/2・場符号一致/ID継承、
円近似の対称なTE真doubletと任意basis回転、上位guard越境/全個別ID破棄、strict往復/入力chart所有、
全資源不足・元改変/不足guard拒否、独立nativeセル番号の元owner保持。
旧14は既存直線追跡5と数学的mode_tracking9を対象にした。

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-ng-uv-cache \
uv run --no-sync python -m unittest -v \
test_planar_curved_tracking test_planar_tracking test_mode_tracking
```

追加1件 `test_actual_elliptical_rank_exchange_tracks_reflection_parity_and_all_rf` は2.673秒PASS。
TE楕円のaxes .020/.019→.019/.020 mで実rankが交換する。独立な主軸反射の
scalar parity [-1,+1]→[+1,-1]を確認し、IDは旧1→新2/旧2→新1を保持。
元全RFを前後完全一致させ、継承二ID集合からは分離周波数だけで個別IDを発明しない。

追加1件 `test_exact_frequency_covariance_cannot_override_e_h_transport_disagreement` は1.415秒PASS。
実90度回転で全fは一致、Hz overlapも1だが、固定Cartesian Eの同rank内積は0。
E/Hの不一致で全IDを未確定にする。周波数や一つの場familyだけでidentityを確定しない。
新8＋関連14、22件を20＋追加1＋追加1で受入。合成円/楕円は測定構造ではない。

rawは `out/p09-planar-curved-comparison-20261007/`。
`tracking-acceptance.json` に実装/test/元FAIL/成功log hashと基準505d7abの元406製品不変を記録した。
新製品は専用追跡1モジュール。既存数学的割当/ID集合merge/feature圧縮だけを再利用し、
xy元E/H・全二次比較・Cartesian有限guardを専用に接続した。新外部資料/依存/legacy参照なし。
unit内の実FEMと旧cylinder保存再生対照を実行したが、seed validator/full/GUI/新大型validatorは未実行。
次は完全な過去anchorによる個別ID回復と、固定元二次領域から生成する形状法則/実調整。
P09の円/非円形両gate・最終二次外周/全場保存・所有履歴/再開・CLI/worker/GUIは全て継続する。
