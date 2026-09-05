# 多セル演習：垂直段差メッシュの実装記録

2026-09-05。段差・円弧・4/7モード同定・分散フィット・HTML表示を実装した。
多セル演習の受入条件を達成。最新の全NG新規計算は `out/seminar-suite-final-20260905` で全検査PASS。
以下には開発時の未達試行も履歴として残す。最新の判定は [MILESTONE_ACCEPTANCE.md](MILESTONE_ACCEPTANCE.md) を参照。

## 最終一括検証と7セル追加参照

flat4・rounded4・rounded7の全モードが、NG細分・Wine細分・両コード差のすべてで合格した。
端部full/half比較、円弧近似を別に細分する試験、全画面検査も合格。69件のunittestを含む9ジョブはすべて新規NG計算。
Wineは検査済み生出力を再利用し、AF/SEGのバイト一致、場による同定、入力・出力hashを確認した。

| 形状 | 最大周波数差 [%] | 最大R/Q差 [%] | 最大軸場L2差 [%] | 最終Wine DX [cm] |
|---|---:|---:|---:|---|
| flat4 | 0.000421 | 0.059415 | 0.010529 | 全4モード0.01 |
| rounded4 | 0.003151 | 0.402161 | 0.064637 | 全4モード0.0125 |
| rounded7 | 0.000184 | 0.757236 | 0.008971 | πのみ0.01、他6モード0.0125 |

初回一括 `out/seminar-suite-20260905` はπモードのWine R/Q最終変化1.98217%とTTFでFAILだった。
追加DX=0.01 cmではR/Q変化0.658403%、TTF変化0.324383%で合格。1%閾値を緩めていない。
RAM設定での0.01/0.011失敗は残し、ローカルSF.INIで作業データをディスク保存した追加計算が正常終了した。
既設設定と物理条件は変更していない。微小RQの非単調な変化も含め、厳密値を保証する主張ではない。
最終π周波数はNG 2863.412120 MHz、Wine 2863.406840 MHz。R/Qの絶対差は0.00006730355 Ω。
元の全バンド3段階はlegacyに保持し、追加履歴はsupplemental_legacy、最終判定はfinal_legacy_modesに記録する。

## 追加検証：flat4の全照合合格と交差分割

`out/seminar-flat-ready-20260905/index.html` は全4モードの数値ゲートPASS。
NGのnr=128/256/512とWine dx=0.05/0.025/0.0125/0.01 cmを使用し、最終2段階も独立に検査した。
既存の保存場・生Wine出力を検査して再利用したレポートであり、このHTML生成時に全計算を再実行したものではない。
最大周波数差0.000421%、最大R/Q差0.059415%、最大軸上場L2差0.010529%。
Wine最低モードR/Qの最後の細分変化は0.184916%となり、前段の1.085%未達を解消した。
`out/gallery-test-flat-ready-20260905` で全4モードの実キー入力・16リンク/画像をheadless検証した。

7セルでは、従来nr=64の0モードに1.0000→0.9901のセル振幅の傾きがあった。
`mesh.triangulation:crossed` で四辺形を中心節点へ4分割すると、0/πモードの等振幅は約1.3e-10以内になる。
これはFEM空間の変更であり、解いた場の平均化や数値補正はしていない。既定のdiagonal分割は維持する。
`out/seminar-seven-crossed-probe-20260905` のnr=64→128でπモードR/Q変化は約1.83%に低下したが、まだFAIL。
追加nr=256の生計算は `out/seminar-seven-crossed-fine-20260905` に保存した。
nr=64/128/256を使った `out/seminar-rounded7-crossed-native-20260905/index.html` は全数値ゲートPASS。
πモードR/Qはnr=128で0.0089600333 Ω、nr=256で0.0089034259 Ω、最終変化0.6318%。
別の固定nr=128・弦誤差12/3/0.75 µm試験も全量PASS（最大変化0.988403%）。
結果は `out/seminar-rounded7-crossed-geometry-20260905/comparison.json`。閾値は1%のまま変更していない。
この7セルPASSはNG内部の収束であり、Wine照合の完了ではない。
円弧4セル半領域から7セルへの偶対称反射だけでは改善しなかった試験も
`out/seminar-seven-parity-probe-20260905` に保持する。

