# 曲線GUIの完全大容量checkpoint

2026-10-07、P09の[専用GUI](PLANAR_CURVED_GUI.md)の大容量科学入力/元場表示を検証する。
有界条件は、先行受入の円TM四trial/非円形TE三trialの完全再生、両周波数gate、
TE過去anchor回復、GUIの完全保存、実対象順位の元場取り込み/表示と全元byte保存。
大容量GUIの実終端/監査は受入済み。P09はIN_PROGRESSで、全条件監査と節目の全validateを継続する。

## 元証拠と入力

rawは `out/p09-planar-curved-large-gui-20261007/`、基準 `e395996`、製品420源は固定。
先行の[所有調整受入](PLANAR_CURVED_TUNING_SAVED.md)にある
`accepted-case-import/accepted-native/circle-moved/checkpoint-004.json` と
`ellipse-moved/checkpoint-003.json` を使用する。
元保存は円40,980,088 byte、TE91,932,064 byteで、全二次chart/全E/H/guard/判断を含む。
各trialの元九ファイルはそのまま使い、新native固有解は生成しない。

科学内容の変更なしに、所有形式の順序付き相対trial名を元ownerのcanonical絶対名へ展開する。
この非ゼロdict入力は公開所有replayが受け取る形である。
元要求/法則/全native hash/全判断/chartは完全一致し、保存ownerのrequestへ束縛する。
ゼロprefixの実owner選択は先行GUIで別に受入済み。
GUI exportは非束縛selection wrapperに元完全checkpointを保存する。
相対名だけのCLIファイルをbrowserが推測したownerで開く検査とは数えない。

円は検索256→最終1024セル、Bessel目標4780938659.800418 Hzと
実最終4781070789.776281 Hz、粗細差208643.6307630539 Hzを保持する。
TEは元非一様形状則/元FEMで最終4230213276.3066583 Hz、
同有限作用素の独立dense参照4230213276.305762 Hzと先行照合済み。
粗細差30077.812368392944 Hzは別gateである。
個別ID odd-xは初回順位2、後続/最終順位1へ移り、後続/最終とも実過去anchor0で回復する。
有限作用素dense一致/二gateを連続問題の誤差上界や表面peak精度の保証と扱わない。

## 検証器と途中記録

新 `verify_gui_planar_curved_large_checkpoint.mjs` は共通browser-sessionの資源管理を使う。
1browserあたり30分/一時profile・cache512 MiB、同時最大2枠を維持する。
実file input/button/download/元RFページ/画像を操作し、実POST body byte/HTTP statusを測る。
科学checkpointを小さく加工して容量検査へ置き換えない。

準備の元入力field名誤り `target_frequency_hz` /正解`target_hz` はFEM前のKeyError。
初回部分出力/sourceを別 `...-initial-preparation-error/` へ保全し、元scientific sourceは不変。
正しいfieldで未使用rootへ準備した。

円初回は完全再生、両gate/元ID、全保存、元五byte importと実順位RFの5項目が成功した。
native downloadの30秒待ちで `manifest.json` が未取得となり終了1。
成功済みcase.json/fields.npzと全FAIL reportを保持し、同じ実import jobから残り取得/画像の
2項目を補完してPASSした。円7項目の分割受入であり一括PASSではない。
取得待ちを300秒へ延長する変更は検証器だけで、物理許容値/期待値は変えない。

TE初回とCDP記録buffer制限後は `Runtime.evaluate` 180秒待ちで終了1/check 0。
debugger切断を観測する処理を加え、次の試行はsocket code1006で終了1/check 0。
これらを科学再生の失敗/成功と数えない。元4版の検証器/全log/reportを保持する。
CDPのPOST記録上限を小さい正値へ指定し、Fetchによる巨大body転送を避けて
`Network.setBlockedURLs` の順序付きURLPatternでlocalhostを許可、他HTTP/Sを遮断する。
URL追跡/外部要求guardは保持する。診断用bufferと本来の科学HTTP bodyを区別する。
切断の根本原因は未確定であり、上記を原因の証明とは主張しない。

使用したAPI仕様はChromiumの[Network protocol定義](https://raw.githubusercontent.com/ChromeDevTools/devtools-protocol/master/pdl/domains/Network.pdl)。
Network.enableのpayload/POST記録上限と、setBlockedURLsの先行一致/許可規則を参照した。
APIの意味だけを再利用し、外部実装コードをコピーしない。新依存なし。

入口（別未使用out、準備済みfixture/workspace、localhost起動logを指定）：

```sh
node scripts/verify_gui_planar_curved_large_checkpoint.mjs --server-log LOG --out NEW_OUT --request FIXTURE_JSON --workspace GUI_WORKSPACE --case circle
node scripts/verify_gui_planar_curved_large_checkpoint.mjs --server-log LOG --out NEW_OUT --request FIXTURE_JSON --workspace GUI_WORKSPACE --case ellipse
```

## 終端と照合

TEの次の実行は終了0、8項目PASS。全三trial/両gate、過去anchor0と実対象順位、
完全checkpoint保存、元五byte import/全download、SIのRF/両R/Q N/A、元場画像を確認した。
円5＋不足2とTE8、計15項目の分割受入で、最初のFAILをPASSへ書き換えない。
TEの実HTTP bodyは再生95,690,800 byte、元場取込102,474,277 byte、いずれもHTTP200で、
64 MiBを超え専用128 MiB以内だった。円は42,823,807/46,149,956 byte、いずれもHTTP200。
全内容を保存したGUI出力は円44,306,754/TE98,715,925 byte。

`large-gui-acceptance.json` と `final-audit-creator-corrected.log` は、元420製品源/全123カード不変、
全7trial×九ファイル=63元entry、元選択五ファイル/実download五ファイルのbyte一致、
科学checkpointの完全一致、両gate、上記実POSTと有界診断を照合した（終了0）。
最初の `final-audit.log` は生成時の15曲線源を全て現行と同一としたAssertionErrorで保全した。
実際には14源が同一で、`planar_curved_tuning.py` の生成時hashは先行rawの
`initial-tuning-source.py` に全7trialで一致する。差分は完全再生の状態を再利用する処理と
公開replay入口の整理のみで、`_trial`/`_assess`/`_reconstruct` は同一。
現行源は先行受入commit401208aと一致し、今回はそれで全prefixを再生した。
生成当時のmanifest/claimを現行版へ書き換えない。

円/TEの調整画面と元場画像の計4画像を視認し、順位/両gateの表示、診断のscroll枠、
元TM/TE場の描画を確認した。GUI leafで新native固有解0、最終byte監査で物理再構築0。
TE browser46225、server90242はいずれも実終了0、worker-terminalは空で、Chrome slot 0/外部要求0。
準備誤り/3 debugger失敗/円download不足/監査誤りをそれぞれ保持する。

製品/科学kernel/物理gate/benchmark変更なし。
P09全条件の節目として、別root `out/validation-p09-milestone-20261007` の全validateを一度起動した。
handle60083で実行中、full/seed成功は未証明。GUI leafの新native求解0と区別する。
Hosted CI、Wine/科学GPUは今回未実施。
P09全条件、原互換条件/全123カードgoalは継続する。
