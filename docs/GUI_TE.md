# TE GUIの接続と受入

2026-09-15 JST：[TE円筒チューニング](TE_TUNING.md)を同端条件の直線円筒へ接続し、限定受入。
EφによるID、半領域・鏡映の元セクター順位、加速量N/A、保存再開・回復・最終粗細ゲートを保持。
関連53unit（52＋1の分割実行）、専用44実FEM、Chrome閉PEC9/鏡映11/旧TM9項目がPASS。
8組native全配列/RF一致、元114ファイル保持。一般TE形状・他物理調整とD03は残る。
親33=10受入/16進行/6他未受入/1範囲外、D02と全計画goalは継続中。


2026-09-09追補: [同端条件のTE円筒追跡](TE_SECTOR_TRACKING_PLAN.md)を半領域・鏡映部分スペクトルへ拡張し、限定受入。同じ側の一対称面を持つ直線P1/P2円筒が対象。実Eφで対応し、異なる端条件・通常/鏡映の混在を拒否する。独立32FEM、8Study、Chrome9操作、旧追跡8文書の再生、標準801件（799合格、2skip）と既存TM/TE数値回帰を確認。一般形状の追跡・TE調整は未対応。

[TE鏡映結果の収束比較](TE_REFLECTED_CONVERGENCE_PLAN.md)を接続・限定受入。同じ元半領域の物理・対称条件だけを比較し、電場/磁場/RFの個別判定と部分スペクトル番号を保持する。独立12FEM、4Study、Chrome7操作、CLI/GUI保存一致と再起動を確認。標準795件（793合格、2skip）と既存TM/TE数値回帰が合格。

2026-09-09追補: [TE対称面鏡映](TE_REFLECTION_PLAN.md)を接続。TEのEφは磁気対称面で偶、電気対称面で奇、Hrは逆符号、Hzは同符号。元振幅を維持しU/PEC損失は2倍、f/Q0/Gは不変。専用native版4で元半領域から再構成・再検証し、API/CLI/Project/Job/GUIで部分スペクトルと明示する。鏡映結果の追跡は上記の同端条件円筒に限定対応。収束比較は上記の元半領域方式に限定対応。標準790件（788合格、2skip）と既存TM/TE数値回帰まで限定受入済み。

2026-09-09、基準449d1ef。O02の通常TEジョブを、場表示・プローブ・モデル選択へ接続する工程。
通常GUIの接続と独立照合・最終標準は以下の範囲で合格。TE追跡等と計画全体は未完了。

| 受入項目 | 現在の証拠 | 判定範囲 |
|---|---|---|
| P1/P2/曲線P2の表示・SIプローブ | tests/test_te_display.py、3件PASS | 保存場成分、軸、B=μ0H、位相、元hash、strict mode |
| 独立円筒場との比較 | 同テストのBessel場比較 | 円筒の選択プローブで成分誤差1%未満 |
| 通常GUI実操作 | browser-te-expanded-wait-20260909、Chrome10項目PASS | TE選択、P1/曲線実FEM・描画・プローブ保存、Project往復、N/A・未対応操作、TM復帰 |
| GUI/API・保存/ダウンロード一致 | te-gui-independent-20260909、PASS | 新規API FEM3件と全係数/周波数一致、全3プローブ成分、管理器再起動後verify=True |
| 球形TEの独立物理 | 同独立reportの3モード | f、場、Gを別判定、既存許容差PASS |
| 日本語図タイトル | Chromeのte-fields.png目視 | この環境の既存日本語fontで表示。fontの配布や全環境保証は含まない |
| 既存TM表示 | test_display.py、2件PASS | P1/P2表示の従来の意味を保持 |
| 標準・TM/旧TE数値回帰 | validation-gui-te-20260909、PASS | 766件中764合格/2skip、seed9モード19量f差0/RF最大8.882e-16、旧TE7件差0、448source一致 |

上記out名は無視対象のローカル検証出力を指す。TEのStudy/追跡/調整/最適化・連続表面ピークはこの受入に含めない。

## 表示契約

TEはEφを実ピーク、Hr/Hzをexp(+iωt)の+i quadratureとして扱う。
磁束密度はμ0倍で、図はMV/m・mT、CSVはV/m・A/m・Tとmを使う。
軸上Eφ/Brはゼロ、Bzは有限。R/Q・軸方向加速量はN/Aと理由を表示する。
磁力線はrEφの等高線。符号付きEφの色範囲はゼロを中心に対称とする。
P2は4つの表示三角形へ分割し、曲線では基準座標の中心を写像して元FEM場を評価する。
描画分割・補間は表面ピークや収束の認証ではない。PEC・軸・対称境界タグを表示する。

通常plot_mode/export_radial_probeがCaseの明示TEから専用reader/描画/プローブへ分岐する。
TM用read_solutionは従来どおりTEを拒否する。
プローブには元native全ファイルhash・規格化・位相・領域外NaN/insideを記録する。
GUIの描画cacheへTE関連実装のhashを含める。

## 途中検証

開始時に直前標準763件・443対象hashと現在ソースの一致を確認。
旧plot_modeがTE保存を拒否する反例をout/te-gui-development-20260909/red.txtへ保持。
追加3検査の初回はテストのsave_run/sphere呼出し誤りで3ERROR。呼出し修正後は3件1.339秒PASS。
境界表示追加後も3件1.345秒PASS。既存TM描画2件0.015秒PASS。
追加検査はP1/P2/曲線P2の成分/CSV/元hash/位相/軸、円筒Bessel解析の場成分1%以内、plot分岐とstrict mode。
保存球形の初期図を目視し、モード名変数が成分ループで上書きされる表示ミスを修正した。
初期図はout/te-gui-development-20260909/curved.pngに保持する（タイトル修正前）。

