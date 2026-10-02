# 新版平面比較・追跡履歴GUI（P04-c-b受入）

2026-10-02、製品基準 `21ba035`。変更は `web/planar.html/js` の新版写像9/10保持とstrict要求輸送、平面履歴に限定したCSS。
FEM、場内積、追跡許容差、保存版/worker契約は変更しない。実操作/全元場照合/最終表示と[親P04監査](PLANAR_PIECEWISE_ACCEPTANCE.md)を受入。

## 再現と変更

原P04は元TE/TM場の写像、形状法則、追跡履歴、再開、調整GUIへの接続を要求する。
調整GUIの受入だけでは、単独比較/履歴フォームの新版宣言が保持されなかった。
実関数を隔離実行した `form-baseline.log`（session51699、終了1）では、読み込んだ版9が
矩形の版1へ変わり、元の対応分割を失った。保存要求完全一致という不変量が先に失敗した。

- 明示区分写像9と元Project/頂点多項式法則10の選択肢を追加し、宣言全体をJSON欄へ保持する。
- 新版では旧尺度/回転入力を隠し、対応分割または元Project/両試行値/細分段数を指定する。
- 保存/投入/回復宣言には `trackingRequestText` から写像/ID/群/controlsの元JSON文字列を渡す。
  重複キーをブラウザーのJSON.parse→再serializationで隠さず、strictサーバーで拒否する。
- pairと所有履歴から次段のID集合を引き継ぐ既存操作は、新版の元宣言を保持する。
  両試行値/細分を次の比較に合わせて明示する。順位とIDを混同しない。

元TE/TM場・peak phasor・SI・U′[J/m]・加速量N/Aを保持する。対応PASSを連続枝や一般誤差保証とはしない。

## 選択した検証

証拠根は `out/p04cb-planar-tracking-gui-20261002/`。

```sh
node scripts/verify_planar_tracking_form.mjs out/p04cb-planar-tracking-gui-20261002/all-form-requests.json
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-ng-uv-cache \
  uv run --no-sync python -m unittest -v test_gui_planar_piecewise_tracking \
  test_gui_planar_recovery \
  test_planar_tracking_history_saved.PlanarHistorySavedTests.test_gui_history_extension_and_native_import
```

隔離フォームは全版1〜10の完全往復と、版8〜10写像/全controlsの重複キー保持をPASS。
これは実ブラウザー操作の代用ではない。`all-form-selected.log` に記録する。
Pythonは新strict2、旧GUI回復2、fixture classの直接履歴5、所有GUI1の計10件、
session7780、160.560秒PASS/終了0（`selected.log`）。未知の個別IDの生成、真の縮退、
祖先改変、各pair合格だけでは不十分な履歴、保存元場の取込も既存検査で確認した。

[調整GUIの独立API実FEM4試行](PLANAR_PIECEWISE_TUNING_GUI.md)を元場として再利用し、
別API実行で版9、版10、同値最終細分10の3pairをPASSした（session95901、終了0）。
ここでは新FEMを解かず、保存nativeの復元と元場比較を実行する。物理精度の独立証拠は
P04-a/bと調整GUIの解析TE10・全配列対照を再利用する。

初回prepare/session6542はfixtureの群順位0をstrict拒否/終了1。順位1へ修正し、許容差は維持する。

## 実操作と全照合の受入

実Chrome検証器は `verify_gui_planar_piecewise_tracking.mjs`。分割証拠を以下に記録する。
全実行で395製品hashを固定し、外部要求0。新FEMを代用する計算は追加していない。