円弧4セルWineのdx=0.05/0.025/0.0125 cm計算は完了し、全照合・両コードの収束がPASS。
`out/seminar-rounded4-wine-comparison-20260905/index.html`：最大周波数差0.003152%、Q0差0.001365%、
R/Q差0.402161%、軸上場L2差0.064637%。Wineの最大R/Q細分変化は0.371362%。
円弧7セルWineの3段階計算は `out/seminar-rounded-wine-20260905/rounded7` で完了。
全modeのSFOとOUTSF7を確認した。πの追加参照と最終判定は冒頭の最終一括検証を参照。

## 再現方法

```bash
superfish-ng solve examples/seminar_4cell_flat.json --out out/flat-new
superfish-ng plot out/flat-new --mode 4 --mesh --out out/flat-mode4-new.png
```

形状はユーザー提供のflat入力の数値寸法をSIに変換して定義した。端部は半セル。
既存legacyのコード・説明文・計算アルゴリズムを転記したものではない。
本例題は `schema_version:2`、`geometry.type:stepped_profile` を使用する。
従来のprofileは引き続き厳密なz増加を要求するため、既存入力の意味は変えない。

## メッシュの構成と不変量

各非垂直壁区間をz方向の台形スラブに分ける。全体で共有する絶対半径の格子を用い、
高さの異なる左右列を三角形で接続する。段差の下側は隣接スラブと節点を共有し、
上側のディスク面は正確な垂直境界として残す。急な斜面に置き換えたり、ディスク内部を埋めたりしない。
半径格子は一様格子にすべての壁頂点半径を加えたもの。浮動小数点の近接重複だけを除き、壁座標は保持する。

正Jacobian、辺の非多様体性、境界頂点次数、連結性、Euler標数、全境界辺の所定輪郭への包含、
周長と断面積を検査する。負面積・欠落境界・穴・亀裂を成功として渡さない。
長方形の和で構成した段差fixtureに対し、定数uの質量積分 `Σ Δz R⁴/4` と
剛性積分 `2Σ Δz R²` を独立に検査した。斜面と段差の混在、ディスク内プローブの領域外判定、
通常pillboxとの周波数・Q・R/Q一致もテストする。

既存のFEM積分とRF式は変更していない。49件のunittestと
`out/validation-stepped-20260905` の既存数値検証が合格した。

## 初回のWine照合（収束受入前）

NGの初回入力はnr=64/nz=168、Wineはdx=0.05 cm。AUTOFISHとSF7を全4モードで実行した。
比較用AF/SEGは同じNG輪郭から生成し、SF7は全104.970 mmの符号付き軸場を800区間で取得した。
振幅はU=1 Jへ合わせた。生出力は `out/seminar-flat-wine-probe-20260905/mode1`〜`mode4`。
NG結果は `out/seminar-flat-probe-20260905`、図は `out/seminar-flat-probe-20260905-mode4.png`。

| 周波数順位 | NG [MHz] | Wine [MHz] | 相対周波数差 | 軸場L2差 | 相対R/Q差 |
|---|---:|---:|---:|---:|---:|
| 1 | 2835.947560 | 2835.696540 | 0.00885% | 0.2930% | **1.0991%** |
| 2 | 2843.500002 | 2843.201250 | 0.01051% | 0.3849% | 0.02959% |
| 3 | 2858.555992 | 2858.162520 | 0.01377% | 0.3932% | 0.05832% |
| 4 | 2866.059780 | 2865.619020 | 0.01538% | 0.3600% | 0.06598% |

セル中心の符号と相対振幅は、順に約 `[1,1,1,1]`、`[1,.5,-.5,-1]`、
`[1,-.5,-.5,1]`、`[-1,1,-1,1]` で、対象の4位相モードとの対応が見られる。
現段階では自動同定ゲートではなく確認用記録であり、mode番号そのものを物理ラベルとして定義しない。

探索的なNG細分（nr=32/64/128、nz=84/168/336）は
`out/seminar-flat-refinement-probe-20260905` に保存した。
最低モードのWine R/Qは約0.040855 Ω、TTFは約0.00707と小さく、相殺の影響が大きい。
nr=128では軸場差が0.1225%へ低下した一方、R/Q差は1.6244%で相対受入目標を超えている。
粗い段階では約19%の差もあり、単一メッシュで合格とはしない。
Wine側も細分して周波数・RF量・場の収束を確認すること。誤差基準の緩和や数値補正は行っていない。