GUIにTM/TE選択・明示モデル保持・TE説明・N/A理由表示を追加。
実Chrome検証器scripts/verify_gui_te.mjsを作成。初回は実TEジョブ完了後の「結果を開く」操作が欠けていた。
この初回は製品GUIの描画合格として数えない。

## 残る受入

- Chromeの結果選択・描画・Project完全往復、プローブdownload/metadata、TMへの切替。
- 曲線TEを含む実GUI/保存場照合、必要に応じた未対応操作の理由表示。
- 最終標準、既存TM周波数/RF、ソース一致、README/対応表/計画/実装状況・来歴・ローカルコミット。

## ブラウザーで判明した問題と修正

初回18003終了1: 結果選択を省いた検証器のtimeout。次の2回も終了1で、一覧再描画前の古いDOMボタン（幅0）をクリックしていた。現在のボタンを再取得する検証器へ修正。
99816終了1では実際の製品不具合を確認: 画像生成後のGUI cache記録がTM専用results.case_sha256を要求し、TE画像を返せない。
TEだけは検証済みcase.jsonのdigestを記録し、TM従来値は保持する。旧サーバー12799/PID862617をSIGINT終了0後、新サーバーで再実行した。
87096終了1はフォームの省略値と正規化済みProjectを直接比較した検証器の誤り。strict normalize後の完全Project同士で比較するよう修正。
最終の限定ブラウザー77891終了0、out/browser-te-normalized-20260909/report.json・driver.mjs・te-fields.png。TE選択/実FEM/N/A・画像読込・再読込完全往復の4項目PASS、外部HTTP要求0、実装hash前後一致。
スクリーンショットを目視。低分割P1による場の段差は平滑化しない。日本語Case名がMatplotlib既定フォントで欠字になる点は残り、描画フォントの対応を確認する。
サーバー25384/PID876859もSIGINT終了0。全ブラウザー試行とサーバーは終了済み。
これはプローブdownload・曲線GUI・TM切替・最終標準を含む全受入ではない。

## 拡張受入の進行（2026-09-09）

TE詳細RF表のnullにもN/A理由を表示。選択したTE結果ではTM専用の円筒比較・バンド同定・連続表面ピーク操作を無効化し、理由を表示する。TMへ切り替えた結果では通常操作へ戻す。
図タイトルはインストール済み日本語フォント（Noto CJK/IPA等）があれば選択する。フォントを同梱・自動取得しない。フォントがない環境での日本語表示保証はしない。
追加3検査3541終了0、1.350秒。拡張Chrome55711は終了1で、P1プローブ保存・TE専用操作制限・曲線P2実計算/描画まで合格したが、曲線プローブdownloadの15秒待機を超えた。
サーバー側のCSV/metadata完成を後で確認。単独保存プローブ37560終了0、9.644秒（HTTPでは前段read_job完全再検証もある）。検証器のdownload待機を180秒に変更し、10868で再実行し終了0。初回driver/reportはout/browser-te-expanded-20260909へ保持。
標準67203をout/validation-gui-te-20260909で実行。終了後の結果は以下に記録する。

## 拡張GUI・独立照合の合格

拡張ブラウザー10868終了0、out/browser-te-expanded-wait-20260909。Chrome10項目PASS、外部HTTP要求0、実装hash前後一致。P1 TEの選択/実FEM/描画/Project往復/プローブ保存、TE専用操作制限、曲線P2の実FEM/描画/プローブ、TM切替と通常操作/プローブを確認。両図を目視し、日本語Case名も表示できた。
GUI21290/PID882385はSIGINT終了0。新管理器で全3保存結果をverify=True再検証し、新規API FEM3回と係数/周波数完全一致を確認した。
独立72935終了0、out/te-gui-independent-20260909。download CSVの全成分を保存samplerへ照合し、TEのB=μ0H、規格化/全native hash、TM旧列を確認。球形TE3モードの独立最大相対差はf 2.500e-5、G 2.824e-3、場1.506e-3で既存許容差PASS。独立/現在448対象hash一致、ブラウザーの実装hashとも一致。
GUIの低分割P1表示例については物理精度合格を主張せず、保存値との同一性と操作受入を確認した。球形解析の精度検証とは区別する。
標準67203終了0、最終比較80319終了0。標準766件中764合格・2skip（unittest1175.340秒、command1175.692秒）。TM seed9モード19量の周波数差0、RF最大8.882e-16、旧直線/曲線TE保存7件のRF差0。標準・独立・固定時・終了後448対象hashとブラウザー実装hashが一致。

## 最終記録

標準766件中764合格・2skip（unittest1175.340秒、command1175.692秒）。TM seed9モード19量の周波数差0、RF最大8.882e-16、旧直線/曲線TE保存7件のRF差0。標準・独立・固定時・終了後448対象hashとブラウザー実装hashが一致。

標準outにcommand.log/tests.log/validation.json/source-fixed.json/verify_completion.py/comparison.log/seed_regression.jsonを保持。全関連実行は終了し、ソース固定を解除した。新規Wine/legacy実行・Hosted CI・他OSの実行はない。
