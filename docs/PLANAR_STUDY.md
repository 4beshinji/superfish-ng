# 平面RFの独立パラメータ掃引

専用PlanarStudy、実worker、全点保存/再検証、CLIと平面GUIを接続した。独立物理・操作・保存再起動・標準/既存数値回帰まで確認し、以下の範囲で限定受入。[Study・収束・追跡の受入計画](PLANAR_STUDY_PLAN.md)。独立掃引と、未実装の収束診断・追跡を区別する。

## 入力と操作

```
python -m superfish_ng execute-planar-study examples/planar/study_rectangle_width.json --out out/my-width-study
python -m superfish_ng execute-planar-study examples/planar/study_triangle_scale.json --out out/my-scale-study
python -m superfish_ng replay-planar-study out/my-width-study
```

APIは `PlanarStudy(project, parameter, values)`、`execute_planar_study(study, directory)`、`read_planar_study(directory)`（superfish_ng.planar_study_jobs）。`JobManager.start_planar_study(study)` は別プロセスで実行する。CLI出力先は新規ディレクトリだけを許可する。同梱例は粗い操作例であり、メッシュ精度の保証はない。

JSONはformat=superfish_ng_planar_study、study_version=1、kind=sweep、project、parameter、valuesの六フィールドを全て要求する。projectは専用PlanarProject、valuesは2点以上の有限正数。未知キー、真偽値・非数値、不正な後続点、未対応kindを拒否する。全点のProject・物理・元メッシュを実行と出力作成前に検証する。valuesの順序を保持し、各点は元Projectから独立に生成する。

| parameter | 値の意味 | 対象 |
|---|---|---|
| uniform_scale | 元の全xy座標を原点から倍率変換。無次元 | 矩形・明示多角形 |
| /case/geometry/width_m | 幅 [m] | 矩形だけ |
| /case/geometry/height_m | 高さ [m] | 矩形だけ |
| /case/rf/stored_energy_j_per_m | U′ [J/m] | 両Case |
| /case/rf/conductivity_s_per_m | 壁導電率 [S/m] | 両Case |

一様尺度では多角形の宣言境界と全節点を同じ倍率で変換し、接続と節点番号を保持する。多角形の部分座標だけを変更する変数や、無宣言の変形・メッシュ操作は拒否する。表示単位m/mmは入力文書に保持し、パラメータのSI値と混同しない。

平面GUIの「独立パラメータ掃引」で現在のProjectと変数・値配列を指定し、Study保存/読込、実行、中止、履歴から復元を行う。結果は点ごとに順位・f・U′・P′・Q0・G・両R/QのN/Aを表示する。「結果を取り込む」は元の保存係数とメッシュを別の平面結果履歴へ取り込み、描画・プローブ・新規再実行へ接続する。取込で新しい場を生成せず、正スペクトル再計算は検証のために行う。Study結果は軸対称追跡の候補に混入させない。

## 保存と完了契約

親kindはplanar_study。study.json、study-results.json、job.json、manifest.jsonとpoint-0000等の各点を保存する。各点は専用PlanarProject・planar_solveの完了状態/manifest・五nativeファイルを持つ実計算。親manifestは入力/要約と全点の八ファイルを過不足なく列挙し、点のProjectを指定値から再生成して照合する。各点の実装hashは親と一致し、取込を新規掃引計算と見なさない。

再生は全nativeの正スペクトル・係数・規格化・RFを完全再検証し、点の順序・値・相対パス・要約と再結合する。hashを書き換えたRFやProjectの改変、真偽値へのindex改変、kindだけの削除/変更、未知要約キー、不足/余分な点、リンク、読込中の変更を拒否する。既存軸対称Studyの書式/全長RFは流用しない。

投入時の正規化済み入力バイト列をqueued hashへ保持し、workerはqueued状態と排他的claimを要求する。入力/実装の変化を実行前後と完了検証後に照合する。二重投入・完了ディレクトリへの再投入を拒否し、元結果を保持する。失敗・中止を親completeとしない。中止時の途中点が残ってもStudy全体の完了とは扱わない。再起動後も完成した保存点を再検証できる。