## 追加のメッシュ細分とモード同定

NGはnr=128/256/512、nz=336/672/1344まで細分した。最細は620,488節点。
最終2段階の全4モードの周波数・Q/G/RQ/P/TTF変化が従来の閾値以内になった。
最低モードのR/Qは0.0424236 Ω、最終変化は約0.702%。閾値を緩めず、実計算を細分した結果である。
Wineはdx=0.05/0.025/0.0125 cmを計算済みで、最細とのNG比較自体は全モード合格するが、
最低モードのWine側最終R/Q変化が約1.085%のため、全体はFAILと記録した。
この結果は `out/seminar-flat-comparison-20260905` に保持する。
さらにdx=0.01 cmを `out/seminar-flat-wine-dx001-20260905` で計算中。
完了済みの最低モードはf=2835.277280 MHz、R/Q=0.0423984 Ω、NGとの軸場L2差0.00513%。
残りの計算と最終レポート再生成を確認するまではWine照合完了としない。

`modes.identify_cell_band` はセル中心値のcosパターンとの重なりと軸上の零交差数を両方検査し、
割当てを一対一に決める。重なりの下限は0.98。列の順序・符号を入れ替えた7モードfixtureでも同定する。
これは対象のhalf-end-cellバンドの同定であり、任意の高次radialファミリーの分類器ではない。
分散はf=m1+m2 cosθを最小二乗フィットし、周波数と符号付き残差を別々に保存する。
残差はcosモデルからの差であり、ソルバーの固有値残差ではない。

```bash
python scripts/seminar_multicell.py --case flat4 --run-legacy --out out/flat-exercise-new
python scripts/seminar_multicell.py --case rounded4 --out out/rounded4-new
python scripts/seminar_multicell.py --case rounded7 --out out/rounded7-new
```

各コマンドは全モード図、軸上/半径方向CSV、分散曲線と残差、比較JSON、モード選択HTMLを生成する。
既定のNGメッシュはflat4が128/256/512、rounded4/7が32/64/128。
`--levels`、`--wine-dx`、`--wine-timeout-s` で検証設定を明示できる。
`--native-runs` は既存計算の再利用を明記し、入力・case hash・保存場と軸CSVの一致を検査する。
`--reference-dirs` はWineのAF/SEGを再生成した入力と全バイト比較し、生SFO/SF7を読む。
全ファイルhashを記録する。実行中にソースが変わった場合はPASSにしない。

## 円弧を保持した4セル・7セル

`examples/seminar_4cell_rounded.json` と `seminar_7cell_rounded.json` は元入力の円弧半径3 mm、
端点、反時計回りの指定を保持する。v2のarc_profileは円弧を指定した最大弦誤差で直線近似してメッシュへ渡す。
単純な短円弧の中心と角度から独立に生成し、z逆行・軸への交差・不可能な半径を拒否する。
元の円弧パラメーターをcaseに残し、出力には近似方法・最大弦誤差・近接座標の丸め許容幅を記録する。

既存のrounded4 `OUTAUT.TXT` の最初の円弧の境界8点について、指定中心からの半径差は
最大3.73e-11 mであり、出力座標の印字精度内で同じ円を確認した。
提供寸法の円弧と直線の接続は完全な接線連続ではない。見た目を滑らかにする補正を加えず、表面ピークの収束も保証しない。

円弧の最大弦誤差3 µmを固定し、rounded4のnr=32/64/128の全モードで最終メッシュ変化が合格した。
`out/seminar-rounded4-native-20260905/index.html` に保存した。これはまだWine比較なしの結果である。

| 位相 | rounded4 NG [MHz] | R/Q [Ω] |
|---|---:|---:|
| 0 | 2837.245886 | 0.034705 |
| π/3 | 2843.829867 | 248.660520 |
| 2π/3 | 2856.959744 | 242.454681 |
| π | 2863.505719 | 66.011701 |

## FEM分割と円弧近似の検査を分ける

```bash
python scripts/seminar_geometry.py --case rounded4 --out out/geometry4-new
python scripts/seminar_geometry.py --case rounded7 --out out/geometry7-new
```

