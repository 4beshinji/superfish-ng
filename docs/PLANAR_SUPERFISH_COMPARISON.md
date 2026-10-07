# C07-planar：平面TE/TMの参照比較準備

2026-10-07、先行B03/P09 DONE後の有界変更。今回の受入は、既存比較入口からの
候補デッキ/NG入力・版付き表の生成、未知の参照をPASSへ数えないこと、出力保全とstrict拒否。
新5検査＋既存TM比較5/TE相補比較2、計12件0.772秒、実終了0/PASS。
旧ソルバーとNGの新求解はともに0。**C07-planarはIN_PROGRESS、旧Cartesian比較はUNVERIFIED**。

## ケースと現存する証拠

対象は合成真空・閉PEC矩形の遮断問題。座標はxy、z方向に一様、伝搬定数0。
幅0.31 m/高さ0.2 mとその二倍で、TE10/TE01/TM11を分ける。
各ケースでNG P2のnx=ny=16/32/64、候補旧版DX=min(a,b)×100/n [cm]を用意した。
これは両側細分の入力準備であり、両側の数値収束を実施した証拠ではない。

| ケース | 尺度 | 解析ラベル | 旧版/入力・設定/hash | モード対応/両側細分 | f / 場 / RF / 表面 | F/I/O/N/W |
|---|---:|---|---|---|---|---|
| te10-scale1 | 1 | TE(1,0) | 期待7.17・実版未観測、3水準/各5ファイルhash保存 | 未実施、index=null | 全UNVERIFIED | 全UNVERIFIED |
| te01-scale1 | 1 | TE(0,1) | 同上 | 同上 | 全UNVERIFIED | 全UNVERIFIED |
| tm11-scale1 | 1 | TM(1,1) | 同上 | 同上 | 全UNVERIFIED | 全UNVERIFIED |
| te10-scale2 | 2 | TE(1,0) | 同上 | 同上 | 全UNVERIFIED | 全UNVERIFIED |
| te01-scale2 | 2 | TE(0,1) | 同上 | 同上 | 全UNVERIFIED | 全UNVERIFIED |
| tm11-scale2 | 2 | TM(1,1) | 同上 | 同上 | 全UNVERIFIED | 全UNVERIFIED |

原ケース表は `out/c07-planar-preparation-20261007/candidates/comparison.json`。
6ケース×3水準×5入力=90ファイルのSHA-256、原入力、mesh、候補boundary宣言、
f初期値、未実行のcommand/exit=null/120秒上限、四量と全受入軸の理由を保持した。
GUI/一般AF変換/保存結果変換/実旧版実行をこの準備検査のPASSへ数えない。
加速電圧と加速器/回路定義R/Qは、有限加速経路がない断面という理由付きN/A。
参照不在・未知仕様はN/Aへ変更しない。

矩形の独立解析f=c0/2 sqrt((m/a)^2+(n/b)^2)は探索初期値と尺度不変量だけに使用。
FEM解や比較結果へ代用しない。実モード対応は同じ全体phaseによる元E/Hの両一致を要する。
TE01を順位や近い周波数だけで同定せず、縮退/guard不足では個別対応を未確認に保つ。
RF壁積分と表面peakは別判定し、周波数/Gの一致をpeak精度の根拠にしない。

## 候補デッキの意味と未確認事項

AFは独立に作成した全矩形の閉外周、ICYLIN=0、CONV=1、cm座標、正のDX/周波数hint。
全四辺SEGと、内部二線＋全四壁の符号付き場を要求するIN7、局所SF.INIを添える。
TE候補の全外周NBS=1、TM候補の全外周NBS=0は、Hz Neumann/相補Dirichletを試すための仮説。
7.17の境界解釈・偏波と一致したとは主張しない。直線入力候補の作成を製品AF importer受入に数えない。
未知の曲線/材料/軸対称Caseをこのwriterへ渡すことは拒否する。