| 条件 | 実操作証拠 |
| --- | --- |
| 新要求9保存/再読込、元SI宣言保持 | `browser-2/report.json`：完全な分割とIDが往復一致 |
| strict JSON | 同report：重複mapping_versionをサーバーで拒否、job割当なし |
| 実pairと所有履歴 | 同report：元場9、元Project法則10のpairがPASS、順序9→10の所有履歴と個別IDを保持 |
| 次段のID集合 | 同reportと`browser-4/report.json`：pair/履歴の元宣言と群を保持、次の値/細分を明示 |
| 明示回復条件 | browser4：解決済みanchor点2/個別IDと完全な比較10を宣言して保持。解決済み履歴なので不要な回復eventは作らない |
| 最終細分と三段履歴 | browser4：比較10の細分0→1がPASS、三段9→10→10と最終IDを所有 |
| 元場/結果輸出 | browser4：履歴結果全文一致、最終元場取込/実描画、U′=1 J/mと加速量N/A、URL復元 |
| 新サーバー復元 | `restarted-browser/report.json`：三段全物理再生、元場/元法則/ID群の復元、要約/全文の表示5項目 |
| 最終CSS範囲と宣言全文 | `scoped-browser/report.json`：平面専用classの固定表、宣言全文一致、横はみ出しなし3項目。Hφ側にclassなし |
| 独立API/全元場 | `native-audit.json`：別API3pairの全要求/全field比較/判断とGUI/履歴が完全一致、全70配列・native全byte・全RF/最終Project一致 |

browser2/session58021は9項目PASS後に検証器の回復宣言不備で終了1。
browser4/session19976は同じ保存済みpair/履歴を再利用し7項目PASS/終了0。
この9/7は一回の16項目成功ではなく、1項目重複を含む分割操作証拠。
新サーバー/session67927は5項目PASS/終了0、最終CSS限定/session73174は3項目PASS/終了0。
独立API session95901と全照合session12034も終了0。
server12853はSIGINT終端130、server86426はSIGINT正常終了0。所有browser slotは空。
終端と最終hash/native byte/所有pair保持は `final-acceptance.json`。製品src固定解除、生存handleなし。

`history-field.png`と復元元場、要約/展開宣言を目視した。
初回の履歴表は巨大JSONで横にはみ出したため、新版9/10を要約+展開全文に変更した。
要約には対応セル数または両試行値/細分を表示し、全文は保存宣言の全JSONを保持する。
平面専用classでCSSを限定する。全照合後の差分はHTML/JS/CSSだけ、数値ソース不変。
表示変更後も全版1〜10の隔離フォームがPASS。新固有値計算/全API照合の再実行は不要と判断し、
保存済み元場の新サーバー再生/表示とbyte一致だけを確認した。

## 再現コマンドと失敗

```sh
node scripts/verify_gui_planar_piecewise_tracking.mjs --url LAUNCH_URL --out NEW_DIRECTORY --fixture FIXTURE_JSON
# 部分操作成功済みのbrowser2から、保存したpair/履歴を再利用して残条件を操作する
node scripts/verify_gui_planar_piecewise_tracking.mjs --url LAUNCH_URL --out NEW_DIRECTORY \
  --fixture FIXTURE_JSON --continue-report PARTIAL_REPORT
# 新server/新profileで保存結果と元場を復元する（最終CSSだけは --layout-only true）
node scripts/verify_gui_planar_piecewise_tracking.mjs --url NEW_LAUNCH_URL --out NEW_DIRECTORY --resume-report PRIOR_REPORT
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src UV_CACHE_DIR=/tmp/superfish-ng-uv-cache \
  uv run --no-sync python scripts/validate_planar_piecewise_tracking_gui.py \
  --root out/p04cb-planar-tracking-gui-20261002 --browser out/p04cb-planar-tracking-gui-20261002/browser-4 --out NEW_AUDIT_JSON
```

全照合は表示変更前の固定ソースに対して実行する。表示修正後の数値ソース/byte不変は
`post-display-source-diff.json`、`css-scope-change.json`、`final-acceptance.json`で区別する。
初回browser/session23379は2項目PASS後、同一file選択のchange未発火で検証器timeout/終了1。
file入力値をclearする検証器修正後、browser2は9項目PASS。その後、未解決群のanchorを正しく拒否して終了1。
browser3/session79214は復元2項目PASS後、隠れた入力欄への検証器fillで不正JSON/終了1。
検証器だけを解決済みanchor IDの明示、details展開後入力へ修正しbrowser4成功。
全失敗ログ/reportを保持し、製品のstrict拒否/物理閾値を変えていない。

既存自作フォーム/strict parser/worker/所有履歴/共通browser lifecycleを再利用した。
新外部資料/依存/legacy参照なし。seed/全validateは本GUI変更では実行していない。
