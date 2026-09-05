# セミナーマイルストーンの受入監査

2026-09-05。**S1〜S6のマイルストーン完了**。追加Wine参照を使う全NG新規再実行
`out/seminar-suite-final-20260905` は9数値ジョブ・7ページ検査が合格し、実行中ソース変更なし。
初回 `out/seminar-suite-20260905` のπ参照細分FAILは別途保持し、上書きしていない。
対象とPDF原本hashは [MILESTONE_SEMINAR.md](MILESTONE_SEMINAR.md)、操作は [SEMINAR_SUITE.md](SEMINAR_SUITE.md)。

## 要求と直接エビデンス

以下の相対パスの基準は `out/seminar-suite-final-20260905/`。

| 要求 | 検査範囲と直接エビデンス | 現状 |
|---|---|---|
| S1: Pillbox TM010/TM011 | `pillbox/comparison.json`：長さ40/80/120 mmの各2モードを解析・細分検査。80 mmの2モードをWine/SF7で照合 | 数値PASS |
| S1: 半領域 | `symmetry/comparison.json`：z_min/z_maxでTM010の電気対称とTM011の磁気対称の4条件。解析、独立全領域FEM、全領域Wine参照、半/全場・損失・電圧を確認 | 数値PASS |
| S2: 平坦4セル | `flat4/comparison.json`：4モード、NG3段階・Wine4段階。垂直段差の面積・境界・正面積はメッシュ生成と回帰テストで検査 | 数値PASS |
| S3: 円弧4セル | `rounded4/comparison.json` と `geometry4/comparison.json`：半径保持、FEMと弦誤差を別に細分。全4モードとWineを照合 | 数値PASS |
| S3: 円弧7セル | `geometry7/comparison.json`：固定nr=128・交差分割で弦誤差3/0.75/0.1875 µm、面積誤差は約1/4ずつ減少。rounded7/comparison.jsonに全モードの照合とπ追加DX=0.01 cm | NG/形状細分・NG–Wine差・Wine細分すべてPASS |
| S4: モード同定と分散 | `flat4` / `rounded4` / `rounded7` のcomparison.json、dispersion.csv/png。符号・零交差・cosセル振幅と一対一同定、fit残差を保持 | 全4/7モードの同定・分散出力を確認 |
| 端部full/half比較 | `end_cells/comparison.json`：iris中心切断と空洞中心切断、flat/rounded各4モード。full側にhalf側位相名を流用せず、零交差と実場で比較 | 新規計算・細分PASS |
| S5: 表示・操作・保存 | 各例題index.html、電磁場・軸上/半径プローブPNG/CSV、CLIのmesh表示、入口の例題選択。headlessの実キー・画像・リンク検査 | 全7ページ検査PASS、入口と7セルπ画面の目視確認済み。旧FAIL表示も保持 |
| S6: 全例題新規計算 | suite.jsonの全9ジョブ、各コマンド・終了コード・レポートhash、実行前後のソースhash。NG保存場の再利用なし | 9/9数値ジョブPASS、69テストPASS、7/7画面PASS、ソース変更なし |

Pillboxの40/120 mmとfull-end比較形状について、Wineを直接実行したとは主張しない。
Pillboxの長さ変更は解析解、full-endは幾何不変量・新規FEM細分・保存された場で検査する。
Wine直接照合の対象は80 mm PillboxのTM010/TM011、平坦4セル、円弧4セル、円弧7セルの計17モード。

## 数値・実行の合否

対応するモードごとに周波数差0.1%、Q0/G/壁損失/RQ/TTF差1%、Uを揃えた符号付き軸上Ezの相対L2差1%未満。
NGとWineの最終2段階も同じ周波数・RF基準で検査する。固有値残差の小ささで離散化誤差を代用しない。
R/Qが小さいときの絶対差は `|RQ_NG−RQ_Wine|` [Ω]、相対差は `|RQ_NG/RQ_Wine−1|` と区別する。
絶対差は解釈用で、現在の1%相対ゲートを無効にする別の合格条件には使わない。

失敗した旧計算や初回のR/Q未収束はout/へ保持し、最新の合格例で上書きしない。
終了コード0とreport.passed=trueの両方を要求し、未生成・不正なレポートも成功にしない。
最終suite.jsonのSHA-256は `26bc55c9a4b8f7d01707173d3b2572e560f67c726968ab3f2a119d403ba95aed`。
全子レポート、参照AF/SEG/SFO/SF7/ローカルSF.INI、画面とリンク先のhashを再確認した。

### 最後に解消した未達：7セルπモード

WineのDX=0.0125→0.01 cmのR/Q変化は0.658403%、TTF変化は0.324383%で、ともに1%未満。
最終Wine R/Qは0.008888054453 Ω、NGは0.008820750903 Ω。
両者の差は相対0.757236%、絶対0.00006730355 Ω。周波数差0.000184381%、軸場L2差0.00897126%。
微小RQの誤差は非単調であり、厳密解への保証とは区別するが、事前の細分・照合ゲートを変更せず満たした。
π以外の6モードは最終DX=0.0125 cm。旧3段階はlegacy、新しい判定対象はfinal_legacy_modesを参照。
RAM設定で失敗した試行も保存。ディスク設定の追加Wine/SF7は終了コード0、既設設定は変更していない。

## このマイルストーンで保証しないこと

- 旧ソフトウェアの完全な入力互換性やWindows右クリックメニューの複製。
- m>0、TE、同軸TEM、静電/静磁場、開放ポート、3D、一般CAD、材料非線形。
- 測定値への一致、実機設計の認証、一般的なモード交差追跡、周波数チューニング。
- 鋭い角や接線不連続点の表面ピークのメッシュ独立精度。出力値はP1による推定として扱う。
- Wineの半領域またはfull-end比較形状の直接計算、別OSでの動作、Hosted CI。

旧ソルバーのソース・実行形式・原本PDF・生Wine出力は実装配布物へ含めない。
独立実装という来歴の範囲と限界は [PROVENANCE.md](PROVENANCE.md) に明記する。