結果・状態はmode_tracking=not_performed、numerical_validation=not_checkedを維持する。順位は各点の正スペクトルの順序であり、隣接点の同じ順位を物理モードIDへ読み替えない。正方形の縮退や幅掃引の交差で個別同定を宣言しない。

## 検証経過

- 前工程中の隔離入力候補と順位交差3FEMはPLANAR_STUDY_PLAN.mdに記録。主ツリーへ接続後、新8unitが2.756秒でPASS。全点/strict文書・元メッシュ、尺度則、再hash改変/種別逃避、queued入力変更/再投入/完了中変更、保存失敗、実中止・再起動・点取込、CLI再生を確認。物理式・許容差は不変。
- GUI4unit（既存3＋新1）が3.567秒でPASS。Studyの正規化・実worker・全体結果・strict点番号・元バイト列取込を確認。平面関連58検査もPASS。
- out/planar-study-independent-20260910は34.995秒で終了0。P1/P2・TE/TM・矩形/多角形の参照8FEM＋24実workerの48点、計56実FEMで尺度/規格化/導電率則を確認。f最大相対差7.328e-15、全場2.371e-11、RF7.994e-15。G/Q、U′/P′、Rsと両R/Q N/Aを別に照合した。これらは相似・比例則の確認で、粗分割の絶対精度保証ではない。
- out/planar-study-crossing-final-20260910は5.155秒で終了0。CLIのP2 n24・幅0.18/0.20/0.22 mの実3点と独立cos場/面積内積を照合。解析f最大相対差1.408e-6、両側でcos x/cos yの順位逆転、正方形の二次元縮退部分空間を確認した。結果は追跡未実施を保持。同梱2Studyも実CLI5点と再生を確認した。
- out/browser-planar-study-20260910はChrome8操作PASS・外部HTTP0・src hash不変。矩形幅/多角形尺度、Studyファイル往復、点取込/場画像、未対応収束入力時の現入力保持、query URL復元、実中止、軸対称追跡除外を確認。study-results.pngを目視し、単位長RF・順位・N/A・追跡未実施表示を確認した。
- out/planar-study-gui-independent-20260910でブラウザー全5点を独立参照FEMと全係数/結果照合し、HTTP結果・取込元native・認証/未知キー/点番号拒否がPASS。既存平面GUI13操作と軸対称GUI10操作もPASS。

標準out/validation-planar-study-final-20260910は865件（863合格、2skip、unittest1238.644秒）で終了0。旧平面32件・TE10件のnative再生はout/planar-study-native-regression-final-20260910でPASS。再起動後Chromeはout/browser-planar-study-restarted-20260910で2Studyの復元・点取込/描画がPASS。サーバーは正常終了し、out/planar-study-restart-20260910で29Study/61点とGUI取込4件の保存hash・完全再生がPASS。TM seed9モード19量f差0/RF最大8.882e-16と505source、29Study/61点・GUI取込4件のhashを最終照合してPASS。標準ディレクトリにverify_completion.py/seed_regression.jsonを保持。全関連実行と専用GUIサーバーは終了済み。既存.manager.lockのResourceWarningは原因未確定のまま残る。平面の収束診断・追跡、親P02と全計画は未完。

[後続の同形状細分診断](PLANAR_CONVERGENCE_PLAN.md)は幾何/移送の候補段階であり、この独立掃引の対応に含めない。

追跡候補除外の追加確認out/browser-planar-study-filter-20260910では、以前/現在の両selectに実際の軸対称TM/TE/曲線TEの3結果が存在し、二つの平面Studyと取込点が含まれないことを確認した。空の候補一覧だけを見た除外判定にしない。Chrome2確認PASS・src不変・外部HTTP0、一時GUIも正常終了済み。
