# 曲線選択移送版2：独立幾何・native場・操作の受入

2026-10-13 JST、ADD-N04-selection-charts-06 **DONE**。開始は05完了commit `b8be3ce`。
異なる初期接続への選択移送の01〜06を受入。親N04は境界分割変更生成とRF版5対照を残し継続する。
新規公開は専用検証器であり、製品のFEM/場/RF/追跡/保存核・許容差は無変更。

## 固定条件と結果

[原仕様の全ゲート](CURVED_SELECTION_CHARTS_SPEC.md#必須五工程と独立受入ゲート)を維持した。
矩形の旧2/新3初期要素へ両側uniform二段を加え、旧選択0を移送した新4要素
`[0,2,3,14]`をmarked末尾へ追加する。尺度1/2で旧・新・marked新の計6求解を実行した。
各尺度の要素数は32/48/69、U=1 J・SI・peak phasorと両R/Qを保持する。
初期26/27要素の非アフィン形状ではuniform一段と旧marked0/新marked1を保持した。
全域/旧選択の有理被覆と二policyは完全一致し、参照面積を物理誤差へ読み替えない。

| 別ゲート | 条件・実測 |
|---|---|
| 独立幾何 | 旧三角形の閉式面積/回転体積/Hφ=r質量、別8×8 P2/Duffy積分、元選択と交差の三量、新cover/containedの三量不等式、全域Green積分を確認。元選択の最大相対差3.492e-16（gate3e-12）、全有理被覆EXACT |
| 尺度の幾何 | 非アフィン26/27・別履歴の各三量で4/8/32倍と同じ全選択を確認（gate3e-12）。Greenの符号と正の物理面積/体積を別記 |
| 親子行列 | marked直前/直後を次数12で別組立しPᵀKfP/Kc・PᵀMfP/Mcを確認。最大相対2.617e-17（gate1e-10）、子P2全座標/接続はnativeと完全一致 |
| 周波数 | fixed-domain Ritz変化は両尺度で約−1.953e-8、非増加gate5e-11を満たす。尺度2で1/2倍（gate1e-10） |
| 元場 | 全要素の独立8×8物理回転体積重みでHφ/Er/Ezを別々に比較。Hの全内積から単一符号だけを選び振幅fitなし。2^(−3/2)尺度則の最大相対L2差1.191e-11（gate1e-10）。供給点は旧2048/新3072/marked新4416、欠測0 |
| RF | 両R/Q/G/TTFの尺度不変を別量で確認。fを含む尺度の最大相対差5.329e-15（gate1e-10）。保存readerからの全RF再評価はgate1e-12以内 |
| API/CLI保存 | 六nativeの係数/fと全P2幾何配列がAPI readerへ完全一致。六つのradial probeとmetadataはAPI/CLIでbyte/値一致。transfer全文書はAPI/CLI/保存完全再生と一致、8 CLI起動は終了0 |
| 実GUIと所有保存 | 新55操作PASS（05の43＋六nativeの全RF/元Project12）、外部要求0・製品源不変。六所有コピーの全9ファイルと全10 NPZ配列は元nativeへ完全byte/配列一致。元Case/RF/全metadata一致、六場画像を生成し最終画像を目視確認 |

6求解は初回に保存した1回＋後続の5回。初回の成功nativeを再利用したので合計6新求解である。
後続の科学検査/CLI段階は26.983秒・5新求解/1再利用で、全科学ゲートの後に検査器が停止した。
CLI修正・所有包装・GUI・終端監査は追加FEM0。別の05旧GUI回帰1求解を専用6へ含めない。
予算は実行前plan.jsonへ3600秒/32 GiB address space、BLAS1、移送100000組/1000三角形、
非アフィン100000組/10000三角形と元Case要素上限を固定した。

これは離散場・幾何・操作の受入であり、粗い矩形の連続物理精度/表面ピーク精度はUNVERIFIED、
physical_error_bound=nullを維持する。03のstrict/対称/逆方向・非nested/frozenと
04の改竄/予算/保存型拒否、05の元非アフィンnative全配列/RF一致を、変更のない製品源に対して再利用した。
新unit/seed/full/legacy実行0。検証器追加だけのために全FEMや成功済みunitを再実行していない。

## 失敗保全、差分と再現

初稿のNumPy scalar座標をstrict LineSegmentが拒否した0求解のERROR、
Greenのsigned境界積分を正の領域積分へ直接比較した0求解のFAILを保全した。
元境界の(z,r)と内部写像の(r,z)の向きを確認し、符号を報告に残して正の物理量を比較する。
次の1求解後のFAILは保存していない固有値配列を完全一致要求した検査側の問題だった。
元係数/f/P2配列の完全一致は維持し、周波数から再構築する固有値へbyte一致を要求しない。

5追加求解後のERRORはCLIの確認メッセージをJSONと思って解析したもの。
元の数値/独立helperのASTが全て不変であることを確認し、CLI確認だけを修正して再実行した。
元FAIL reportを上書きせず、completed-acceptance.jsonへ科学証拠の再利用/元report SHAを結合した。
新ブラウザーの初回は閉じたdetails内のimportボタンをクリックしようとして停止し、
detailsを開く手順を補完した。製品の意味や受入ゲートの緩和はない。

六保存場には検証済みnativeと実際の元Projectを結合した`managed/` archiveを作った。
原nativeの全byteと元Case/source meshを照合し、origin=imported・新求解なしと明示する。
元Projectを持たないraw save_runの非managed取込みが既定の編集Projectを作る既存挙動を、
元外部メッシュを保持した元Projectの再生証拠として使わない。

科学実行時の全源は不変。以後の差分は二検証器のCLI/所有包装/GUI確認だけで、製品源は不変。
同時進行の別レビューscript変更は監査で区別し、今回の数値利用源/変更対象に含めない。
最終snapshot1444対象/1230 Python源。既存6 unitの源と05の製品受入はそのまま再利用した。
全handle/六imported job/plot subprocess/server/browserは終端、ブラウザーslotは空。
新依存・外部文献・旧資産参照なし。既存自作P2基底/Green式/親子制限を利用した。

rawは`out/n04-selection-charts-acceptance-20261013-native/`の元FAIL/completed/final-acceptance、
六native/元Project/二policy/八CLI出力、変更前検証器、分割source snapshot/監査と、
`out/n04-selection-charts-browser-native-20261013/`の55操作/六所有コピー/図/guard終端。
前段の`...-20261013`/`...-finite`/`...-green`も失敗/費用を保持する。

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-uv-cache \
  uv run --no-sync python scripts/validate_curved_selection_charts.py --out <未使用出力先>
# 途中保存がある場合は元完了nativeを検証して再利用し、不足段階だけ求解する。
# ... --reuse-native <前回の出力先>
node scripts/verify_gui_curved_selection_charts.mjs \
  --url-file <起動URLファイル> --sources <05の独立fixtureディレクトリ> \
  --native-sources <六nativeとmanaged archiveの出力先> --out <未使用出力先>
```

全131は82 DONE/2 IN_PROGRESS/47 PLANNED、原123は76/2/45。
次はADD-N04-boundary-remesh-01。選択移送の完了を親N04/原32要件/全goalの完走とは扱わない。