NG入力は専用PlanarCase、SI・peak exp(+iωt)、U′=1 J/m、側壁だけのP′[W/m]。
旧版ENERGY/POWER/SF7を軸対称比較器へ渡す処理は追加していない。
Cartesianのsigned成分/phase/振幅、SFOエネルギー/損失の長さ規約、相補TMでの損失制限を
対象出力と独立Maxwell/面積・壁積分で確認するまで変換・規格化・RFゲートを実装しない。

この環境では `wine` / `wine64` / `Xvfb` がPATHに存在せず、以前の
`/tmp/superfish-wine-runtime` と指定旧root `/home/sin/code/superfish` も存在しない。
実行ファイルの内部/ソースを読まず、ソフトを取得・コピー・インストールしていない。
将来の旧版実行では、既存の許諾内でWine/prefix/displayを確認し、全processへ120秒上限を実際に適用する。
表の未実行commandに上限を記載したことは、実行/取消し/失敗保存の受入ではない。
終了非0/timeout/版不一致/欠損出力は原logを残してUNVERIFIED/FAILを別記する。

## 入口と確認したコマンド

```sh
OPENBLAS_NUM_THREADS=1 UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python scripts/compare_superfish.py --planar --prepare-only --out out/c07-planar-preparation-20261007/candidates
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python -m unittest -v test_planar_superfish_preparation test_superfish_comparison test_superfish_te_comparison
```

準備CLIの実終了は**3（UNVERIFIED）**、ログは同親rootの `prepare.log`。
数値比較PASS=0/FAIL=1、引数拒否=2と区別する。既存出力の上書き・out境界脱出は拒否する。
`--planar` または `--prepare-only` 単独、`--run-legacy`との混用も実終了2で拒否し、出力を作らない。
通常の軸対称比較入口/変換規約は維持し、旧比較器7件も確認した。
unitの原logは `selected-tests.log`。90入力とケース表の読取監査は `preparation-acceptance.json`。
全検証・seed・専用FEM validatorはこの検証準備だけの変更で再実行しない。
P09の直前全検証は2359検査/479モジュールで実終了0、今回の限定12件と重複集計しない。
製品srcの科学源は変更していない。
最終読取監査は終了0、全420製品ファイルはP09受入源と一致し、全123カードの差はC07-planarの着手だけ。
初回監査の420件assertはsrc/直下のegg-info6件も数えたためAssertionErrorとなり、
`initial-audit-failure.json`へ保持した。製品範囲をsrc/superfish_ng/へ正して全hashを照合し、科学検査や許容差は変更していない。

## 来歴と次の範囲

再利用は自作のPlanarCase/strict入力、既存AFの直線構文・中立的なINI/IN7輸送だけ。
旧場の成分換算や単位長規約を軸対称コードから推測して移植していない。
[USPAS公式紹介](https://uspas.fnal.gov/resources/downloads.shtml)はCartesian/軸対称の機能分類のみを確認。
[2011 USPAS講義、Proton_5.pdfのPDF18ページ/印刷18](https://uspas.fnal.gov/materials/11ODU/Proton_5.pdf)は
矩形モードを遮断問題と説明し、1 cm長の電力という規約を示す。これは版7.17の
SFO energy/phase/相補TM契約を確定する根拠にはしない。web抽出は読めたが画像取得はCache miss、
講義のNT円弧指定は現行旧仕様と異なるため再利用しない。
既存1987公開manualはRF/SFO章がIn Processで、欠落R25の代用にしない。
検索に混入したlegacy鏡像リポジトリは開かず、ソース/バイナリ/数値snippetを使っていない。
新依存・Hosted CI・GPU・実測比較はなし。

これはC07-planarの矩形準備leaf。原カードの対象を矩形だけへ縮小しない。
次はP09の円/非円形/曲線元領域・実ID/調整条件とP04多角形条件を版付き表へ対応付ける。
旧版での厳密な二次領域/曲線指定が不明な場合、勝手に直線化して同一領域と宣言しない。
原32互換要件/全123カード/全goalは継続する。
