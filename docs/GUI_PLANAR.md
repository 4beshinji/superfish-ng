# 平面RFの表示とGUI

専用xy表示・SIプローブと `/planar.html` を接続した。独立場・ブラウザー操作・保存再起動・標準/既存数値回帰を確認し、以下の範囲で限定受入。[受入条件](PLANAR_GUI_PLAN.md)。矩形Case版1・明示単純多角形版2、TE/TM、P1/P2と専用PlanarProjectを保持する。

## 起動と操作

```
python -m superfish_ng gui --workspace out/my-gui-workspace
python -m superfish_ng plot-planar out/my-planar-job/solution --out out/my-planar-fields.png --mode 1 --mesh
python -m superfish_ng probe-planar out/my-planar-job/solution --points points.json --out out/my-planar-probe.csv
```

GUI起動URLを開き「平面RFワークスペース」へ移動する。同じローカルセッション・workspace所有・実workerを使う。平面画面から軸対称画面へ戻れる。軸対称履歴の平面ジョブはジョブID付きURLで専用画面へ開き、軸対称モード追跡の候補には含めない。

矩形は名前、表示単位m/mm、寸法、分割数、次数、モード数、TE/TM、単位長エネルギー、壁導電率を編集する。表示単位の切替でSI座標を変えない。多角形は読み込んだ元メッシュを保持し、共通物理条件を編集できる。元座標/接続変更は「Project JSONを編集」で全文を編集して明示適用する。JSONの座標は常にm。未知キーを含む不正文書は現入力を置換しない。曲線・材料・穴・伝搬・平面Study/追跡/調整は未対応。

結果取込は直接nativeまたは管理済み平面ジョブを指定する。元係数と元メッシュを保存して再検証し、新しい計算とは区別する。結果を開くと保存Projectを復元し、「計算を開始」で新しい実workerに投入できる。履歴から中止と完了結果の選択を行う。完了は整合性確認であり、メッシュ精度合格とは表示しない。

## 場・単位・出力契約

TMは実Ez、quadrature Bx/By、TEは実Bz、quadrature Ex/Eyを符号付きで表示する。全図でゼロを中心に正負対称の色範囲を用いる。xy軸、長さ単位、PEC、exp(+iωt)のピークphasor、quadratureが+i成分であることを明示する。B=μ0H。U′はJ/m、壁損失P′はW/m、Q0/Gを表示し、二つのR/Qと加速量は有限加速経路がないためN/Aとする。

表示は元FEM要素内の評価で、P1は一三角形、P2は四表示三角形に分け、その中心で正確な元多項式・勾配を評価する。色は各表示三角形で一定。節点補間でP1の勾配不連続を平滑化しない。元要素番号と重心座標を保持し、境界で別要素を誤選択しない。表示細分は再計算や表面ピーク・収束認証ではない。描画による数値積分でRF値を置換しない。

SIプローブCSVは既存の14列（x/yと全E/Hのreal/quadrature成分）を維持する。座標配列の全点が領域内であることを要求し、外部点・非数値・無効モードを拒否する。CSVとPNGには `.csv.json` / `.png.json` を付け、元native全五ファイルのhash、出力hash、Case、モード順序、規格化・位相、RF量、精度未検証状態を保存する。GUIではプローブ情報を別ボタンで保存する。

図/プローブは元native外の新しい出力だけを作り、既存出力とmetadataを上書きしない。完全native再検証後に評価し、元hashを公開前後で確認する。metadataを先に、データを最後に排他的リンクで公開する。通常plotも明示した平面formatから専用描画へ分岐し、軸対称zプローブ引数は拒否する。

GUI描画cacheは全native・実装hash、依存版、モード・表示単位・メッシュ設定で分ける。保存画像/CSVとmetadataのhashを照合してから返し、リンクや改変cacheを拒否する。操作APIは既存Host/Origin/tokenとstrict actionキー検査を共有する。

## 検証経過と現在の証拠

- 開始前の旧plot_modeは平面Caseを軸対称readerで拒否した。out/planar-display-development-20260910/preflight.log（終了1）を保持。
- 追加表示4unitがPASS（1.665秒）。矩形/多角形・P1/P2・TE/TM・二尺度の親要素/全成分、独立矩形sin/cos場、B=μ0H、metadata/出力保護/strict入力を検証。
- 追加GUI3unitの初回は管理器が付加するidを保存状態と直接比較して3ERROR。管理器の同じ形式で比較するよう修正し3PASS（2.987秒）。初回と修正後ログを保持。
- 平面関連50検査と新旧表示9検査がPASS。製品FEM・既存nativeの数値式/許容差は変更していない。
- Chrome初回は非同期新規作成/ファイル読込の待機不足で単位変更待ちが停止。待機後は10操作が通過したがページ遷移直後の未定義変数参照で停止。さらに待機を直すと、実際の製品不具合であるquery付き静的ページURLの404を確認した。URLのpath部分でページを選ぶ修正とサーバー再起動後、out/browser-planar-fixed-20260910は13項目PASS、外部HTTP要求0、src hash不変。先行3試行のログとreportを保持。
- Chromeでは矩形TE/多角形TM実worker、単位変更、Projectファイル往復、画像/プローブ/nativeダウンロード、領域外拒否、直接/管理済み取込と再実行、不正文書時の現入力保持、実中止、追跡候補除外、ジョブURLからの復元を確認。polygon-fields.pngを目視してxy軸・符号・単位・要素ごとの段差を確認した。
- out/planar-display-independent-20260910は21.591秒、499source不変でPASS。既存細分native8件の20モードを独立sin/cos場と同じ位相で照合し、表示中心での最大縦場誤差5.872e-5、横場誤差0.004574。粗い画像の精度を保証する結果ではない。回転2角・二尺度・P1/P2・TE/TMの16native/64モード、別の参照FEM4件に対するベクトル成分の最大相対差4.966e-14、SIプローブ16件、実CLI画像8件と元hash不変もPASS。
- out/planar-gui-independent-20260910はブラウザー生成結果と独立参照FEM2件の全係数/結果一致、HTTP結果/全nativeダウンロード、二取込と再実行の元hash、プローブ全12成分、認証拒否・未知引数拒否・query付きURLの4HTTP確認がPASS。

既存軸対称GUIはout/browser-axis-regression-planar-20260910で10操作PASS（TM/TE/曲線TE、画像・プローブ・Project往復）。再起動後Chromeはout/browser-planar-restarted-20260910で3保存ジョブを復元して第2モードを描画しPASS。専用サーバーは正常終了し、out/planar-gui-restart-20260910で平面5件/軸対称3件と保存画像/プローブの再検証がPASS。標準out/validation-planar-gui-final-20260910は856件（854合格、2skip、unittest1238.757秒）で終了0。旧平面32件/TE10件のnative再生はout/planar-gui-native-regression-final-20260910でPASS。TM seed9モード19量f差0/RF最大8.882e-16と499source、独立24表示出力・保存ジョブ/画像のhashを最終照合してPASS。標準ディレクトリにverify_completion.pyとseed_regression.jsonを保持。全関連実行と専用GUIサーバーは終了済み。既存.manager.lockのResourceWarningは原因未確定のまま残る。親P02・全計画の受入は未完。

[後続の平面Study・収束比較・追跡](PLANAR_STUDY_PLAN.md)は設計段階。現行GUIの受入に含めない。
