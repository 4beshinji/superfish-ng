# 平面曲線の明示個別ID回復核

2026-10-07、P09の専用API leaf。P09はIN_PROGRESS。
先行は[元E/H追跡核](PLANAR_CURVED_TRACKING.md)。過去anchor・直前・現在の三つの元native解と、
継承/anchorそれぞれの完全な追跡要求を使う。所有履歴への実anchor束縛、保存/再開/調整/GUIは後続。

`planar_curved_identity_recovery.py` の `PlanarCurvedIdentityRecoveryRequest` はstrict専用版1。
zero-based `anchor_snapshot_index` と完全な `PlanarCurvedTrackingRequest` を保存し、
anchorは個別IDが解決済みの宣言に限定する。current位置は正整数でanchorより後、
継承/anchor比較のcurrent tracked prefix数は同じでなければならない。

`recover_planar_curved_modes` は元E/H・全二次写像・各有限guardから継承比較を再計算する。
継承subspaceがUNVERIFIEDならanchor比較は行わず、comparison/assessment/回復周波数をnullで止める。
継承個別IDが全て解決済みの場合は不要な回復要求を拒否する。
継承集合だけがPASSで個別ID未確定なら、過去anchor→現在を同じ元E/Hで再計算し、
全個別対応と全継承ID集合の一致を検査する。成功時だけIDをkeyとする元fを返す。
失敗時は `recovered_frequencies_hz=null`、候補比較/元集合/未確認理由を別に保持する。
真縮退やguard不足をanchor要求で迂回しない。予算不足はUNVERIFIED専用例外で停止し、部分回復を返さない。

このkernelはanchor位置/IDの宣言を持つが、所有された過去snapshotとの一致を単独では証明しない。
後続の履歴/調整ownerが、確認済みの実snapshot・元native全hash・そこで確定したIDへ束縛する必要がある。
現時点で所有保存/再開を受入済みとは扱わない。回復は宣言写像による過去元場との再識別であり、
縮退を通る連続path identityの証明ではない。scalar/f順位を固有modeのlabelとして使わない。

## 独立対照と限定検査

最初に実TE楕円→対称円→楕円のrank交換/回復を作成し、API不在のModuleNotFoundErrorを
`recovery-baseline.log` に保存した。元数値回帰の失敗ではない。
楕円axes .020/.019→.0195/.0195→.019/.020→.0188/.0202 mで、
独立な主軸反射のscalar偶奇が[-1,+1]→[+1,-1]になることを確認する。
継承では二ID集合/個別nullを保持し、anchor回復後は新rank [even-x,odd-x] を得て、
次snapshotでもそのIDを継承する。全四解の元係数/周波数全byteと全RFが前後完全一致する。
真円のdoubletで個別回復不可、誤anchor IDの集合越境、継承guardの時は比較1回だけ、
anchor guard、両比較の求積予算不足、版bool/余分key/位置/帯不一致/解決済み要求を分けて拒否する。
合成円/楕円を測定構造とは扱わない。

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-ng-uv-cache \
uv run --no-sync python -m unittest -v \
test_planar_curved_identity_recovery test_planar_identity_recovery \
test_mode_identity_recovery.IdentityRecoveryInvariantTests
```

新4＋旧平面回復4＋数学的集合不変量2、10件26.658秒PASS（終了0）。
rawは `out/p09-planar-curved-comparison-20261007/recovery-selected-tests.log`。
`recovery-acceptance.json` は実装/test/FAIL/成功log hashと基準b2b7f81の元407製品不変を照合した。
新製品はこの専用回復1モジュール。既存自作の中立集合評価だけを数学として再利用し、
元xy E/H追跡で二つの比較を再構築する。新外部資料/依存/legacy参照なし。
unit内の元実FEMと旧矩形回復を実行し、full/seed/GUI/新大型validatorは実行していない。
次は元の全二次節点から生成する形状法則と実調整。P09の両周波数gate・最終固定境界/全場・
所有履歴/anchor束縛・再開・CLI/worker/GUIは継続する。
