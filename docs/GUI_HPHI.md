# 正半径Hφの保存場表示とGUI

後続の[独立Hφ Study](HPHI_STUDY.md)を保存/実worker/CLI/GUIへ接続・限定受入した。収束・追跡・軸接続の穴付き領域は別工程。
2026-09-12：[表示計画](HPHI_GUI_PLAN.md)に従って主ツリーへ統合・限定受入した。
固定コピーでの全体回帰と主ツリーのソース同一性を確認し、主ツリーでも専用unitとCLIを再実行した。

## 元の場と物理量

閉同軸円筒と正半径の明示一般断面・複数穴を、専用HphiProjectとhphi_solveジョブから開く。
図はzを横軸、rを縦軸とし、SIの元座標からm/mm表示へ変換する。元P1セルは一枚、P2セルは四枚の
表示三角形を使い、親セルと重心座標を保持して元係数から片側の場を評価する。節点への勾配平均化は行わない。
真空の元三角形だけを描き、内導体・凹外周の外部を塗らない。全PEC境界を線で示す。

Hφ realとEr/Ez quadratureを各々符号付きの対称色範囲で表示する。
peak exp(+iωt)、real+i·quadratureを明記し、Hφの規約と軸接続TMの別規約を暗黙変換しない。
表示の最大標本を表面ピークやその精度保証として扱わない。
SIプローブにはE/H/Bの全18成分を出力し、内導体内部・軸・領域外は拒否する。

RFは全3D U[J]・全壁損失P[W]・Q0・Gを保持する。円筒の内外壁/端板と、一般断面の
境界成分/各元線分の壁損失を確認できる。R/Qの加速器/回路両規約と加速電圧はN/A理由を表示する。
周波数順位を追跡IDとせず、completeを離散化精度の合格と表示しない。

## 入力・保存・ジョブ

`/hphi.html` の専用画面からProject読込/保存・円筒寸法/分割/P次数/RF入力・JSON編集、
実worker開始/中止、直接native/管理済みジョブ取込、元場のモード切替、画像/CSV/元5ファイルの取得を行う。
一般断面の外周・全穴・節点・接続をProjectで欠落なく保持する。未対応物理の入力失敗では既存入力を保持する。
保存ジョブをURLから復元し、サーバー再起動後も同じProjectで新しいジョブを実行できる。
通常履歴からHφ専用画面へ開き、Hφジョブを既存の軸接続/平面追跡候補へ混ぜない。

既存の局所HTTP Host/Origin/tokenとstrict action検査を使う。
場を開くときは全nativeを完全再検証する。CSV/PNGのsidecarは全元hash、単位・位相、順位、RF、データhashを保持する。
既存出力を置換せず、画像/プローブをnative内部へ追加しない。GUIのcacheは全native・実装・依存版・順位・表示設定に束縛し、
表示応答前後に元のhashを照合する。ダウンロード対象は元5ファイルに限定する。

CLIは次のとおり。`points.json` はSIの `[[r,z], ...]`。

```sh
python -m superfish_ng plot-hphi saved-native --mode 2 --length-unit mm --mesh --out new-fields.png
python -m superfish_ng probe-hphi-csv saved-native --mode 2 --points points.json --out new-probe.csv
```

## 検証と失敗履歴

元セル・CSV/PNG・source変更拒否の3unitと、両native/実worker・probe/cache・実HTTPの4unitが合格した。
初回HTTPはsandboxがbindを拒否したため、その環境拒否だけskip可能にし、許可されたローカルHTTPで全4件を再実行して合格した。
アプリのHTTP失敗を成功として扱っていない。

独立 `scripts/validate_hphi_display.py` は既存の解析受入済み円筒TEM/矩形穴nativeを完全再生する。
両幾何・両次数・二尺度の8件で元表示配列のH/E、位相と規格化、穴を除いた面積/3D体積、
18成分プローブ、16実CLIのCSV/PNG・元hashが合格した。160.992秒、固定581source。
最大表示標本誤差はP1でH=4.287e-4・E=1.636e-2、P2でH=1.244e-4・E=1.497e-3。
これは元標本の確認で、新しい離散化精度や表面ピークの受入ではない。既存の細分・場/RFゲートを保持する。

実ChromeはHφの再起動復元を含む9操作と、既存軸接続TM/TE・平面TM/TE/追跡候補の5操作で合格。
初回Hφ検証はページ読込前の状態参照、既存画面検証は日本語状態名の待機条件とCDPのawait構文、
再起動版は新規Projectの非同期反映を待つ前の入力操作で失敗した。各失敗reportを保持し、
検証器の待機・構文を修正して同じアプリソースで再実行した。図やHTTP応答だけをブラウザー合格と数えない。

再起動後19完了・3取消ジョブを検証し、以前のnative 100ファイル不変。
ブラウザーとCLIのCSV・metadata・PNGはbyte単位で一致し、既存4画面の結果全文も保存nativeと一致した。
円筒・矩形穴・斜め穴・凹外周の実画像を確認。全ゼロの色範囲は、明示した描画fixtureでEzだけをゼロへ置換して検査した。
fixtureの画像へ「計算場ではない」と表記し、FEM/物理受入・native比較には使っていない。

証拠はout/hphi-display-independent-first-20260912、out/hphi-gui-browser-restored-20260912、
out/hphi-gui-existing-browser-complete-20260912、out/hphi-gui-artifacts-20260912、out/hphi-gui-development-20260912。
全ブラウザー・ローカルサーバーは終了済み。最初の標準65753は終了143で中断。理由未特定・結果なしで受入に数えない。581source不変と子プロセス終了を確認し、out/validation-hphi-gui-candidate-retry-20260912で再実行し、下記のとおり合格した。中断記録はout/hphi-gui-development-20260912/interrupted-standard.json。

新規外部資料・依存・旧版参照なし。既存自作の平面表示/GUIとHφ専用FEM/Project/Jobを接続した。
曲線・軸接続の穴付き領域、HφのStudy/収束/追跡等は後続。P03/O02と全計画は未完。

## 最終受入記録

標準1014件（1011合格・3skip）は1812.958秒でPASS、ResourceWarningなし。
3skipは任意NGSolve参照環境2件と、sandbox内で待受できない実HTTP検査1件。
主ツリーの実HTTPを含むGUI4unitは許可されたローカル実行で5.979秒、表示3unitは1.271秒で合格した。
主2CLIのCSV/metadata/PNGも、検証済みブラウザー保存とbyte単位で一致した。
固定候補581source、主587source（従来の不変egg-info 6件を含む）が対応する。
既存seed9モード19量はf差0、最大相対差8.882e-16。既存ベンチマークを更新していない。
証拠はout/validation-hphi-gui-candidate-retry-20260912/seed_regression.json、out/hphi-gui-main-cli-20260912。
候補の内部作業用アーカイブはout/hphi-gui-development-20260912/frozen-candidate-source.tar.gzとarchive.json。
次の[独立Study](HPHI_STUDY_PLAN.md)と[軸接続の穴付き領域](AXIS_CONNECTED_HOLES_PLAN.md)は別工程として進める。