固定のnr/nzに対して最大弦誤差12/3/0.75 µmを変える。境界の点数と総自由度も変わるため、
完全にFEM誤差を取り除いた「純粋な形状誤差」とは呼ばない。FEM分割数を変える試験とは別の入力制御で評価する。
円弧部分の正確な断面積は、弦の多角形面積から符号付き円弧部分の面積を加減して計算する。
rounded4では断面積誤差が1.53e-7→3.83e-8→9.58e-9 m²へ減少し、
最終の周波数・RF量変化も合格した（`out/seminar-rounded4-geometry-20260905`）。

rounded7も全7モードを同定し、図・分散曲線を `out/seminar-rounded7-native-20260905` に保存した。
ただしnr=64→128のπモードR/Q変化は9.53%、π/3モードは1.46%で、数値ゲートはFAIL。
形状近似3→0.75 µmのπモードR/Q変化も1.19%で、`out/seminar-rounded7-geometry-20260905` はFAIL。
πモードのR/Qは約0.009 Ωで相殺に敏感である。追加細分や幾何の厳密な対称性を利用した計算を検討し、
基準を満たすまで合格にはしない。

56件のunittestと `out/validation-multicell-foundations-20260905` が合格。
Pillbox・rounded4・rounded7の生成HTMLはheadlessブラウザーの実キーボード入力で検証した。
詳細は [BROWSER_VERIFICATION.md](BROWSER_VERIFICATION.md)。UIのPASSと数値のPASSは独立に保持する。

端部比較を実装する際は本文p.28の赤い切断面を確認すること。
full-cell側の図はiris中心、half-cell側は空洞中心で切っている。
単に端の大半径ギャップだけを延長したモデルと同一視しない。
同じ周期34.99 mmを保つfull-cell版なら端にhalf-diskを残し、4セル全長は139.96 mmになる。
この切断面で `examples/seminar_4cell_flat_full_ends.json` と `seminar_4cell_rounded_full_ends.json` を作成し、
`scripts/seminar_end_cells.py` で同じ円弧・周期・孔を持つhalf/full各4モードを計算・可視化した。
断面積が元のhalf-end型の4/3、端面半径がiris最小半径、形状が鏡映対称であることをテストする。
full-end側には半セル用cos位相を流用せず、実際の零交差0〜3個で並べる。同じ零交差数でも同じ位相進みとは主張しない。
比較グラフだけz/L・最大振幅で揃え、元のSI軸場CSVとU=1 Jの場を別途保持する。

初回 `out/seminar-end-cells-20260905` はflat/halfの最低モードR/Q細分変化1.1521%だけがFAIL。
full側の全モードとrounded両端形状は合格。flat/halfに追加nr=384を実行し、R/Qは
nr=256の0.0422991543から0.0424360874 Ωへ変化（0.32373%）。追加段階を明示した
`out/seminar-end-cells-ready-20260905/index.html` は全検査PASS、実行中ソース変更なし。
全8選択肢・51リンク/画像を `out/gallery-test-end-cells-ready-20260905` でheadless検証した。

円弧形状の零交差3個のモードでは、セル中心振幅（最大絶対値で正規化）が
half端部 `[1,-1,1,-1]` に対してfull端部 `[0.414213,-1,1,-0.414213]` になり、
端の場が内側より弱くなる違いを図と保存場で確認した。対応する周波数はそれぞれ2863.447213 MHzと2859.617541 MHz。
full側をhalf側のπモードと同じ位相として比較した値ではない。零交差0個のモードでは両形状のセル振幅はほぼ一定であり、
「full端部ならすべてのモードが同じように歪む」とは結論しない。

```bash
python scripts/seminar_end_cells.py --flat-half-extra-n 384 --out out/end-cells-new
```

既定nr=64/128/256にflat/halfだけ384を追加する。既存場を使う場合のみ `--native-roots` を明示し、
一致するcase・hash・保存場を検査して再利用を記録する。全例題一括回帰ではこのオプションを使わず新規に解く。

交差分割・端部比較の変更後は63件のunittestと `out/validation-crossed-ends-20260905` が合格。
seedのPillbox/合成空洞の周波数・Q0・R/Qとの差は最大9.55e-15で、丸め誤差内。全Pythonソースは3.10文法検査も合格した。
