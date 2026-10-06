# P08：曲線native・Project・GUIの全条件受入

2026-10-07。P08 DONE。P07の専用数学を保ち、版3の元保存解を共通操作経路と実GUIへ接続した。
原要件を含む全123カードgoalは未完了。次はP09の曲線比較/追跡/調整・所有再開。

## 原条件との対応

| 条件 | 受入証拠と限界 |
| --- | --- |
| 版付きCase/Projectと全元二次配列 | [共通操作経路](PLANAR_CURVED_OPERATIONS.md)。厳密版3 dispatch、Project往復、全Domain/numerics/RF保持、版/geometry/unsupported physicsをsolve前拒否 |
| 元native保存・物理再構築 | [専用native](PLANAR_CURVED_NATIVE.md)。全node/cell/壁/owner/freeと係数/周波数のdtype/shape/bytes、符号付きzero、K/M/最低正帯・正規化/直交性・PEC/TE核を再構築 |
| 改変拒否 | 専用native新7件＋共通経路の再検査。geometry/mesh/RF/理由/版、倍振幅・PEC破壊・周波数・正しい固有対の偽最低帯・dtype・途中変更・NPZ破損/重複と完成/通常file条件 |
| 独立API/CLI/GUIの全配列・全RF一致 | [共通操作経路](PLANAR_CURVED_OPERATIONS.md)新9件の分割受入。実Chromeは両偏波の全五nativeファイルが独立専用APIの参照とbyte一致。全RF/metadataと元点の全12 signed SI場も一致 |
| 所有worker、実中止・再起動 | 新unitは1024cell曲線workerのrunning/生存を観測して中止・実終端、新job再起動/元byte import/管理器再作成を確認。Chromeは中止・新job、さらに旧server終了0→別server起動→元native/Study/中止状態と新workerの再生を確認 |
| 独立Studyと元場表示 | 全二次nodeの正尺度変換、接続保持、両偏波のf/E/H/U′/P′/Q/Gとenergy/σ則。元reference中心場・実二次壁表示。表示標本をRF積分/連続誤差に用いない |
| 旧矩形/多角形の保存再生 | 旧版1/2直接利用、関連48件、実Chrome旧操作13項目。Project往復・単位保持・元native取込/新solve・plot/probe・中止・永続再生、軸RF追跡選択への混入防止 |
| 理由付き加速量N/Aとモード順位 | 全RF再構築とGUI probe metadataに二つのR/Q・Vacc・Eaccのnull/理由を保持。独立sweepの任意位相を質量overlapで整合し、順位を永続IDへ読み替えない。未実装の曲線比較/調整入口は明示拒否 |

## 実ブラウザーの受入

`verify_gui_planar_curved.mjs`は新15項目PASS、旧`verify_gui_planar.mjs`は13項目PASS、
`verify_gui_planar_curved_replay.mjs`は新server上の7項目PASS。計35項目、全終了0。
各実行で全403製品hash不変、外部HTTP要求0。両偏波のPNGを目視し、元曲線壁・signed場・
J/m/W/m・N/A・モード順位/精度未確認の説明と画面収まりを確認した。
作業は自作の回転/平行移動楕円16cell、実中止だけは元写像を制限細分した1024cell。
測定構造・連続場の精度証明として扱わない。P07の独立離散化受入を継承する。

最初のChrome反例は、曲線Caseで多角形説明を表示し、一次要素の選択を残していた。
`web/planar.html` / `planar.js`だけで曲線説明と二次要素の固定を追加した。
旧検証器の初回は11項目成功後、`nav a`を軸RFリンクと仮定して新しい先頭の磁気リンクへ遷移し失敗。
製品を変更せず、検証器を`nav a[href="/"]`へ修正し、13項目を再検査した。
両FAIL report/logを保持する。既定sandboxのlocalhost bind拒否logも保存し、
承認済みローカル実行権限でサーバーを起動した。自動承認reviewの拒否ではない。

```sh
node scripts/verify_gui_planar_curved.mjs --url LAUNCH_URL --out NEW_DIRECTORY \
  --fixtures ORIGINAL_API_REFERENCES --workspace GUI_WORKSPACE
node scripts/verify_gui_planar.mjs --url LAUNCH_URL --out ANOTHER_NEW_DIRECTORY \
  --workspace GUI_WORKSPACE
# 旧serverを実終端し、同じworkspaceで新serverを起動してから実行する。
node scripts/verify_gui_planar_curved_replay.mjs --url NEW_SERVER_URL --out REPLAY_NEW_DIRECTORY \
  --fixtures ORIGINAL_API_REFERENCES --report FIRST_CURVED_BROWSER_REPORT
```

全Chromeは既存[共通資源管理器](BROWSER_RESOURCES.md)から起動し、終了時に回収した。
両GUI serverは終了0。全所有jobはterminal、Chrome slot 0、引継ぎ中の数値/GUI handleなし。
元参照・全download・Project/Study/native・PNG・初回FAIL・成功report/logは
ignored `out/p08-planar-curved-native-20261007/`に保持する。検証tokenは停止済みserverの一時session。

## 最終照合と範囲

`audit_planar_curved_operations.py`は新9件の7成功＋修正2件、関連48件、実Chrome35項目を
各log/report/hashへ結び付ける。専用FEM/RF源とテストは操作検査時と完全一致し、
その後の製品差分は二つのGUIフォームだけ。全元native/GUI downloadのhash一致、
元browser reportと新server replayのbinding、全job終端・Chrome回収も確認する。
新solve/物理再構築はこの監査では0。

```sh
UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python \
  scripts/audit_planar_curved_operations.py out/p08-planar-curved-native-20261007 \
  --out NEW_ACCEPTANCE_JSON
```

`final-p08-acceptance-v2.json` / `final-p08-audit-v2.log`は終了0 PASS。
初回監査はPASSだったが、書込中の監査stdout自身まで元artifactへ数えていた。
初回証明を保持し、監査出力を明示除外しvalidator hashを追加したV2で監査だけ再実行した。
数値/GUIの成功を件数やhash更新のために再実行していない。
この監査は受入時のsource用であり、P09等の後続変更後は元commit/元hash証拠として読む。
元成功を現在のsource不変へ読み替えて再実行しない。
原123カードを保持し、P08だけをDONEにする。P09と原互換親P02/O02/D02等は未完了。

P08はCartesian保存/操作経路として影響を限定した。専用曲線・共有P2・seedのFEM/RF数学、
物理許容値・依存は変更していない。限定unittestと実操作の証拠であり、full validate/seed再検証・
release/milestone・hosted CIの証拠ではない。新外部資料・依存・legacy参照はない。
