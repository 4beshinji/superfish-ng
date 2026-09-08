# ローカルCodexへの引継ぎ

## D01 GUI対応比較・追跡履歴 — 2026-09-08

直前基準abf856f。gui_mode_tracking.pyで完了個別Jobの選択と既存native追跡/再検証APIを接続。
GUIに写像・閾値・ID入力、個別/部分空間の対応表、未確認理由、履歴開始/継続、保存/再読込を追加。
履歴中は手入力IDを使わず基準結果を表示し、UNVERIFIED履歴の継続を無効化する。
サーバー生成の文書文字列をダウンロード・再送し、数値表記を保持する。
GUIの既存loopback/token/4 MiB上限と厳密入力を維持。FEM・追跡の数値条件は変更していない。

着手前455件中453合格・2 skip（128.376秒）。新接続API未実装で失敗を確認して接続4検査を追加。
初回Chromeは7操作後、minimum_overlap=1の未確認文書をJavaScriptで再JSON化して1.0→1となり、
履歴開始の厳密再検証で失敗。out/browser-d01-mode-tracking-20260908/report.jsonと初回検証出力を保持。
サーバー文書文字列をそのまま開始/継続へ渡す修正と回帰1検査を追加。検証条件を緩めていない。
ID欄の幅と、履歴中の基準結果表示も修正した。
最終460件中458合格・2 skip（128.587秒）、`out/validation-d01-gui-tracking-final-20260908` PASS。
seed周波数差0、RF/エネルギー相対差最大8.881784197001248e-16。
同ディレクトリseed_comparison.jsonに内訳。基準値・許容差の変更なし。

`out/d01-gui-tracking-final-sources-20260908` の実FEM縮退合流/分裂もPASS。
`out/browser-d01-mode-tracking-final-20260908/report.json` でChrome8操作PASS、外部要求0。
取込/結果選択、合流の部分空間表示、履歴ID編集禁止、分裂継続、ダウンロード一致、
ファイル再検証とcontrols復元、改変拒否、未確認履歴の保存可能/継続禁止を実操作で確認。
tracking-history.pngを視認し、部分空間未確定表示とボタン状態を確認。
標準・独立FEM・ブラウザーのsource hashは最終コードと一致。検証用GUI2プロセスは停止した。
今回ブラウザー例は円筒写像。profile/paired_meshのGUI選択は共通API接続であり、各写像の新しいブラウザー受入ではない。
Wine・hosted CIは今回未実行。

判断: GUI独自のID推測や数値再計算を作らず、保存場APIの確定/未確認状態を製品操作へ伝える。
新規外部資料・依存・legacy参照なし。多対多再構成、個別枝回復、接続の変わる再メッシュ写像、
適応的ステップとStudy/tune統合は残件。親課題は8受入、C00/G03/D01の3進行中、
他21未受入、X01拡張候補1で変わらず。全計画は未完了。[仕様](MODE_TRACKING.md)。


## D01合流/分裂をID集合として継続 — 2026-09-08

直前基準826c647。明示controls cluster_transition_policy=retain_subspace とminimum_cluster_linkを追加。
基底不変の部分空間投影量から二部グラフを作り、多対一/一対多・合計次元保存の場合だけ
集合候補を作る。再直交化後に既存の最悪主角・ランク・割当分離を全て再検査する。
単一モード同士の曖昧な回転、多対多、方向喪失をまとめて合格にしない。
分裂後もID集合を保持して個別周波数を拒否する。集合順位は非連続にも対応し、昇順/一意/全分割を維持。
元クラスタ・リンク行列・MERGE/SPLIT候補と判定を保存/履歴へ接続した。
既存policy未指定requestの計算結果・停止意味は維持する。

着手前449件中447合格・2 skip（128.470秒）。新controls未実装で追加6検査の失敗を確認した。
解析基底回転での合流、非連続分裂/継承、曖昧混合、方向喪失/ランク不足、厳密controls、
実FEM縮退の保存再開/改変拒否を追加してPASS。既存部分空間5検査もPASS。
最終455件中453合格・2 skip（128.737秒）、`out/validation-d01-cluster-transitions-20260908` PASS。
seed周波数差0、RF/エネルギー相対差最大8.881784197001248e-16。
同ディレクトリseed_comparison.jsonに内訳。FEM・基準値・許容差を変更していない。

`python scripts/validate_cluster_transitions.py --out out/d01-cluster-transitions-20260908` PASS。
R=0.1 m、L=0.055→0.06322753439669529→0.075 mをP2/12×12/3モードの実FEMで解いた。
中央LはBessel零点から独立に求めたTM020/TM011縮退位置。解析周波数相対誤差は最大5.6130317729330415e-6、
中央の数値周波数相対gapは1.0283783478115538e-6で、明示クラスタgap1e-3内。
標本次数12/18の両方でMERGE/SPLIT候補がPASS。最終最悪主角は0.9999999999890008 / 0.9999999999872012。
最終TM010だけ個別ID、TM011/TM020は集合として保持。個別枝を回復したとは扱わない。
同出力history-c-12.jsonをCLI再検証PASS。以前のout/d01-subspace-history-second-20260908.jsonもPASS。
標準/独立検証のsource hashは最終コードと一致。GUI・Wine・hosted CIは今回未実行。

判断: 次元保存と全方向の重なりが確認できた集合だけを継続し、個別IDを捏造しない。
公開された数値コード等は参照せず、射影の基底不変性と円筒分離解から独立実装。新規外部資料・依存・legacy参照なし。
多対多の再構成、分裂後の個別枝回復、接続が変わる再メッシュの写像、適応的ステップ、GUI/Study/tuneが残る。
親課題は8受入、C00/G03/D01の3進行中、他21未受入、X01拡張候補1で変わらず。
全計画は未完了。[仕様と再現](MODE_TRACKING.md)。


## D01明示メッシュ対応による折返し/曲線場の追跡 — 2026-09-08

直前基準3e0d6a3。`paired_mesh_tracking.track_paired_mesh_modes` と保存/履歴/CLIへ
mapping=paired_meshを追加。controls.vertex_pairsで全幾何頂点の0始まり全単射を必須指定する。
三角形接続と軸/PEC境界を保存する対応だけを受け付け、番号の一致から対応を推測しない。
三角形重心座標を局所頂点対応で並べ替え、直線/二次幾何とP1/P2係数から直接場を評価する。
体積要素2π r detJから、Hphiに正規化したsqrt(r detJ)を掛けて共通参照積分で比較する。
曲線を弦へ置換せず、実二次Jacobianを使用。次数2〜32、総標本262144以下。

着手前444件中442合格・2 skip（127.977秒）。新API未実装を確認後、5検査を追加。
初回FEM fixtureはgeometry_orderをsolverに置いたため厳密入力で失敗し、正しいmesh項目へ修正。
変動曲線Jacobianの独立積分、全単射/境界/接続/予算、折返し相似と番号置換、
native曲線相似、保存履歴がPASS。
最終449件中447合格・2 skip（128.227秒）、`out/validation-d01-paired-mesh-20260908` PASS。
seed周波数差0、RF/エネルギー相対差最大8.881784197001248e-16。
同ディレクトリseed_comparison.jsonに内訳。FEM・基準値・許容差を変更していない。

`python scripts/validate_paired_mesh_tracking.py --out out/d01-paired-mesh-20260908` PASS。
合成折返し/楕円曲線のP2 FEM、2倍相似、頂点逆順・要素逆順・局所巡回置換を明示対応で比較した。
相似則の相対差（f/RQ/G）は、折返し7.438494264988549e-15 / 1.4210854715202004e-14 / 9.2148511043888e-15、
楕円2.220446049250313e-16 / 3.375077994860476e-14 / 2.55351295663786e-15。
両形状とも次数3/5の最小主角重なりは丸め上1.0。同じID対応と保存後の履歴往復を確認。
同出力のfolded-requestから `out/d01-paired-mesh-cli-20260908.json` をCLI保存/再検証PASS。
ellipse-history.jsonもCLI再検証PASS。標準/独立検証のsource hashは最終コードと一致。
GUI・Wine・hosted CIは今回未実行。

判断: 一般輪郭で番号だけを一致とみなさず、明示的な位相対応と体積整合を契約にする。
変数変換から独立導出し、新規外部資料・依存・legacy参照なし。
接続が変わる再メッシュ間の写像、合流/分裂解決、適応的ステップ、GUI/Study/tuneが残る。
親課題は8受入、C00/G03/D01の3進行中、他21未受入、X01拡張候補1で変わらず。
全計画は未完了。[仕様と操作](MODE_TRACKING.md)。


## D01半径可変profileの体積整合写像 — 2026-09-08

直前基準fd1d4ed。`profile_mode_tracking.track_profile_modes` と保存/履歴/CLIへ
mapping=normalized_profileを追加。正の連続折れ線半径と両端PECだけに限定する。
r=rho R(L zeta), z=L zetaの体積要素2π L R² rhoから、標本をHphi*R/Rmaxとした。
定数2π L Rmax²だけを正規化で除き、変動する体積要素を保持する。
両形状の正規化節点の和集合で積分区間を分け、写像・倍率・点・重みを記録する。
総標本262144上限、未対応形状/対称端・参照節点の潰れ等を明示拒否。
従来normalized_cylinderの計算/保存意味は維持する。FEM自体の変更なし。

着手前438件中436合格・2 skip（127.238秒）。新API未実装を確認して追加6検査を実装。
初回2件はCaseを含まない生Solutionをテストから渡したため失敗し、契約どおり保存解を再読込して修正。
独立多項式体積積分、節点不変性、未対応入力、実FEM相似則/標本次数、保存履歴、円筒極限がPASS。
最終444件中442合格・2 skip（128.693秒）、`out/validation-d01-profile-tracking-20260908` PASS。
seed周波数差0、RF/エネルギー相対差最大8.881784197001248e-16。
同ディレクトリseed_comparison.jsonに内訳。基準値・許容差を変更していない。

`python scripts/validate_profile_tracking.py --out out/d01-profile-tracking-20260908` PASS。
合成profile、P2、12×20、3モードの2倍相似で、相対差はf:9.103828801926284e-15、
R/Q:4.007905118896815e-14、G:7.327471962526033e-15。
局所半径1%変更の最小主角重なりは次数8:0.9999457659745057、次数12:0.9999457604718266。
両方で同じID対応を得て、保存後の履歴再開もPASS。点間の連続物理枝の証明ではない。
同出力pair/historyをCLI再検証し、requestから `out/d01-profile-tracking-cli-20260908.json` を
CLI新規保存/再検証してPASS。標準/独立検証のsource hashは最終コードと一致。
GUI・Wine・hosted CIは今回未実行。

判断: 円筒の定数Jacobianを半径可変形状へそのまま流用せず、体積整合の明示写像を追加。
数式は変数変換から独立導出し、新規外部資料・依存・legacy参照なし。
折返し・曲線等の一般写像、合流/分裂解決、適応的ステップ、GUI/Study/tuneは残件。
親課題は8受入、C00/G03/D01の3進行中、他21未受入、X01拡張候補1で変わらず。
全計画は未完了。[仕様と再現](MODE_TRACKING.md)。


## D01部分空間ID集合の履歴継承 — 2026-09-08

直前基準14438fa。標本追跡にprevious_identity_groupsを追加し、現在順位集合とID集合を
個別基底への仮割当なしで次段階へ継承する。全順位の分割、ID一意性、次元、連続順位を厳密検査。
旧集合を保持して新周波数クラスタと比較し、閾値変更で旧集合を勝手に再分割しない。
合流/分裂は未確認。個別周波数の受渡しは多次元集合内で引き続き拒否する。
2時点request第2版はprevious_groupsを使用。履歴第2版はcurrent_identity_groupsと
individual_ids_completeを保存し、部分空間対応PASSなら集合として再開する。
第1版は元の停止意味を含め再検証互換。旧停止文書を自動でPASSへ変更しない。

着手前433件中431合格・2 skip（127.209秒）。未実装で新しい5テストの失敗を確認した。
3時点の独立直交基底回転/順位交差、分裂、厳密分割、native保存場履歴/改変拒否、旧停止互換を追加。
既存履歴2検査は第2版の集合継承契約に更新し、個別ID不確定を確認し続ける。
最終438件中436合格・2 skip（127.959秒）、`out/validation-d01-subspace-history-20260908` PASS。
seed周波数差0、RF/エネルギー相対差最大8.881784197001248e-16。
内訳は同ディレクトリseed_comparison.json。FEM・基準値・許容差の変更なし。

`out/d01-subspace-history-sources-20260908` の独立円筒交差PASS。
長さ0.055/0.075/0.08 m、半径0.1 m、P2、12×12、3モードの保存場で、
gap=.9を明示して3モードを一つの集合にまとめ、CLI履歴を作成/延長/再検証した。
`out/d01-subspace-history-first-20260908.json` とsecond版を新規保存、PASS。
最終ID集合はTM010/TM011/TM020、個別IDは全null、individual_ids_complete=false。
これは広い周波数集合の保存検証であり、実FEMの3モードが縮退しているという主張ではない。
前回保存の `out/d01-history-second-20260908.json` （第1版）もCLI再検証PASS。
標準/独立検証のsource hashは最終コード一致。GUI・Wine・hosted CIは今回未実行。

判断: 基底のラベルを捏造せず、集合の同一性を履歴へ渡す。一般写像、合流/分裂の追跡解決、
適応的ステップ制御、GUI/Study/tuneが残る。新規外部資料・依存・legacy参照なし。
親課題は8受入、C00/G03/D01の3進行中、他21未受入、X01拡張候補1で変わらず。
全計画は未完了。[仕様](MODE_TRACKING.md)。


## D01順序付き履歴・個別ID再開 — 2026-09-08

直前基準3d4401b。`mode_tracking_history.py` とstart/extend/replay-mode-history CLIを追加。
確認済みの2時点文書から開始し、全段階の元保存場を再検証して、隣接source/hashとID継承を確認する。
延長requestはcurrent_run/controlsだけを受け付け、以前のcurrent_mode_idsを自動継承する。
元履歴を変更せず、新規出力へ保存する。過去入力の変更や、単独では有効でも接続しない対応を拒否する。
UNVERIFIED段階も保存するが、その後の延長は停止する。部分空間対応がPASSでも個別ID不確定なら
履歴はUNVERIFIEDとし、基底への恣意的ID付与を避ける。全元入力と数値環境が再検証に必要。

着手前427件中425合格・2 skip（127.254秒）。新API未実装時の失敗を確認後、追加6件PASS。
実FEM3時点交差/保存再開、未確認保存/停止、部分空間停止、段階間不連続、過去入力変更、CLIを検証。
最終433件中431合格・2 skip（127.204秒）、`out/validation-d01-history-20260908` PASS。
seed周波数差0、RF/エネルギー相対差最大8.881784197001248e-16。
内訳は同ディレクトリseed_comparison.json。FEM・基準値・許容差を変更していない。

`out/d01-history-sources-20260908` の独立円筒交差PASS。
半径0.1 m、長さ0.055/0.075/0.08 m、P2、12×12、3モードの保存場を使用。
CLIで `out/d01-history-first-20260908.json` を作り、延長requestから
`out/d01-history-second-20260908.json` へ保存、再検証もPASS。
最後のIDはTM010/TM011/TM020で、交差後のIDを次段階へ継承した。
標準検証・独立交差のsource hashは最終コードと一致。GUI・Wine・hosted CIは今回未実行。

判断: 離散段階の履歴と再開を実装し、標本間の連続物理枝の証明とは区別する。
一般写像、部分空間ID集合の多段階継承、合流/分裂、適応的ステップ、GUI/Study/tuneは残件。
失敗からは最後の確認済み履歴を使って別出力へ分岐できるが、自動分岐管理は未実装。
新規外部資料・依存・legacy参照なし。親課題は8受入、C00/G03/D01の3進行中、
他21未受入、X01拡張候補1で変わらず、全計画は未完了。[仕様と操作](MODE_TRACKING.md)。


## D01の2時点対応保存・再検証CLI — 2026-09-08

直前基準a26280d。独立FEM場の対応核を `saved_mode_tracking.py` とCLIへ接続した。
厳密request版1、request所在からの相対入力解決、元保存場の主要ファイルと完了markerのSHA256、
比較前後の同一性検査、絶対入力パス、controls/重み/ID対応を保存する。
再読込は元native保存の整合性検査と場比較を再実行し、文書全体を照合する。固有値問題は再計算しない。
入力変更・対応改変を拒否し、UNVERIFIEDも理由付きで保存/再検証する。既存出力は上書きしない。
元入力のパスとバイト同一性が必要で、移動後の透過的再開・署名・連続履歴の保証ではない。

着手前421件中419合格・2 skip（125.977秒）。追加6件は実FEM交差の往復、改変、
比較中の変更、バイト同一性、UNVERIFIED、CLI/厳密requestを検証。
最終427件中425合格・2 skip（126.690秒）、
`out/validation-d01-saved-tracking-20260908` PASS。
seedの周波数差0、RF/エネルギー相対差最大8.881784197001248e-16。
比較内訳は同ディレクトリseed_comparison.json。基準値・許容差・FEMは変更していない。

`out/d01-saved-tracking-sources-20260908` の独立実FEM円筒交差PASS。
`out/d01-saved-tracking-request-20260908.json` からCLIで
`out/d01-saved-tracking-20260908.json` を新規保存し、再検証もPASS。
周波数順位の入替え後もTM010/TM011/TM020の対応を確認した。
両検証のsource hashは最終コードと一致。今回GUI・Wine・hosted CIは実行していない。

判断: 2時点の保存とCLIを先に具体化し、連続履歴や一般写像の完成とは区別する。
新規外部資料・依存・legacy参照なし。一般形状写像、クラスタ合流/分裂、
多段階履歴/安定ID再開、GUI/Study/tuneは残件。親課題の受入件数は8、
進行中C00/G03/D01が3、他21未受入、X01拡張候補1で変わらず、全計画は未完了。
詳細と再現用requestは[モード追跡](MODE_TRACKING.md)。


## D01標本部分空間追跡と明示円筒写像 — 2026-09-08

G03の残件を保持し、計画上独立に着手可能なD01を開始した。
mode_tracking.pyは共通標本の実場/正重み/写像説明を要求し、周波数クラスタごとに
重み付きSVD直交基底を作る。最悪主角の重なりと行/列の競合差から等次元クラスタを対応付ける。
以前のIDを継承し、mode_indexは周波数順位のまま。多次元は部分空間だけを識別し個別IDを付けない。
曖昧・欠落/追加・ランク不足・合流/分裂を未確認で残す。
tracked_frequency_hzは追跡全体の未確認と部分空間内の個別周波数を拒否する。tune本体は未実装。

track_cylindrical_modesはmapping=normalized_cylinderを明示必須とし、一定半径profile・両端PECに制限。
保存後に読み直した実P1/P2場のHphiをr=R*rho,z=L*zetaへ写し、rho重みのGauss積則で比較する。
形状依存の定数Jacobianは正規化で消える。一般形状へこの写像を暗黙適用しない。
結果に比較点/重み/寸法/次数/場の規約を記録し、既存の場・RF・同形状比較は変更しない。

追加9テストは解析交差/近接、縮退基底回転、曖昧同点、欠落/ランク不足/合流、
重み/標本順/符号/極端振幅、厳密入力、部分空間の一方向喪失、保存後の実FEM円筒交差。
実装前ModuleNotFoundErrorを確認。変更前412件中410合格・2 skip（126.677秒）。
最終421件中419合格・2 skip（128.101秒）、out/validation-d01-mode-tracking-20260908 PASS。
同所seed_comparison.jsonでcase hash一致、周波数差0、RF/エネルギー差最大8.882e-16。
FEM本体/数値基準変更なし、検証中ソース変更なし、最終fingerprint一致。

scripts/validate_mode_tracking.pyの独立実行out/d01-cylinder-crossing-20260908/mode_tracking.json PASS。
R=0.1 m、L=0.055/0.075 mのP2円筒を12×12分割/3モードで実計算・保存・再読込した。
Bessel解析周波数で旧順位010/020/011、新順位010/011/020を確認し、最大相対周波数差5.600337e-6。
追跡は解析式でなく保存Hphiから行い、12×12と18×18標本で同じID対応を確認。
最小principal overlapはそれぞれ0.999999999965、0.999999999961。
両実行のソースhash一致。GUI/Wine新規実行なし。合成円筒であり測定構造ではない。

[追跡仕様](MODE_TRACKING.md)を追加し、README・対応表・計画・実装状況を同期。
重み付き内積・SVDの基底不変性と既存SciPy割当から独立実装。新規外部資料/コード/依存/旧資産参照なし。
D01は部分実装。一般写像・合流/分裂・連続履歴/安定ID保存・CLI/GUI/Study/tune統合は残件。
G03の一般弧端/重解・旧入力/物理収束も継続。8親課題の限定受入は維持し、
進行中はC00/G03/D01の3件、他21親課題未受入、X01は拡張候補。全計画目標は未完了。


## G03曲率・最小半径の極端な尺度への修正 — 2026-09-08

conics.pyの曲率/最小半径の積商を、frexpの仮数/二進指数で合成してldexpで戻す計算へ変更。
中間の三乗・積・比の範囲逸脱を避け、最終値が表現できない場合は明示ValueErrorとする。
曲率の分子に二進回転行列のdet、最小半径に一様回転尺度を含める。
点/接線/角度パラメータや有限弧候補の数値評価方法は変更していない。
これらの数値評価を、最小子午面半径制約の有理数区間証明としては使わない。

修正前に楕円軸(2s,s)、s=1e±200で、表現可能な最小半径s/2がNaNになることを確認。
双曲線軸(1e-300,1e-300)、u=460..461では半径infと曲率評価エラーを確認した。
追加4テストの修正前実行は2エラー/1失敗。修正後は4件と既存円錐曲線テストの計28件PASS。
双曲線は80桁Decimalの独立指数関数・平方根・曲率式で照合した。
初期subnormal fixtureはnp.float64を渡して厳密入力に拒否されたためbuiltin floatへ訂正。
製品の厳密型検査や許容差は緩めていない。

変更前408件中406合格・2 skip（124.645秒）。
最終412件中410合格・2 skip（127.394秒）、out/validation-g03-conic-scale-20260908 PASS。
同所seed_comparison.jsonでcase hash一致、周波数差0、RF/エネルギー差最大8.882e-16。
FEM本体・数値基準変更なし、検証中ソース変更なし、最終fingerprint一致。
scale_examples.jsonに再計算した極端尺度の入力/数値を保存。
双曲線の最小半径7.496180459261836e298 m、始点曲率1.334012708784858e-299 /mを確認した。
これをFEMの対応寸法範囲や任意の極端な軸比の精度保証へ拡張しない。

construction_replay.jsonで既存構築版1〜6と半径制約付き版6を再読込CASE_VALIDATED。
前回GUIからダウンロードした構築診断も再検証し、元Caseの合格を維持した。
GUI/Wineの新規実行なし。README・対応表・計画・実装状況・幾何仕様・G03照合表を同期。
初等積商の指数分離と既存の曲率式から独立修正し、新規外部資料/コード/依存/旧資産参照なし。
次は一般の弧端/重解と退化候補構築、旧入力/物理収束の残件。
8親課題の限定受入を維持し、G03全体と全計画目標は未完了。


## G03最小子午面曲率半径のCase制約 — 2026-09-08

meridional_radius.pyと任意geometry.minimum_meridional_radius_mを追加。
有限正数を要求し、未指定なら旧JSONのキー・Case hashを維持する。
PEC曲線内部の|k|を距離0の法線オフセット区間で囲み、全域|k|<=1/Rを検査する。
違反点の下界が1/Rを超えればFAIL、幅/級数/箱数予算不足はUNVERIFIED。両方をCaseで拒否。
PEC-PECは1e-8 radのG1数値検査も要求。軸/対称境界と周方向主曲率は対象外。
構築選択後の完成Case、保存再読込、鏡映、GUIでの形状保持へ接続した。
専用GUI入力欄はない。制約は解析曲線に対するもの。FEM精度や物理ピーク収束の保証ではない。

実装前のModuleNotFoundErrorを確認。追加6テストは円/直線・1 ULP差、楕円/双曲線極値と
有限弧/尺度/向き、予算不足、PEC角拒否/厳密入力/旧JSON、構築/GUI・実FEM不変/保存再読込、
両対称タグの鏡映後再検査。予算不足fixtureの初期要求3.9 mは実最小約3.870707 mを超え、
実装が正しくFAILを返した。要求を3.8 mへ修正し、1箱UNVERIFIED/既定予算PASSを確認。
製品の判定や許容差は緩めていない。
変更前402件中400合格・2 skip（121.781秒）。最終408件中406合格・2 skip（125.496秒）。
out/validation-g03-meridional-radius-20260908 PASS、seed_comparison.jsonでcase hash一致、
周波数差0、RF/エネルギー差最大8.882e-16。FEM本体/数値基準変更なし、最終source hash一致。
同所construction_replay.jsonで版1〜6の既存保存を再読込。radius_constraint.jsonに区間証拠を保存。

out/gui-meridional-radius-browser-20260908/report.jsonでChrome11操作PASS、外部要求0、
実行中ソース変更なし。保存された構築・適用・FEM計算で0.019 mの制約保持を確認。
tangent-construction.pngの表示も確認。検証GUIは停止済み。今回Wine新規実行なし。
例examples/construction/radius_constrained_fillet_request.jsonはR20 mmのフィレットへ下限19 mmを指定。
21 mm指定は違反として拒否し、半径は自動変更しない。
実CLIはout/g03-radius-constrained-construction-20260908.json、out/g03-radius-constrained-case-20260908.json、
out/g03-radius-constrained-solve-20260908。周波数1258432805.464176 Hz、R/Q(acc)=140.166774 ohm、
制約なしの同一形状と一致。合成形状であり測定空洞ではない。

[制約仕様](MERIDIONAL_RADIUS.md)を追加。README・対応表・計画・実装状況・G03照合表を同期。
既存区間曲率核から独立実装し、新規外部資料/コード/依存/旧資産参照なし。
次は一般の弧端/重解と退化候補構築、旧入力/物理収束の残件。
8親課題の限定受入を維持し、G03全体と全計画目標は未完了。


## G03構築診断の保存・CLI/GUI接続 — 2026-09-08

construction_diagnostics.pyを追加し、版5/6構築の実探索証明から区間・符号付き距離を
有理数で取り出して既存の特殊ケース診断へ渡す。延長線分も実際の探索区間を使う。
元構築全体・parameter_domain_box・診断を別の版1文書として保存する。
文書型はconstruction_offset_diagnosis。再読込は元構築と診断を再計算し全体照合する。
既存構築版1〜6の保存内容は変えない。診断CERTIFIEDとCASE_VALIDATEDは別判定。
通常交点の診断がUNVERIFIEDでも、認証候補/閉輪郭検査に合格したCaseを取り消さない。

GUIは診断/全領域分類の状態を別欄に表示し、「中心軌跡の診断を保存」で元構築ごと保存。
同じ構築ファイル入力で再検証して開ける。要求/候補の変更、改変拒否で診断保存も無効化。
CLI diagnose-constructionは保存構築または保存診断を受け、既存出力へは上書きしない。
診断用の要求から元の計算プロジェクトへ自動適用しない。

追加5テストは弧端接触の証明と未完成Caseの分離、明示延長の実探索範囲、通常合格と
特殊ケース未分類の両立、旧版維持、改変拒否、CLI保存再実行/上書き拒否。
実装前のModuleNotFoundErrorを確認。変更前397件中395合格・2 skip（121.122秒）。
最終402件中400合格・2 skip（121.903秒）、out/validation-g03-construction-diagnosis-20260908 PASS。
同所seed_comparison.jsonでcase hash一致、周波数差0、RF/エネルギー差最大8.882e-16。
FEM本体/数学分類核/許容差/数値基準変更なし。検証中ソース変更なし、最終fingerprint一致。
同所construction_replay.jsonに版1〜6の既存実保存ファイル再読込CASE_VALIDATEDを保存。

out/gui-construction-diagnosis-browser-20260908/report.jsonはChrome11操作PASS、外部要求0、
実行中ソース変更なし。元の8操作に診断表示/ダウンロード/再読込、診断改変拒否、
弧端接触を証明しても未確認構築の適用を許可しない3操作を追加した。
tangent-degenerate.pngで診断表示と適用不可を視認。元プロジェクト不変も確認。
ダウンロードした診断はPythonでも再読込し、診断UNVERIFIED/構築CASE_VALIDATEDを確認。
検証用GUIは停止済み。今回Wine新規実行なし。

例examples/construction/degenerate_fillet_request.jsonを実CLIで構築するとUNVERIFIED（exit 1）。
out/g03-degenerate-fillet-construction-20260908.jsonへ保存し、diagnose-constructionで
out/g03-construction-diagnosis-20260908.jsonへSINGLE_TANGENCY / finite_domain_complete=trueを保存。
診断はexit 0でも構築はUNVERIFIED、Caseなしのまま。例は未完成の編集/診断要求であり測定空洞ではない。

README・対応表・計画・実装状況・G03照合表・診断/GUI仕様を同期。
既存核の製品接続で、新規外部資料/コード/依存/旧資産参照なし。
次は一般の弧端/重解と退化候補構築、最小半径契約、旧入力/物理収束の残件。
8親課題の限定受入を維持し、G03全体と全計画目標は未完了。


## G03弧端・退化の厳密特殊ケース診断 — 2026-09-08

offset_degeneracies.pyとdiagnose-offsets CLIを追加。元パラメータが一致する円/楕円/双曲線の
オフセットについて、方向補正した距離を照合し、共通区間の無限対/共有端点を証明する。
この証拠を別パラメータの交差まで含む全解数へ拡張しない。
有理数で表せる円のオフセットと直線では、外接/内接/離隔、潰れ、平行重複を分類。
支持接点を元の有限範囲へ戻し、円弧は既存の区間所属検査を使う。
中心点の個数とパラメータ対の無限性、証明した事実とfinite_domain_completeを区別する。
一般二進回転/直線長の平方根を1や有理数近似へ置換しない。未対応/予算不足はUNVERIFIED。

追加9テストは独立円の外接/内接と1 ULP差、有限弧端点/外部/予算不足、潰れと無限対、
楕円/双曲線の共有区間/方向反転/共有端点、直線と円/平行直線、尺度/交換、
支持円一致と有限所属の区別、厳密入力とCLI保存再実行・未確認出力・上書き拒否。
実装前のModuleNotFoundErrorを確認。変更前388件中386合格・2 skip（121.553秒）。
最終397件中395合格・2 skip（121.847秒）、out/validation-g03-offset-degeneracy-20260908 PASS。
同所seed_comparison.jsonでcase hash一致、周波数差0、RF/エネルギー差最大8.882e-16。
FEM・許容差・数値基準変更なし。検証中の実装変更なし、最終source fingerprint一致。

例はexamples/construction/offset_tangency_diagnosis_request.json。弧の始点で接する円の中心軌跡を
out/g03-offset-tangency-diagnosis-20260908.jsonへ実CLI保存し、SINGLE_TANGENCY / 完全分類を確認。
診断要求版1は構築要求版1やCase版1とは別契約。出力にdocument_type・要求/hash・software版を保持する。
validation内diagnostic_examples.jsonに反転円オフセット、直線上への潰れ、共有端点の追加実行を保存。
同所construction_replay.jsonに版1〜6の実保存ファイル再読込CASE_VALIDATEDを保存した。
GUI新規実行なし、Wine新規実行なし。既存構築の候補/保存結果へ診断を暗黙に適用しない。

[診断仕様](OFFSET_DEGENERACIES.md)を追加し、README・対応表・計画・実装状況・G03照合表を同期。
既存区間演算と初等円幾何/線形代数から独立実装。新規外部資料/コード/依存/旧資産参照なし。
次は一般の弧端/重解、診断の構築/GUI接続、最小半径契約、旧入力と物理収束の残件。
8親課題の限定受入を維持し、G03全体と全計画目標は未完了。


## G03版6直線・有限弧フィレット — 2026-09-08

normal_offsets / offset_intersectionsを線分の支持直線へ拡張し、conic_filletと
構築schema_version=6で直線と有限弧の指定半径フィレットを保存/Case/CLI/GUIへ接続した。
二進端点の線分を有理数アフィン式で扱い、単位法線の平方根を外向き区間で囲む。
延長なしは[0,1]、明示allow_extension=trueでは有限弧の中心軌跡を線分方向へ射影して
必要な有限探索範囲を導く。弧は延長しない。配列順に線分の始点/終点を保持し、
空/逆向きになる保持線分を拒否する。生成接点/保持端/中心の位置上界を検査し、
元線分との方向差とG1角度は数値検査として区別する。

実装前には線分normal_offset_boundsのValueErrorとallow_extension未対応のTypeErrorを確認。
追加6テストは3-4-5線分法線区間、既知円/双曲線接点、明示延長と両順序、逆向き拒否、
保存/再構築/GUI・解析面積/体積、実曲線FEMの相似則。変更前382件中380合格・2 skip。
最終388件中386合格・2 skip（124.074秒）、out/validation-g03-line-conic-fillet-20260908 PASS。
同所seed_comparison.jsonでcase hash一致、周波数差0、RF/エネルギー差最大8.882e-16。
FEM本体・数値基準・許容差変更なし。検証中の実装変更なし、最終fingerprint一致。

out/gui-line-conic-fillet-browser-20260908/report.jsonはChrome8操作PASS、外部要求0、
実行中ソース変更なし。半径/回転方向/円弧長/接点上界、明示選択・ダウンロード・再構築・
適用・FEM/描画・改変拒否まで確認。tangent-construction.pngの表示も確認し、GUIは停止済み。
validation内construction_replay.jsonに版1〜6の実保存ファイルのCASE_VALIDATEDを保存した。

合成例はexamples/construction/line_conic_fillet_request.json。z=0.15 mの直線壁と
半径0.1 mの円弧を半径0.02 m、反時計回りの円弧で接続する。延長なし、二次幾何/二次場。
CLIはout/g03-line-conic-fillet-construction-20260908.json、out/g03-line-conic-fillet-case-20260908.json、
out/g03-line-conic-fillet-solve-20260908へ保存。周波数1258432805.464176 HzはGUIと一致し、
R/Q(acc)=140.166774 ohm。接点位置誤差上界最大2.568e-17 mで要求1e-12 m以内。
保持線分の方向差0、延長なし、端点内側調整なし。この形状のRF/物理ピーク収束は未検証。

既存の認証交点核・初等線形射影から独立実装。新規外部資料/コード/依存/旧資産参照なし。
Wine新規実行なし。README・対応表・計画・実装状況・G03照合表を同期。
次は弧端/退化の追加分類、輪郭全体の最小半径契約、旧入力と物理収束の残件。
8親課題の限定受入を維持する。G03全体と全計画目標は未完了。


## G03版5有限弧フィレット・保存/CLI/GUI統合 — 2026-09-08

conic_filletと構築schema_version=5を追加。両有限弧の中心軌跡に同じ符号付きRを使い、
根箱から元の接点を復元して元弧/指定半径円弧/元弧へ切り詰める。
半径・回転方向・最大円弧角を明示し、大回り上限超過や空/表現不能・未達は選択不可。
元弧端点/フィレット端点/保持外端/中心の誤差上界を確認し、G1角度は数値検査として区別。
float中点が根箱内にあるかも記録するが、接点一致の根拠にはせず位置上界で検査する。
版1〜4の経路を維持し、版5保存/再構築・Case/CLI/GUIまで接続した。

初回の合成Caseは隣接検査で約3e-17 mの丸め重なりを拒否した。
out/g03-conic-fillet-overlap-before-20260908.jsonへ元の要求/候補/拒否理由を保持。
検査は緩めず、必要時だけフィレット両端を明示位置/角度許容差内で内側へ取り、
中心/Rを保持して全上界・G1・進行方向分離を再検査する処理を追加した。
合成例の内側角は3.125e-12 rad、元弧接点上界約1.09e-15 m、フィレット約6.36e-14 m。
要求の1e-12 mより小さいことを確認。初期fixtureのjoin_toleranceは軸長制限より
大きかったため1e-12 mへ厳しくし、製品の制限・許容差は緩和していない。

追加6テストは既知円の接点/半径/小回り・大回り、楕円/双曲線四分円、
方向反転・厳密指定/未達、保存/GUIと解析面積/体積、二次曲線FEM相似則。
変更前376件中374合格・2 skip、最終382件中380合格・2 skip（119.905秒）。
out/validation-g03-conic-fillet-20260908 PASS。同所seed_comparison.jsonでcase hash一致、
周波数差0、RF/エネルギー差最大8.882e-16。FEM本体/数値基準変更なし。
検証中の実装変更なし。Wine新規実行なし。

out/gui-conic-fillet-browser-20260908/report.jsonのChrome8操作PASS、外部要求0、
実行中ソース変更なし。tangent-construction.pngの半径/時計回り/円弧長/接点上界表示を確認。
明示選択・保存ダウンロード・再構築・適用・曲線FEM/描画・改変拒否まで実操作済み。
検証用GUIは停止済み。validation内construction_replay.jsonには版1〜5の
実保存ファイル再読込をCASE_VALIDATEDで保持する。

例はexamples/construction/two_lobe_fillet_request.json。2円弧をR=0.02 mの時計回り円弧で
つなぐ合成2山形状で、geometry_order=2 / element_order=2を明示する。
実CLI記録はout/g03-conic-fillet-construction-20260908.json、out/g03-conic-fillet-case-20260908.json、
out/g03-conic-fillet-solve-20260908。周波数1310579815.6725943 Hz、R/Q(acc)=85.595228 ohm。
GUIと同じ周波数を確認。解析面積/体積と相似則を、この形状のRF/物理ピーク収束へ読み替えない。

既存の認証交点/端点区間核と初等円幾何から独立実装。新規外部資料/コード/依存/旧資産参照なし。
README・対応表・計画・実装状況・G03照合表を同期。
次は線分と弧のフィレット、弧端/退化の追加分類、旧入力と物理収束の残件。
8親課題の限定受入を維持し、G03全体・全計画目標は未完了。


## G03中心軌跡の有限領域交点探索 — 2026-09-08

offset_intersections.intersect_normal_offsetsを追加。符号付き法線距離を指定した
2円錐曲線の有限fraction領域で、F=C1−C2の孤立交点を探す。
有理数のKrawczyk内部包含と∞ノルム収縮上界<1で存在/一意性を確認し、
根のparameter_box・center_box・証明領域/行列/収縮上界を保持する。
座標包絡/Krawczyk箱が交わらない場合だけ除外し、包含で縮小して根を失わない。
認証後も指定fraction幅まで縮小する。96 bit既定の外向き二進格子で分母増大を制御し、
格子精度/級数/箱数の予算不足、接触・潰れ・同一・弧端/共有境界は未確認を保持する。
全体PASSには未処理/未確認領域なしと全根の幅達成を要求する。

追加7テストは円の2交点、楕円陰関数からの4交点、非零距離の楕円/双曲線頂点交点、
有限弧制限/離隔、接触/同一/潰れ/弧端、尺度/交換、格子/級数/箱数予算と厳密入力。
未実装ImportErrorを先に確認。初期接触fixtureが接点を有限弧から外していたため、
接点を含む弧へ訂正した。製品の正しい無交点判定や許容差は変更していない。
変更前369件中367合格・2 skip、最終376件中374合格・2 skip（98.680秒）。
out/validation-g03-offset-intersections-20260908 PASS。同所seed_comparison.jsonで
case hash一致、周波数差0、RF/エネルギー差最大8.882e-16。FEM/数値基準変更なし。
検証中の実装変更なし。GUI/Wineは今回未実行。

同所intersection_examples.jsonに入力・controls・根箱・認証証拠を保存（136349 bytes）。
円2交点PASS（121箱）、楕円4交点PASS（99箱）、楕円/双曲線1交点PASS（8箱）。
接触例は40箱予算で2領域を未確認として保持しUNVERIFIED。未確認を根なしに変えない。
既知座標との照合にはDecimal100桁の別計算を使用した。

R32としてRump (2010)の著者所属機関公開原稿Theorem 13.3、§13.1–13.2の数学的条件を確認。
出版社で書誌も照合し、REFERENCES.md / references.bibへ記録した。
区間演算・分割・証拠保存は既存Fraction核から独立実装。論文本文/掲載コードは転記せず、
INTLABや第三者PDFは同梱しない。新規依存/旧資産参照なし。

G03照合表・README・対応表・計画・実装状況を同期。
次は根箱からの有限接点復元、左右/半径の組合せ、有向円弧と空弧の検査、
線分中心軌跡、弧端/退化の追加分類、保存/Case/CLI/GUI、独立形状/FEM検証。
8親課題の限定受入を維持し、G03全体・全計画目標は未完了。


## G03法線オフセット区間と要件照合 — 2026-09-08

normal_offsets.normal_offset_bounds / partition_normal_offsetを追加。
円錐曲線フィレットの中心軌跡C=x+dNとC'=(1−dκ)x'を有理数区間で囲む。
二進回転係数のc²+s²を保持し、符号付き曲率/速度に反映する。
sin/cos中点級数+Lipschitz、sinh両端、coshと速度の有理数平方根境界を使用。
円の定曲率では相関を使い、半径分の内側オフセットが中心へ潰れることを保持する。
正則FORWARD/REVERSED、円のCOLLAPSED、ゼロを含むUNVERIFIEDを区別する。
全有限fraction区間を被覆し、予算不足/分離不足で未処理区間を除外しない。
PASSは全区間の正則性だけで、交点・尖点の存在/根数・フィレット候補完成ではない。

追加6テストは円の半径変化/潰れ、楕円/両枝双曲線頂点、点/数値微分の包含、
既知楕円折返し位置の保持と全区間被覆、予算/厳密入力、方向/尺度、
Decimalによる二進回転頂点の独立照合。未実装ImportErrorを先に確認した。
双曲線頂点の中心方向の初期テスト期待値は法線符号から訂正し、閾値緩和なし。
変更前363件中361合格・2 skip、最終369件中367合格・2 skip（94.587秒）。
out/validation-g03-normal-offsets-20260908 PASS。seed_comparison.jsonでcase hash一致、
周波数差0、RF/エネルギー差最大8.882e-16。FEM/数値基準の変更なし。
検証中の実装変更なし。GUI/Wineの新規実行なし。

同所offset_partitions.jsonは要求曲線/controls/区間結果を有理数表記で保存。
円はSINGULAR（1区間）、楕円は39区間処理後に18正則・2未確認を保持してUNVERIFIED、
双曲線は全区間正則でPASS。楕円の未確認を失敗根除外や尖点数証明へ読み替えない。
この基盤は通常Case/GUIからの弧フィレット構築へまだ接続していない。

G03_ACCEPTANCE.mdを新設し、CONIC_GEOMETRYの5段階と計画G03の要件を照合した。
曲線FEM/幾何別細分の既存comparison.jsonのPASSと、前回Chrome8操作のpassed=trueを
現在のファイルで再確認。全曲線入力互換・弧を含むフィレット・物理ピーク収束は不足を明示。
最小半径のプリミティブ値と、任意輪郭への制約契約も区別する。
README・対応表・計画・実装状況・バックログを同期した。

新規外部資料/コード/依存/旧資産参照なし。初等微分幾何と既存有理数区間核から独立導出。
次は中心軌跡の交点探索、有限接点/有向切詰め、保存/CLI/GUI、独立形状/FEM検証。
8親課題の限定受入を維持し、G03全体・全計画目標は未完了。


## G03版4指定半径の線分間フィレット — 2026-09-08

line_filletと構築schema_version=4を追加。2本の有向線分の支持交点を二進入力から
有理数で求め、R tan(|θ|/2)の切詰め距離で小円弧を構築する。交点以降の生成幾何は
浮動小数点を含み、支持直線距離・有限範囲・G1・保持方向を数値検査する。
版2/3の区間認証とは区別し、GUIにも指定半径・円弧長・数値検査と表示する。
有限線分の延長は明示bool、空/逆向き保持線分・平行/反転・数値未達を拒否し、
半径を自動縮小しない。線分/円弧/線分を完成Case全体の検査へ通す。

既知直角接点/中心/1/R曲率/除去面積を先にテスト化し、未実装ImportErrorを確認。
追加7テストは回転/鏡映/尺度/逆順、浅い/鈍い転向、過大半径/延長/厳密指定、
保存改変拒否/GUI共通APIと解析面積、二次曲線FEM相似則までPASS。
初期テストのNumPy scalar入力をbuilt-in floatへ修正し、数値未達用fixtureは
端点がfloatで一致する直角から非直角へ訂正した。製品の型契約・許容差は緩和していない。
変更前標準356件中354合格・2 skip、最終363件中361合格・2 skip（94.553秒）。
out/validation-g03-line-fillet-20260908 PASS。seed_comparison.jsonでcase hash一致、
周波数差0、RF/エネルギー相対差最大8.882e-16。FEM本体/数値基準の変更なし。

out/gui-line-fillet-browser-20260908/report.jsonのChrome8操作PASS、外部要求0、
実行中ソース変更なし。tangent-construction.pngの半径/長さ/検査範囲表示を確認。
明示選択・保存ダウンロード・再構築・適用・曲線FEM/描画・改変拒否まで実操作済み。
検証用GUIサーバーは停止済み。validation内construction_replay.jsonには
以前の版1/2/3と今回の版4の実保存ファイル再読込をCASE_VALIDATEDで記録した。

例はexamples/construction/corner_fillet_request.json。合成長方形断面の右上角を
R=0.02 mで丸め、geometry_order=2 / element_order=2を明示。
実CLI構築/Case/solveはout/g03-line-fillet-construction-20260908.json、
out/g03-line-fillet-case-20260908.json、out/g03-line-fillet-solve-20260908。
周波数1152045668.073337 Hz、R/Q(acc)=57.172456 ohm。GUIと同じ値を確認。
幾何の解析不変量とFEMの相似則の証拠であり、この形状のRF/ピーク収束は未検証。

式は初等直線/円幾何から独立導出。新規外部資料/コード/依存/旧資産参照なし。
Wine新規計算なし。次は円/楕円/双曲線弧を含むフィレットとG03全要件照合。
線分間の部分受入で全フィレット対応とは扱わず、8親課題の限定受入を維持する。
G03全体・全互換目標は未完了。


## G03版3固定支持直線・有限弧の構築統合 — 2026-09-08

line_arc_tangentと構築schema_version=3を追加。固定支持直線の接線条件w²=nQnと
接点c+Qn/wを二進入力から厳密有理数で求める。非接線・無限遠接点を区別し、
有限線分の延長可否と元の順序/保持端点を明示する。枝/有限弧/fractionを区間判定し、
空線分/空弧・逆向き・未確認は接続しない。生成端点と保持弧外端の位置誤差を囲む。
G1角度は数値検査。近傍線の自動補正・任意フィレット・角度区間認証とは区別する。
要求/保存/再構築・Case/CLI/GUIへ接続し、版1/2の既存保存文書も実再読込できた。

追加7テストは既知円/双曲線接点、枝/端点/延長/方向、非接線/漸近線、予算/厳密controls、
保存/GUI共通API、合成カプセルの解析面積/体積と実FEM相似則。
標準356件中354合格・2 skip（92.557秒）、out/validation-g03-line-arc-20260908 PASS。
同所seed_comparison.jsonでcase hash一致、周波数差0、RF/エネルギー相対差最大8.882e-16。
数値基準/FEM本体/許容差の変更なし。

out/gui-line-arc-browser-20260908/report.jsonのChrome8操作PASS、外部要求0、
実行中ソース変更なし。tangent-construction.pngで保持端/接点と誤差上界の表示を確認。
保存ダウンロード・再構築・明示適用・FEM/描画・改変拒否まで確認し、GUIサーバーは停止済み。
実CLI記録はout/g03-line-arc-construction-20260908.json、out/g03-line-arc-case-20260908.json、
out/g03-line-arc-solve-20260908。例はexamples/construction/capsule_line_arc_request.json。
版1のout/gui-tangent-browser-final-20260908/downloads/tangent-construction.json、
版2のout/g03-certified-capsule-construction-20260908.jsonもCASE_VALIDATEDで再読込した。

版2/3カプセル比較はvalidation内capsule_v2_v3_comparison.json。
双方617節点/1152三角形で、f相対差2.32491e-8、両RQ差0.626214%、G差8.12673e-8、
TTF差0.310662%。微小な構築差から再生成したメッシュ同士の比較であり、純幾何誤差と
FEM/RF誤差を分離していない。このカプセルのRF精度収束は未検証として保持する。
接点誤差上界をRF精度保証に読み替えず、差を隠す補正も行わない。

式は既存二次形式と初等幾何から独立導出。新規外部資料/コード/依存/旧資産参照なし。
Wine新規計算なし。次はフィレットとG03全要件照合。8親課題の限定受入を維持し、
G03全体・全互換目標の完了は宣言しない。


## G03版2区間付き構築・保存・CLI/GUI統合 — 2026-09-08

certified_constructionと構築schema_version=2を追加。確定fraction区間内のfloat位置を選び、
生成弧の数学的端点と出力floatを囲むboxから、厳密接点への距離上界を検査する。
外側の保持端点も誤差上界を確認する。G1角度は生成プリミティブの数値検査として区別。
第1弧END/第2弧STARTは元弧を再利用し、空弧・零長・逆向き・未達は候補と理由を残して選択不可。
版1の従来経路と保存文書の実再読込を維持。版2は同じCLI/GUIで保存/再構築/Case/FEMまで接続した。

最終標準349件中347合格・2 skip（91.637秒）、標準数値回帰PASS。
out/validation-g03-certified-construction-20260908のseed_comparison.jsonでcase hash一致、
周波数差ゼロ、RF/エネルギー相対差最大8.882e-16。基準更新なし。
Chrome8操作はout/gui-certified-construction-browser-20260908/report.jsonでPASS。
外部要求0・実行中ソース変更なし、tangent-construction.pngの誤差上界表示を確認。
検証用GUIサーバーは停止済み。Wine新規計算なし。

追加5テストは区間内切詰め/誤差上界、端点再利用/空弧拒否、版2保存/版1継続、
不正指定/位置未達、GUI応答と合成カプセルの解析面積/体積・実FEM相似則。
例題はexamples/construction/capsule_certified_request.json。
実CLIの構築/Case/solveはout/g03-certified-capsule-construction-20260908.json、
out/g03-certified-capsule-case-20260908.json、out/g03-certified-capsule-solve-20260908。

版1/2カプセル比較はcapsule_v1_v2_comparison.json。617節点/1152三角形は同数だが
メッシュ座標/接続は異なり、f差1.41259e-8、RQ差0.312004%、TTF差0.154291%を記録した。
接点位置誤差の保証をRF精度保証にせず、この形状のRF収束は未検証。補正/閾値変更なし。
仕様・再現・初期版との区別はTANGENT_CONSTRUCTION.mdとGUI_ACCEPTANCE.md。
新規外部資料/コード/依存/旧資産参照なし。

次は直線と弧の接線/フィレットとG03全要件照合。G03全体と全互換目標は未完了。


## G03有限弧所属とfractionの有理数区間 — 2026-09-08

certified_arcs.certified_finite_arc_tangentsを追加。支持曲線の接点boxから有限弧の
INTERIOR/EXTERIOR/START/END/UNVERIFIEDを判定し、fractionを有理数の閉区間で返す。
楕円は2 rad以下のsectorの和集合、双曲線は枝とsinhの単調性を使う。
端点sin/cosはTaylorのLagrange剰余、sinhは正項級数の幾何残尾で囲む。
float atan/asinhや経験的epsilonは判定根拠にしない。厳密な一点一致だけをSTART/ENDにする。
fractionはprefix所属の二分で囲み、未分離/予算不足では最後の有効区間を保持する。

最終標準344件中342合格・2 skip（86.157秒）、標準数値回帰PASS。
out/validation-g03-certified-arcs-20260908のseed_comparison.jsonでcase hash一致、
周波数差ゼロ、RF/エネルギー相対差最大8.882e-16。基準更新なし。GUI/Wineは今回未実行。

対象は保存された二進パラメータと支持係数。元の実数入力の丸め前まで認証しない。
独立8検査で10^-20 rad端点近傍、周期/逆向き/内部sector境界、双曲線枝/端点、
Decimal.expによる独立sinh照合、既知fractionの1/2・1/3・2/3、各予算不足を確認。
元の合成カプセル候補1件も両点INTERIORとfraction幅2^-32でPASS。
有理数レポートはout/validation-g03-certified-arcs-20260908/capsule_membership.json。
仕様と式は[TANGENT_CONSTRUCTION.md](TANGENT_CONSTRUCTION.md)。新規外部コード/資料/依存/旧資産参照なし。

次は区間から選んだ切詰め位置の接点誤差上界と明示位置許容差の検査、空弧/端点再利用の操作契約、
版付き構築・保存・CLI/GUIへの統合。既存の版1構築/GUIは数値ガード判定のまま保持する。
直線と弧の接線・フィレット・G03全要件照合は継続。全互換目標は未完了。


## G03支持曲線の接点座標区間 — 2026-09-08

contact_enclosures.supporting_contact_enclosuresを追加した。既存の孤立法線根区間から、
接触定数・接点座標を有理数区間で伝播する。厳密根は一点として扱い、D=0の±sqrt分岐を保持する。
分母の0分離に失敗すれば未確認。box幅上限の未達でも生成boxと候補番号を保存する。
返却float接点から厳密接点までの距離上界も別に返す。

最終標準336件中334合格・2 skip（85.740秒）、標準数値回帰PASS。
out/validation-g03-contact-enclosures-20260908に検証ログとseed_comparison.jsonを保存。
seed case hash一致、周波数差ゼロ、RF/エネルギー相対差最大8.882e-16。基準更新なし。

局所座標の厳密逆行列から双曲線指定枝を区間符号で検査する。
二進cos/sinのc²+s²を1と仮定しない。回転0.37 radの有理単位円点(3/5,4/5)の
順逆変換が一点boxで厳密一致する追加検査はlocal_inverse_invariant.jsonに保存した。
支持曲線の二進係数に対する区間であり、元の実数回転・測定寸法や有限弧端の所属を認証しない。
既存の有限弧構築・保存形式・CLI/GUI判定にはまだ接続せず、別APIとして公開する。

独立8検査は既知円/楕円/双曲線の無理数接点の二乗比較、根幅→box幅減少、
直角回転/移動/2^-20〜2^20尺度、返却接点誤差上界、指定枝反転、幅未達・未完根・一致曲線・不正幅。
仕様と再現は[TANGENT_CONSTRUCTION.md](TANGENT_CONSTRUCTION.md)。
新規外部資料/コード/依存/旧資産の参照なし。接触式と既存有理数境界から独立実装した。

次は局所接点boxと有限弧端の比較、内外/端点判定と区間に基づく切詰めの版付き構築統合。
双曲線の有限区間・楕円の有向周期区間、直線と弧の接線/フィレット、G03全要件照合は残る。
全互換目標は未完了。GUIは前回受入のままで今回新規実行しない。


## G03接線構築GUI受入 — 2026-09-08

GUIへ構築要求/保存結果の読込、接点・長さ・方向の候補表、明示選択、閉輪郭検査、
構築保存、編集画面への明示適用を追加。tangent_documentはCLIと同じ構築/再構築/Case経路を使う。
要求の編集・候補変更・別ファイル読込で古い結果を解除し、非同期の古い応答も除外する。
読み込み/候補表示だけでは現在のプロジェクトを変更しない。適用時は要求の計算条件も反映する。

最終標準328件中326合格・2 skip（85.344秒）、標準数値回帰PASS。
out/validation-g03-tangent-gui-final-20260908のseed_comparison.jsonでcase hash一致、
周波数差ゼロ、RF/エネルギー相対差最大8.882e-16。ベンチマーク更新なし。
out/gui-tangent-browser-final-20260908のChrome7操作PASS、外部要求0、実行中ソース変更なし。
保存再読込→適用→FEM→場表示、改変拒否まで実操作し、tangent-construction.pngを表示確認した。
GUI合成カプセルf=1170098360.3437803 Hz。物理精度収束や旧版照合の証明ではない。

初回out/gui-tangent-browser-20260908はJavaScript JSON再生成で1.0等の表記が変わり、
保存後の厳密再構築照合がFAIL。サーバーが生成したserialized文字列をそのまま保存する修正後に再検証した。
初回数値回帰はPASSだったがGUI未受入であり、最終版とは区別する。失敗ログは保持。
再現と操作はGUI_GUIDE.md、GUI_ACCEPTANCE.md、TANGENT_CONSTRUCTION.md。
検証用GUIサーバーは停止済み。新規外部資料/コード/依存/旧資産参照なし。

次は接点区間/弧端認証、直線と弧の接線・フィレットとG03全要件照合。
GUIの追加をG03全体の完了や全互換目標の完了とは扱わない。


## G03接線構築の保存・Case・CLI — 2026-09-08

tangent_construction.pyに版1の構築要求/結果と保存後の再構築照合を追加した。
case_templateは未完成の編集文書、候補未選択のcaseはnullと明示する。
連続する2つのPEC弧を明示選択で弧/線/弧へ置換し、既存Caseで閉輪郭と全設定を検査する。
construct-tangent/export-constructed-caseを追加し、既存solveまで接続。
primitiveのstrict読書きを既存CurvedContourと共通化。計算式と依存は変更していない。

最終標準326件中324合格・2 skip（86.428秒）、標準数値回帰PASS。
out/validation-g03-construction-cli-20260908にtests.log/validation.json/seed_comparison.jsonを保存。
seedのcase hash一致、周波数差ゼロ、RF/エネルギー相対差最大8.882e-16。基準更新なし。
検証実行中のsrc/tests/scripts/examples変更なし。GUI/Wineの新規実行なし。

合成カプセルの解析面積/回転体積、実FEMの寸法2倍でf半減・両RQ/G/TTF不変、
保存再構築/改変検出・未確認出力・不正設定/上書き拒否など追加7検査を実装した。
初回例題は長さ0.2 mから0.6 mへ変えた際のjoin_toleranceを流用して境界padding検査に失敗。
入力の許容差を1e-12 mと明示し、既存の許容差上限や判定は変更しなかった。
詳細と再現コマンドは[TANGENT_CONSTRUCTION.md](TANGENT_CONSTRUCTION.md)。

例題はexamples/construction/capsule_request.json。実CLIの構築/書出/solveは
out/g03-capsule-construction-20260908.json、out/g03-capsule-case-20260908.json、
out/g03-capsule-solve-20260908。基本モード1170.098360 MHz。
これは合成例の動作/相似則検証であり、この形状の物理精度収束・旧版照合ではない。

次はGUIの候補表示/明示選択/保存/Case適用。厳密接点区間/弧端認証、直線と弧の接線、
フィレット、G03全要件照合は継続。全計画目標は未完了。
新規外部資料/コード/依存/旧資産の参照なし。


## G03有限弧数値判定と明示選択G1接続 — 2026-09-08

arc_tangents.pyへ有限有向弧の区間/枝判定、方向記録、明示選択の切詰め・局所G1接続APIを追加。
既存の支持曲線列挙を保持し、候補を勝手に選ばず、元曲線の中心/半軸/回転/枝を変えない。
弧端はガード付き未確認。fractionは数値推定であり、厳密な接点区間包囲ではない。
仕様・独立9検査と初回期待値の訂正理由は[TANGENT_CONSTRUCTION.md](TANGENT_CONSTRUCTION.md)。

開始時310件中308合格・2 skip。追加後の独立全テストは、実行中にmodule docstringを
編集してStudyのソース変更検査1件が作動した。数値実装の変更ではないが失敗を保持する。
標準validate内の最終全319件中317合格・2 skip（85.826秒）、標準数値回帰PASS。
出力はout/validation-g03-finite-arcs-20260908、初回失敗はinitial_parallel_tests_source_changed.log。
seed_comparison.jsonで円筒6/成形セル3モードのcase hash一致、周波数差ゼロ、
RF/エネルギー相対差最大8.882e-16。ベンチマークは変更していない。GUI/Wineの新規実行なし。

次は構築要求/選択結果の保存・Case/CLI/GUI・閉輪郭検証への接続。
厳密な接点区間/弧端の認証、直線と弧の接線、フィレット、G03全要件照合は残る。
全33親課題の継続目標は未完。新規外部資料/コード/依存/旧資産の参照なし。


## 主要文書の現状同期 — 2026-09-08

製品基準e68002fにREADME・IMPLEMENTATION_STATUS・COMPATIBILITY_MATRIX/PLAN・BACKLOGと
曲線要素/物理仕様の入口を同期。現在の8親課題の限定受入とG03残件を冒頭に集約した。
以下の実装履歴は当時の記録として保持する。文書のみの変更で製品状態は変わらない。
標準310件中308合格・2 skip（85.808秒）を再確認。validate/GUI/Wineの新規実行なし。
次の実装は下節の有限弧制限・G1接続。全互換目標の新規開始/完了を意味しない。


## G03共通接線の四次式と接点再構成 — 2026-09-08

conic_tangents.supporting_conic_tangentsを追加し、[接線構築仕様](TANGENT_CONSTRUCTION.md)の
四次消去式を有理数で生成してSturm根分離へ接続した。
入力有限弧が属する円錐曲線全体を扱い、有限区間と双曲線の指定枝はまだ制限しない。
arc_filter_status=NOT_APPLIEDを返し、候補を自動選択/切詰め/Case化しない。

2つの法線座標表示で全方向を扱い、境界±1は第1表示へ割り当てる。
D=0の有理根を復元して、同じ法線に対応する2つの直線定数を保持する。
区間全体での負の接触二次式、厳密な無限遠接点を区別して除外する。
根分離/分母分離/座標再構成が未確認なら、その根区間と理由を残す。
同一円等の零消去式を「候補なしPASS」としない。

戻り値のfloat接点・法線・中心相対の直線定数を使って、陰関数・直線上の位置・
陰関数勾配との接線方向を再検査する。座標の桁落ちで接点を表せないケースもUNVERIFIED。
既定無次元残差1e-10を絶対位置誤差上界や元実数曲線の存在保証とは呼ばない。
接点距離の非有限値は拒否し、float接点の一致は出力精度での一致と明記する。

独立8検査: 円の4接線と既知距離、接触/交差/包含/同一円、回転/移動/尺度の楕円、
異なる半軸/回転と同中心の楕円、双曲線陰関数、漸近線、予算不足、座標精度不足。
最初はfixtureの一周弧/NumPy数値型が既存conics入力に拒否され、半周/Python数値型へ修正した。
conicsの入力制約を緩めていない。
最終標準310件中308合格・2 skip、対象8件PASS。
標準物理回帰validation-g03-conic-tangents-regression-20260908は返却値再検査強化前にPASS。
強化後は標準310件を再実行した。FEMソルバーの変更はない。

次は有限弧の区間/枝/進行方向による候補制限、明示許容差での切詰めとG1線分接続。
続いて候補選択/保存/CLI/GUI・閉輪郭の全体検査へ接続する。
円錐曲線全体の候補PASSを有限弧の接線構築完成とは扱わない。
既存R30/R31の数学を参照した独自実装であり、新規外部コード/旧資産の参照はない。
G03全体と全互換目標は継続。

## G03接線構築仕様と実根分離基盤 — 2026-09-08

[TANGENT_CONSTRUCTION.md](TANGENT_CONSTRUCTION.md)で共通直線接線の候補列挙を仕様化。
有限有向弧、指定双曲線枝、複数候補の明示選択、元曲線非変更、ゼロ長接続/無限候補/
無限遠接点と候補なしの区別を定めた。曲率指定フィレット等を完了扱いにはしない。
中心とQ行列から接触条件を立て、2条件の消去による同次四次式を独自導出。
2つの法線座標表示で垂直接線を失わず、D=0・二乗の余分な根・元弧への制限を別処理する。
四次式の生成/接点再構成/候補選択/Case・CLI・GUI接続は未実装。

実装したのはpolynomial_roots.isolate_real_roots。
既存の有理数多項式係数規約を使い、除算/gcdで平方因子を除いてからSturm列で根数を数える。
閉入力区間の端点根は厳密点、非点の分離区間は開区間とする。
重根も異なる根として一度数え、予算不足時は未分離区間とその厳密根数を残す。
PASSは指定区間内の全根の分離と幅条件の達成を表し、係数の入力不確かさは対象外。
ゼロ多項式は無限根として拒否。予算は区間処理数の上限であり、演算時間上限ではない。

独立検査5件は既知有理根の積、複素因子、端点三重根、10^-40間隔の根、
係数の符号/尺度、±sqrt(2)、一点区間、入力拒否と予算不足時の根数保存。
標準302件中300合格・2 skip、validation-g03-tangent-roots-regression-20260908 PASS。
この基盤だけを接線自動構築の完成証拠にしない。次は四次式/接点再構成への接続。

新規参照R30は双対円錐曲線の接触条件、R31は端点を含むSturm根数と重根の扱い。
大学掲載のチュートリアルと著者公開論文を確認し、本文・コード・図の転記はない。
MIT講義のSturm節は未完成だったため、根数実装の根拠から除いた。
G03全体と全互換目標は継続。

## G03二次幾何近似の追加系列受入 — 2026-09-08

前回からのsession 24316を継続して確認し、exit 0で完了した。
out/validation-g03-native-geometry-separated-20260908/comparison.jsonはPASS。
対象は既存の合成楕円と双曲線、弦許容差倍率1,.0625,.015625の3段階。
各幾何段階で固定二次写像のFEM細分0→1を行い、全6比較がPASS。
面積/回転体積相対誤差の各段階での減少、最細各1e-5未満、最後の幾何近似間比較も全ゲートPASS。

| 対象 | 最細要素数 | 最細面積相対誤差 | 最細体積相対誤差 | 最後の周波数相対差 | 軸場L2相対差 | R/Q相対差 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 合成楕円 | 13452 | 1.2881e-8 | 1.9322e-8 | 1.0050e-7 | 6.3866e-6 | 1.0284e-5 |
| 合成双曲線 | 7684 | 5.7777e-10 | 1.1497e-9 | 4.0238e-8 | 7.2460e-6 | 3.5673e-6 |

磁場重なりは楕円0.999999999997、双曲線0.999999999968で同定PASS。
Q0、幾何因子、壁損失、通過時間係数、両R/Q定義の既存RFゲートもPASS。
周波数/軸場/RF閾値は1e-3/1e-2/1e-2の既存値から変更していない。
面積/体積は検証専用の直接積分式との照合であり、FEM解への解析式の代入はない。

初回倍率1,.25,.0625のFAILは
out/validation-g03-native-geometry-convergence-20260908/comparison.jsonへ保持する。
停滞/中間増加を丸めてPASSへ変更しない。
検証スクリプトの既定倍率を今回の受入系列へ変更し、旧系列は
--factors 1 .25 .0625で明示して再現できる。保存再検証と幾何間比較の開始ログも追加。
この変更は引数の既定とログのみ。受入計算は同じ倍率を明示して実行した結果であり、
物理計算/ゲートを変えていない。最終の--help実行でCLIを確認した。
前回の標準297件中295合格・2 skipを保持し、同じ数値ソルバーを再試験していない。

この受入は2つの合成例の3段階系列である。幾何間の場/RF差には残るFEM誤差も含む。
積分モーメントから局所境界最大誤差や物理ピーク誤差を保証しない。
物理ピーク収束はUNVERIFIED。次は接線の自動構築とG03全要件照合。
本節を最新状態とし、過去の実行中記録は履歴として残す。全互換目標は継続する。

## G03二次幾何近似の独立検証 — 2026-09-08

scripts/validate_curved_geometry_convergence.pyを追加した。合成楕円/双曲線の
弦許容差を3段階に変え、各段階で固定二次幾何のFEM細分0→1を行う。
各FEM比較は既存Studyの周波数/軸場/RF/同定閾値を使用し、形状近似間も
細分段数1の保存結果を比較する。形状間の場/RF差には残るFEM誤差も含む。

独立参照は例題を明示的に積分する。楕円は半軸a=.1、b=.08の上半面で
面積πab/2、回転体積4πab²/3。双曲線はr=a sqrt(1+(x/b)²)、
x=z−.05、a=.05、b=.08、−h<=x<=h、h=.05であり、
面積a[h sqrt(1+(h/b)²)+b asinh(h/b)]、体積πa²[2h+2h³/(3b²)]。
例題がこの参照と異なれば拒否し、式をソルバーには使用しない。
二次写像のdet Jと2πr det Jを各方向6点のGauss積分規則で積分して比較する。
これは多項式モーメントの検査であり、局所境界の最大誤差を保証しない。

受入条件は各段階のFEM PASS、面積/体積相対誤差の段階ごとの減少、
最細モーメント誤差各1e-5未満、最後の幾何近似間比較PASS。
--factorsは正・有限・厳密減少の3数を要求する。
初回の既定1,.25,.0625はout/validation-g03-native-geometry-convergence-20260908へ保存しFAIL。
楕円の最初の2段階は面積/体積誤差3.0930e-6/4.6374e-6で停滞した。
双曲線は中間で8.6724e-8/1.7258e-7から1.2283e-7/2.4445e-7へ増加した。
全段階のFEM比較と最後の幾何間比較、最細モーメント閾値はPASSだが、減少条件はFAIL。
弦許容差だけを細かくしても、メッシュ制御の分割により同じ二次境界になり得る。
初回結果を上書きせず、閾値を緩和せず、より細かい近似を含む1,.0625,.015625を追加実行する。

楕円初回0/1のPEC境界を元曲線の向きに揃えて照合した。
16辺の元曲線区間差は最大1.388e-17、節点座標差は最大3.470e-18 mであり、
ビット単位で同一ではないが、丸め誤差の範囲の変化しかない。
標準297件中295合格・2 skip。ソルバーの変更や受入閾値緩和はない。

追加系列の実行中記録（完了証拠ではない）:
コマンドは同スクリプト --factors 1 .0625 .015625
--out out/validation-g03-native-geometry-separated-20260908。
実行ハンドルはexec_command session 24316、ログ/tmp/g03-native-geometry-separated.log。
最後の確認で稼働中。楕円0/1はFEM PASS、モーメント誤差は
3.0930e-6/4.6374e-6から1.9348e-7/2.9019e-7へ減少。
楕円最細13,452要素のpoint-002保存は完了し、保存後の再検証/比較が進行中。
追加系列の総合合否は未確定。次の継続で同じハンドルをpollし、
完了していればcomparison.jsonを検査する。観測待ちだけを理由に再実行しない。
全互換目標を継続し、幾何近似収束を完了に変更しない。

## G03曲線鏡映GUI受入 — 2026-09-08

RF詳細へ鏡映結果の部分スペクトル表示を追加した。直線のreflection_source_caseと
曲線のreflection宣言を対象に、全空洞の固有周波数順位ではないことを明示する。
物理ピーク収束の未確認表示は保持する。

verify_gui.mjsに--curved-reflection yesを追加。
--contour-case examples/curved_hyperbola.json --contour-auto yes --curved-fem yesと併用し、
双曲線の左右端×電気/磁気対称の4入力を検証出力先へ生成してファイル読込する。
各入力で鏡映チェックボックスを実クリックし、計算・保存結果選択・描画まで操作する。
保存された面と偶奇、全Caseの規格化2倍、RFの蓄積エネルギー、部分スペクトル文を検査する。
既存の入力/往復/曲線P2/固定Study7操作に加え、計11操作がPASS。

out/gui-curved-reflection-accepted-20260908/report.jsonはpassed=true、
source_changed_during_run=false、external_requests=[]。
curved-reflection.pngで角診断、物理ピーク未確認、部分スペクトルの日本語説明、
U=2 J（電気/磁気各1 J）を確認した。検証後にGUIサーバーを停止。
標準297件中295合格・2 skip。JavaScript構文検査もPASS。
数値ソルバーや受入閾値の変更はない。

次は二次曲線の幾何近似収束と接線構築の要件照合。
曲線鏡映GUIの限定操作を受入済みとして更新するが、G03全体と全互換目標は継続する。

## G03楕円/双曲線の固定幾何FEM・双曲線鏡映/GUI — 2026-09-08

scripts/validate_curved_shapes.pyを追加し、既存の合成楕円と双曲線をgeometry_order=2、
quadrature_order=12で通常Studyへ渡す。固定二次幾何の細分段数0→1を比較し、
周波数、磁場の同定、軸場L2、RFを既存閾値で評価する。
out/validation-g03-additional-native-shapes-20260908/comparison.jsonはPASS。
楕円は周波数相対差9.2214e-7、軸場L2差1.0679e-4、R/Q相対差4.8770e-4。
双曲線は周波数相対差1.9776e-6、軸場L2差2.7972e-4、R/Q相対差4.3213e-4。
磁場重なりはそれぞれ0.9999999980と0.9999999887。同定/周波数/軸場/RF全ゲートPASS。
これは固定二次境界に対するFEM細分の比較であり、元解析曲線への幾何近似収束は評価しない。

双曲線の左右端をそれぞれ電気/磁気対称として、通常solve→reflect_solution→save→readを実行。
4条件すべてで全領域残差・場の偶奇性・エネルギー/壁損失2倍の不変量がPASS。
最大残差5.1186e-14、場の偶奇相対差6.1084e-12、2倍からの相対差5.3291e-15。
端で鏡映した双曲線の壁には元の曲線接線に応じた角があり、保存した角診断を保持する。
物理ピークの収束はUNVERIFIED。有限の離散極値や小さな残差を物理ピーク認証に読み替えない。

実ブラウザーはverify_gui.mjs --contour-case examples/curved_hyperbola.json
--contour-auto yes --curved-fem yesで7操作PASS。
out/gui-curved-hyperbola-native-accepted-20260908/report.jsonは
source_changed_during_run=false、external_requests=[]。
双曲線の入力/自動メッシュ/保存往復、二次幾何・積分次数12・細分段数1、
固定幾何Study 0→1とその場の表示を操作した。GUIでの鏡映チェックボックスは今回の7操作には含まない。
curved-controls.pngとfixed-study.pngで設定値とStudy PASS/結果表を画像確認。
検証後にローカルGUIサーバーを停止。標準297件中295合格・2 skip。
今回の変更は検証スクリプトと文書であり、数値ソルバーの変更や閾値緩和はない。

次は二次曲線の幾何近似収束、曲線鏡映のGUI操作、接線構築の要件照合。
G03全体の受入は未完で、全32項目/33親課題の目標を維持する。

## G03曲線鏡映の通常API・保存・CLI接続 — 2026-09-08

reflect_solutionはgeometry_order=2の曲線解を固定写像で鏡映する。
入力Caseと解の一致を要求し、全領域の残差と正規化/直交性を再確認する。
固有値の再計算や振幅再調整はない。元の半領域係数を偶奇に従って移し、
全領域Caseのnormalization_jは2倍。mode indexは偶奇部分スペクトルの順序である。
既存のreflected_acceleration_parametersによりユーザー指定の加速長、電圧積分区間、
位相原点も変換する。両端面と両対称タグの保存往復で非既定値を検証した。

保存results.reflection第1版は元Case、面、偶奇、固定写像再構成と振幅の契約を保持する。
mesh.jsonは半領域の元弦メッシュであり、results.mesh.sourceにその用途を明記する。
再読込は元Case+弦メッシュから二次写像と固定細分を再構成した後に鏡映し、
導出した全Caseと保存Caseを照合する。幾何配列の完全照合、係数の偶奇完全照合、
全領域残差、エネルギー規格化、全RF値の再検査を実施する。
直解と鏡映のfield_constructionも厳密照合する。未知の版、面/偶奇/元Case改変、
宣言削除、構成表示の偽装、係数改変はhash更新後も拒否する。
再読込した鏡映解の再保存も可能。既存の直解の保存形式は維持する。

新規tests/test_curved_reflection_saved.pyの4検査は左右×電気/磁気対称の保存/再保存、
再固有値計算の禁止、正規化/場の一致、7種の改変拒否、CLI --reflect-full、
Case不一致と二重鏡映の拒否を含む。
標準297件中295合格・2 skip、validation-g03-reflection-integration-regression-20260908 PASS。
scripts/validate_curved_reflection.pyは通常APIの鏡映をsave/readした結果で物理不変量を検証する形へ更新。
out/validation-g03-curved-reflection-storage-20260908/comparison.jsonの合成半球4ケースはPASS。
最大残差8.695e-14、場の偶奇相対差1.350e-12、エネルギー/壁損失の2倍からの相対差1.433e-14。
周波数値を移したことと全方程式の残差は確認したが、これを物理的な離散化誤差の認証とは扱わない。

保存結果のplot CLIも実行。初回画像は曲線鏡映の部分スペクトル注記が欠けていたため、
visualizeの既存直線鏡映判定を曲線のreflection宣言にも対応させた。
同じ保存結果からreflected-plot-final.pngを出力し、全曲線形状・場・軸/半径プローブ、
U=2 J、部分スペクトルで全固有値順位ではない注記を画像で確認した。
図の修正は標準検査後であり、最終plot CLI実行と画像で確認した。
GUIブラウザー操作は今回未実行。追加形状、GUIを含むG03全要件の照合は次の作業。
物理的な角ピークの収束は引き続きUNVERIFIED。G03全体と全互換目標は継続。

## G03固定二次空間の鏡映核 — 2026-09-08

curved_reflection.reflect_curved_spaceは元の二次写像を鏡映し、対称面の節点を
境界の接続情報で共有する。全要素の向きを保つため局所節点を0,2,1,5,4,3へ並べ替える。
元曲線を再投影せず、固定細分済み空間にも適用する。元曲線の番号と区間は
CurvedContour.reflectedの全輪郭へ写し、鏡映側の曲線パラメータは1−tとなる。
全辺の交差/共有接続、境界閉鎖、全要素Jacobianを既存の検査で再確認する。

係数写像は電気対称で偶、磁気対称で奇。applyは磁気面の非零係数、
不一致の節点数、非有限値を拒否する。場ではHphiとEzがこの偶奇、Erが逆の偶奇となる。
独立不変量は変換行列Pに対するP^T K_full P=2 K_halfと
P^T M_full P=2 M_half（磁気の場合は半領域の自由空間へ制限）、
物理座標と勾配の鏡映則。左右の面、両対称タグ、固定細分段数1で確認した。

最初の右端面検査は細分の浮動小数点評価による約1.4e-17 mの座標差で失敗した。
面は座標の完全一致で探索せず、タグ付き境界の節点を使う。
512 eps×領域寸法以内の面座標だけ丸め誤差として揃える。実際のずれ1e-8 mは拒否する。
軸辺の中点もRFの厳密なアフィン軸規約へ揃える。
既存の親空間や保存結果は変更しない。写像/勾配/行列不変量の許容差緩和はない。

scripts/validate_curved_reflection.py --out out/validation-g03-fixed-curved-reflection-20260908
は合成半球の左右×電気/磁気対称4ケースを計算し、全領域では固有値を再計算せず係数を移す。
全領域残差最大8.695e-14、場の偶奇相対差最大1.350e-12、
電気/磁気/総エネルギーと壁損失の2倍からの相対差最大1.433e-14でPASS。
これは半球メッシュの物理的離散化誤差や表面ピーク収束の認証ではない。
開始時289件中287合格・2 skip。変更後293件中291合格・2 skip。
最後に行列全体の不変量も追加し、対象4件PASS。
validation-g03-reflection-core-regression-20260908もPASS。

通常reflect_solutionは曲線解をまだ拒否する。保存・CLIへの接続は次の必須作業。
半領域Caseと元弦メッシュ、細分段数、鏡映版/面/偶奇を保存し、再読込では
半領域の二次空間を再構成して同じ鏡映を行ってから、全Case・幾何配列・係数・RFを照合する。
全Caseからの再メッシュでは元写像を再現できないため使用しない。
規格化は半領域の2倍、モード番号は偶奇で選ばれた部分スペクトルと明記する。
未実装の保存経路をPASSとは扱わない。G03全体と全互換目標は継続。

## G03元曲線の角診断と保存第2版 — 2026-09-08

curved_corners.classify_curve_joinsは元の解析曲線の接続点を対象とし、メッシュ細分の
継ぎ目を角に数えない。正向き(z,r)輪郭の接線から符号付き旋回角を求め、
軸外のPEC同士では真空内角=π−旋回角として凸角/再入角を分類する。
軸接続、異種境界接続、非PEC同士は分け、平面の角として物理性を推定しない。
角度許容差は1e-8 rad。許容差内の接線一致は厳密な滑らかさの証明ではない。
端点位置と接続隙間、曲線番号、タグ、角度、分類を保持する。
この診断は幾何学的な注意箇所の識別であり、モード固有の発散/有限性を断定しない。
physical_peak_statusはUNVERIFIED。再入角は専用のピーク収束評価を必要とする。

新規results.surface_extremaはversion=2、corner_diagnostics_version=1を持ち、
surface_corner_diagnosticsを必須とする。読込時は元Caseから再計算して照合する。
第1版と宣言なしの旧結果を保持。旧版に後付けした診断も、存在するなら常に再検証する。
診断欠落や物理ピーク状態をPASSへ変えたデータは、hash更新後も拒否する。
第1版の実保存結果validation-g03-peak-rf-surface-final-20260908/level-1も再読込確認。
GUIのRF詳細へ分類数と物理ピーク収束未確認を追加。旧結果の未提供欄は未評価と表示する。

独立検査は段差の270度再入角・凸角数、1e-5/1/1e5寸法倍率、曲線分割による角数不変、
球の軸接続と異種境界接続。最初の混合タグfixtureは内側の線へ対称タグを指定して拒否されたため、
既存契約どおり端面のタグへ修正した。境界契約の緩和はない。
scripts/validate_curved_corners.py --out out/validation-g03-native-corner-diagnostics-20260908
は同じ段差の段数0/1をsolve/save/readし、各270度診断と保存整合がPASS。
周波数相対変化1.00935e-3、離散Eピーク比1.0735116を観測。
これは周波数/物理ピークの収束PASSではなく、physical_peak_status=UNVERIFIEDを保持する。
標準289件中287合格・2 skip、validation-g03-corner-diagnostics-regression-20260908 PASS。
最終の旧版後付け診断の検証強化は保存関連8件で確認。

最終GUI検証out/gui-curved-corners-final-20260908/report.jsonは7項目PASS、
source_changed_during_run=false、external_requests=[]。
RF詳細の角診断文はDOM検査で確認した。corner-diagnostics.pngは詳細表の中央を撮影しており、
診断文自体は画面外のため、その文の視覚確認証拠には使わない。
画像ではRF値と未評価表示を確認。検証後にローカルGUIサーバーを停止した。

次は曲線鏡映と追加形状の総合受入。物理的な角の有限ピークを認証したとは扱わない。

## G03連続離散ピークのRF/保存/GUI接続 — 2026-09-08

quantities_curvedは既定で連続離散ピークの上下界を計算する。
E/Hの下界と上界を別の数値欄に出し、共通のEpk/Bpk推定値欄には上界を使う。
Epk/EaccとBpk/Eaccも上界から計算し、|Vacc|<=1e-12*絶対軸積分の場合はNone。
peak_statusは物理的な角とメッシュ収束の未認証を明記し、離散極値PASSと混同しない。

新規保存results.surface_extremaはversion=1、厳密有理数Bernstein方式、相対幅1e-6、
辺あたり区間上限10000、PEC閉辺/片側微分、上界を推定値に使う契約を持つ。
readは宣言を型を含め厳密照合し、保存係数からピークを再計算して全RF欄と照合する。
宣言を除去して新しいピーク欄だけ残したデータや、hashを再生成したピーク改変も拒否する。
宣言なしの旧曲線結果はinclude_surface_peaks=Falseの従来RF契約で再検証し、元の未評価を保持。
旧実出力validation-g03-native-storage-20260908/runの読込も確認した。
将来評価方式を変更するときは版を分け、既存版の再検証を維持する。

GUIのRF詳細に離散E/Hピークの上下界名を追加し、共通EpkラベルのP1限定表記を修正。
Studyはピーク数値の存在と物理収束の受入を分け、表面収束を判定していないと表示する。
テストは旧保存形式、評価版/値の改変拒否、U×4→ピーク場×2・Epk/Eacc不変、
一定軸場の位相相殺によるピーク比未定義を検査する。

標準285件中283合格・2 skip、validation-g03-peak-rf-regression-20260908 PASS。
validation-g03-peak-rf-surface-final-20260908/comparison.jsonの球形表面/連続極値は両段階PASS。
新規保存の段数1はE最大[8729690.67140714,8729694.094318945] V/m、Epk/Eacc上界推定1.8812138684。
従来の周波数/体積場/RF積分の許容差と基準結果は変更なし。
out/gui-curved-peak-accepted-20260908/report.jsonは実ブラウザー7検査PASS。
評価版・有限なピーク比・物理未認証表示を確認。外部通信0、実行中ソース変更なし。
ブラウザーとGUIサーバーは終了済み。
次は物理的な角の扱い、曲線鏡映、追加形状の総合受入。G03と全互換目標は継続。

## G03離散曲線場の連続極値上界 — 2026-09-08

rational_bounds.bound_rational_normは[0,1]上のsqrt(ΣN_i²)/D、D>0を上下から囲む。
係数は昇べき順。入力floatはその二進値を厳密なFractionへ変換し、以後の多項式演算、
Bernstein変換・次数上げ・中点de Casteljau分割と上界比較は有理数で行う。
ΣN_i²とD²を同じBernstein次数に揃え、D²の全係数が正なら係数比の最大が上界。
これは商を正の重み付き平均で表せることによる。D²の正値と端点D>0から符号を保持する。
正値を囲めない区間は分割し、評価点でD<=0なら拒否する。

端点/中点の厳密値を下界候補とし、最大上界の区間から分割する。
既定相対幅1e-6、生成区間予算10000。予算不足はUNVERIFIED。
戻り値の平方根floatは、二乗をFractionで比較して外向きに丸める。
二乗値がdouble範囲外でもノルムを出力できるよう2の冪で正規化する。
外向き丸めで幅を超えれば追加分割し、厳密最大値自体のfloat幅が不足ならUNVERIFIED。
下界を得たパラメータはfloatと厳密分数を保持する。

curved_extrema.edge_field_polynomialsは保存された6節点/係数から式を直接作る。
H=r*uは4次。Er/Ezは4次以下の分子とomega*epsilon*det(J)の分母からなる。
曲線境界の向きと物理勾配を既存CurvedSurfaceSamplerに照合した。
bound_surface_peaksは全PEC辺を閉区間として評価し、全下界/上界の最大を返す。
返す辺番号と点は下界の評価位置であり、一意な最大点の証明ではない。
角の各セル側を保持する。PASSは保存された離散場の連続極値の囲い込みを意味し、
物理的ピークのメッシュ収束や角特異性の解消を意味しない。
通常RF/保存のpeak_statusはまだ変更していない。

独立検査: 33等間隔点が最大値の1/1000未満しか拾わない狭い有理ピーク、
端点/内部/ベクトル/ゼロ、分母の内部ゼロ、1e-300/1e300尺度、予算/出力精度不足。
一定uでH最大=.08 m相当、E一定=2/(omega*epsilon)の既知値も囲む。
楕円の全辺で有理式と直接の物理勾配評価が一致し、65点/辺のサンプルも上界内。

out/validation-g03-continuous-extrema-20260908/comparison.jsonは保存後の球形段数0/1でPASS。
段数1のE最大は[8729690.67140714,8729694.094318945] V/m、
H最大は[31789.659659353736,31789.678147827413] A/m。
E/Hの区間全体と独立球形の厳密最大との差は各2.58738e-5、3.28173e-6以内（ゲート1%）。
各辺で相対幅1e-6以内。段数1の生成区間数はE合計64、H合計60。
再現: scripts/validate_curved_surface.py --out <新規ディレクトリ>。
標準282件中280合格・2 skip、validation-g03-continuous-extrema-regression-20260908 PASS。
最後のfloat幅停止条件の調整は関連7検査で確認した。
次は通常RF/保存再読込/GUIへの版付き接続と物理的な角の扱い。曲線鏡映も継続。

## G03曲線表面場の片側評価 — 2026-09-08

curved_surface.CurvedSurfaceSamplerが境界辺の唯一の隣接セルを求め、二次写像上で
Hφ、Er/Ez、外向き法線/接線、En/Et、|E|と弧長微分を評価する。
パラメータは保存辺の端点順。接線は正のJacobianを持つセルの反時計回り順で、
外向き法線(r,z)=(t_z,-t_r)。保存辺の順序を反転しても法線は反転しない。
角/共有節点は各隣接境界セルの微分を保持し、平滑化や平均化をしない。

sampled_surface_summaryはPEC辺だけを対象に、各辺の端点を含む等間隔サンプルの
最大|E|/|Hφ|/|Et|、位置、辺番号、パラメータを返す。既定17点/辺。
返却statusに有限サンプルの推定と明記し、連続境界の極値や収束を保証しない。
通常RFのpeak_statusは引き続き未評価。サンプル推定を従来のピーク欄へ代入しない。

独立検査は物理線形u=1+2r+3zの表面射影、凸楕円の外向き法線、辺順序反転、
乱数係数での節点片側微分の不連続保持、strict引数とPEC限定を使う。
scripts/validate_curved_surface.py --out out/validation-g03-curved-surface-traces-20260908
は球形R=.08 m、二次幾何/場、固定幾何段数0/1を通常solve/save/read後に比較する。
壁面の8点Gauss×2πr dsで電磁場の相対L2を評価し、33点/辺で最大サンプル値を比較。
球形参照は表面|E|∝|cosθ|、|Hφ|∝sinθより極/赤道に厳密な最大値を持つ。
参照E最大8.72991655 MV/m、H最大31789.764 A/m。各誤差ゲートは1%。

| 相対量 | 段数0 | 段数1 |
|---|---:|---:|
| 表面電場L2 | 5.40773e-3 | 1.51948e-3 |
| 表面磁場L2 | 4.29670e-5 | 5.54276e-6 |
| 最大Eサンプルと厳密最大の差 | 4.00616e-4 | 2.58738e-5 |
| 最大Hサンプルと厳密最大の差 | 2.90061e-5 | 3.28173e-6 |
| 最大Etサンプル / 参照E最大 | 6.82912e-3 | 1.84038e-3 |

標準275件中273合格・2 skip、validation-g03-surface-traces-regression-20260908 PASS。
全ゲートPASS。実際の二次壁は解析球面の近似であり、接線成分には幾何近似の影響も含む。
この比較は体積場/周波数/RF積分と独立した表面検査で、連続極値の探索受入とは別。
次は連続境界の極値の上界/停止条件と角の扱いを実装し、通常RF/保存/GUIへ接続する。
曲線鏡映と追加形状の総合受入も継続する。

## G03曲線計算設定と固定幾何StudyのGUI — 2026-09-08

曲線入力に計算形状（弦/二次）、体積積分次数、固定幾何の細分段数を追加。
弦を選択中は積分次数/段数を無効化し、二次を選択すると通常Caseへ明示する。
固定幾何Studyを操作一覧へ追加し、既定の比較段数は0,1。
通常のメッシュ細分では二次境界も変わり得ることを説明する。
曲線ピーク未計算の表セルはNaNではなく未評価と表示する。
プレビューは初期分割用の弦であり、選択した二次計算形状とは区別して説明する。

verify_gui.mjs --contour-case examples/curved_ellipse.json --contour-auto yes --curved-fem yes
で通常の入力・エラー保持、曲線設定編集、計算/描画、書出し往復、固定幾何Studyを検査。
対象は合成楕円、幾何次数2、体積積分12、段数1、元メッシュ最大辺長.02 m。
最初の検証は追加ヘルパーのスコープ不具合で停止。修正後の7検査はPASS。
その画面で見つけた旧説明「曲線FEMではありません」を修正。
out/gui-curved-native-accepted-20260908/report.jsonの最終7検査もPASS。
外部通信0、実行中のソース変更なし。curved-controls.png / fixed-study.pngを目視確認。
GUIで実行した固定幾何Studyは520→2080要素、周波数/軸/RF比較PASS。
ブラウザーとローカルGUIサーバーは終了済み。
最初の失敗/中間成功の記録はgui-curved-native-check-20260908 / gui-curved-native-check-final-20260908に保持。
標準271件中269合格・2 skip。今回はUIと検証スクリプトの変更でFEM/RF数式の変更なし。
曲線表面ピーク・鏡映・追加形状を含む総合受入は継続。

## G03固定幾何細分の通常経路 — 2026-09-08

v3 mesh.curved_refinement_levelsを追加。非負整数、既定0、省略時は従来JSONを保持。
明示JSON指定はgeometry_order=2のみ。case_curved_spaceをsolveとreadで共用し、
元メッシュから初期二次幾何を作って指定回数の制限細分を行う。
各段の生成前に4倍後の要素数をcontour_mesh.max_trianglesで検査する。
外部元メッシュでcontour_meshなしの場合の上限は250000。超過は拒否し自動変更しない。
軸子中点は端点平均で表現し、RFの厳密なアフィン軸条件を保持する。

保存は細分段数をCase/field_spaceへ記録し、元弦メッシュを保持する。
readは同じ段数を再構成して全配列・残差/正規化/RFを照合する。
細分後は元弦からの移動量配列を出さず、元曲線パラメータを祖先区間と明記。
段数0の既存保存形式と読込を維持する。

Studyの新種別fixed_geometry_convergenceは
parameter=/case/mesh/curved_refinement_levels、values=[0,1]などの増加非負整数を受け取る。
元メッシュを再読込して点間の完全一致を検査し、固定した二次幾何の比較と記録する。
従来mesh_convergenceの境界再投影を含む比較とは区別する。
GUIフォームは段数を保持するが、選択UIと実ブラウザー受入は次段階。

scripts/validate_curved_study.py --fixed-geometry --out out/validation-g03-fixed-native-study-20260908
で球形段数0→1の保存後比較PASS。元メッシュhash一致、周波数1.6363983269→1.6363973727 GHz。
独立球形参照への相対誤差は周波数9.33016e-7→3.49885e-7、R/Q 2.01474e-4→2.33410e-5。
磁場重なり0.9999999975、軸差2.14213e-4、RFと周波数の全ゲートPASS。
これは当該2段階の検証であり任意形状/任意段数の収束を保証しない。
標準271件中269合格・2 skip、validation-g03-fixed-native-regression-20260908 PASS。
次は曲線GUIの入力/Study/表示の実操作、表面ピークと鏡映。G03と全互換目標は継続。

## G03固定二次幾何の空間細分 — 2026-09-08

curved_refinement.refine_curved_spaceで全参照三角形を4分割し、親写像を子へ制限する。
共有節点は位相上の辺IDで同定し、共有点座標と親係数への補間行の一致を検査する。
親の全P2節点は子の頂点として保持。子中点は親写像で評価し、解析曲線へ再投影しない。
境界タグ・元曲線番号・パラメータ区間を継承し、全子Jacobian・境界・全辺を再検査。
元曲線パラメータは祖先区間の記録であり、解析曲線上への点配置を意味しない。

戻り値はCurvedRefinement(space, prolongation, parent_cells, parent_reference_vertices)。
prolongationは親uを同一の物理場として細分空間へ移す疎行列P。
RestrictedGeometryは元弦からの移動量を捏造せず、既存の再投影候補と別の幾何型を使う。
このAPIは空間/行列の段階。通常Case/solve/save/read/Studyの細分段数接続は未実装。

楕円360→1440要素で写像、ランダムP2場と物理勾配の一致を検証。
境界1/4点が親の二次補間と一致し、解析曲線への再投影点とは異なることを確認。
直線対照の2回細分では軸r=0と磁気対称拘束を厳密に保持。
P^T K_child PとK_parentの相対行列差は積分次数8で1.85819e-11、12で2.29779e-15。
質量行列差は各1.53e-15、1.21e-15。各ゲート1e-10でPASS。
これは同じ場のエネルギー保存の検査であり、固有周波数やRFの離散化誤差の受入ではない。
再現: scripts/validate_fixed_curved_refinement.py --out out/validation-g03-fixed-curved-refinement-20260908。
validation-g03-fixed-curved-refinement-regression-20260908 PASS。
標準268件中266合格・2 skip。通常solve/保存/Studyへの接続と独立物理収束を次に行う。
GUI・表面ピーク・鏡映を含めG03と全互換目標は継続。

## G03曲線Studyの保存比較 — 2026-09-08

compare_refinementを曲線保存解へ接続。最初のメッシュの参照重心を物理座標へ写し、
Jacobian×半径の重みと両解の共通領域で磁場の重なりを評価する。
軸は曲線空間の軸自由度を使い、両軸節点の和集合で区間分割して3点Gauss積分。
積分次数は物理同一性判定から除外するが、betaなど実際の物理/RF条件は保持する。
表面ピークは未評価と明記する。

曲線境界節点を各再メッシュで解析曲線へ置くため、mesh_scaleの変更でも
二次境界自体が変わり得る。これは同じ解析形状の離散化比較であり、
離散幾何を固定したFEM誤差推定とは扱わない。固定二次写像のh細分は残件。

scripts/validate_curved_study.py --out out/validation-g03-native-curved-study-20260908
は球形R=.08 m、幾何/場次数2、弦許容差.0008 m、最大辺長.02→.01 m。
保存後の比較312点、磁場重なり0.9999999977、軸差2.13699e-4、全比較ゲートPASS。
独立球形参照に対する周波数誤差9.33016e-7→5.81020e-8、
R/Q誤差2.01474e-4→1.51583e-5。両段階の全RFゲートもPASS。
最初の出力名は既存ディレクトリのため拒否され、新規名で実行。既存結果は未変更。
標準264件中262合格・2 skip、validation-g03-curved-study-regression-20260908 PASS。
次は固定離散幾何の細分・GUI・表面ピーク・鏡映。G03/全目標は継続。

## G03曲線保存プローブと描画 — 2026-09-08

曲線境界をzの極値で単調区間へ分け、二分法で半径プローブの外側交点を計算。
膨らみ・折返しの複数交点・接点・同一平面内の半径極値を検証。
保存CSVプローブとplotを接続し、領域の隙間は曲線逆写像のinside/NaNを保持。
境界線は各二次辺17点、色/等高線は既存の4直線表示三角形による近似。
球形保存解の実描画 out/g03-curved-sphere-plot-20260908.png を目視確認。
標準261件中259合格・2 skip。その後追加の保存プローブを含む5件も合格。
validation-g03-curved-queries-20260908 PASS。FEM/RFの数式・係数・許容差は変更なし。
次は曲線解のStudy/GUI経路と表面ピーク・鏡映。G03/全互換目標は継続。

## G03通常曲線Caseと保存往復 — 2026-09-08

v3 mesh.geometry_order=2 / solver.element_order=2 / quadrature_order既定8を追加。
通常solve・RF・FieldSamplerへ接続。curved_saved.pyで元メッシュ/全曲線配列保存と
空間再構成・幾何照合・K/M再組立て・正規化/残差/RF照合。固有値再計算なし。
VTKは4直線表示三角形、計算用曲線幾何はNPZ。保存完了/上書き禁止を継承。
GUIフォーム次数保持のみ追加、実ブラウザー未検証。plot/鏡映は明示的に未対応拒否。
標準259件中257合格・2 skip、validation-g03-native-storage-regression-20260908 PASS。
validation-g03-native-storage-20260908/comparison.jsonは保存後の球形全ゲートPASS。
次は曲線解の描画/保存プローブ/Study/GUIと表面ピーク・鏡映。G03/全目標継続。

## G03曲線物理座標プローブ — 2026-09-08

curved_sampling.QuadraticLocator/CurvedFieldSamplerで物理座標から逆写像。
減衰Newton＋参照三角形4分割のBezier包絡。外部証明時だけNone/NaN、予算不足はUNVERIFIED。
曲線の膨らみ・境界/軸/寸法変換と楕円10要素の場一致を検証。
out/validation-g03-curved-probe-final-20260908/comparison.jsonは球形物理点/全軸/既存RF等PASS。
物理点H誤差6.26e-5、E誤差1.15e-3、軸Ez2.14e-4。
標準255件中253合格・2 skip、validation-g03-probe-regression-20260908 PASS。
次は通常Case幾何次数と入力/保存/再読込。ピーク/鏡映/Study/GUIも残り、全目標継続。

## G03曲線RF積分 — 2026-09-08

curved_rfに壁H²弧長積分、軸P2電圧、Q0/G/RQ等を接続。
PECのみ損失、R01 overrides保持。軸中点は端点平均との完全一致を要求。
直線3境界条件と部分電圧/位相設定、独立円柱壁積分を検証。
out/validation-g03-curved-rf-final-20260908/comparison.jsonは球形全RFゲートPASS。
R/Q誤差2.01e-4、壁損失7.19e-6、壁積分8/12差2.22e-16。
標準252件中250合格・2 skip、validate PASS。
次は物理座標逆写像/プローブと通常入力/保存/再読込。ピーク/鏡映/Study/GUIも残る。
G03と全互換目標は継続。

## G03曲線解と体積場 — 2026-09-08

curved_solution.solve_curvedで昇順固有値・残差・質量直交性・指定Uを接続。
fields_in_cellは参照座標を受け、曲線写像の物理勾配からH/Er/Ezを評価。
直線3境界条件との一致、曲線上の物理線形場を検証。
validate_curved_fields.py: out/validation-g03-curved-fields-final-20260908/comparison.json PASS。
球形H誤差7.27e-5、E誤差1.12e-3、各エネルギー0.5 J。
標準250件中248合格・2 skip、validation-g03-curved-solution-20260908 PASS。
次は曲線壁/軸RF・物理座標逆写像、通常入力/保存/再読込/GUI。G03/全互換目標は継続。

## G03全体曲線空間/行列 — 2026-09-08

curved_space.CurvedSpaceへ共有/向き/境界incidence/連結/Euler=1を集約。
内部を含む全二次辺の交差を凸包候補＋既存離隔検査で確認。
assemble_curvedで局所行列をCSR化。直線P2との一致・破損/内部交差拒否を検証。
validate_curved_space.py: out/validation-g03-global-curved-space-20260908/comparison.json PASS。
球形周波数誤差9.33e-7、積分次数8/12差約6e-15。場/RF精度とは別の限定受入。
標準248件中246合格・2 skip、validation-g03-space-regression-20260908 PASS。
次は曲線解の正規化・場・RFと入力/保存/再読込。G03/全互換目標は継続。

## G03二次境界の検査 — 2026-09-08

quadratic_boundaryで二次Bezier境界の単一閉サイクル・折返し・全辺対離隔を検査。
隣接辺は共有点近傍の単調投影と残区間対の分割検査。丸め/予算未確定はUNVERIFIED。
楕円32辺/双曲線28辺PASS。端点が単純でも曲線交差する例と隣接辺の再交差を拒否。
共有候補の最後へ接続しboundary_checkを保持。
次は元の円板位相・共有辺・全域Jacobian・単純境界を集約した全体空間と行列。
標準245件中243合格・2 skip、validation-g03-boundary-final-20260908 PASS。
G03の製品solve/保存/場/RFと全互換目標は継続。

## G03共有二次幾何候補 — 2026-09-08

弦ごとの元曲線fraction区間を追加し始点回転/保存へ保持。
curved_mesh.curve_geometry_candidateで境界頂点/共有辺中点を元曲線へ移動。
内部点保持、共有整合/軸固定、全要素Jacobian/半径検査。独立面積/体積が弦誤差の1/10未満。
双曲線の粗い弦4 mm/細かい辺5 mmは要素89で曲線化反転を拒否し、元メッシュ不変。
JacobianはBernstein下界で先に判定し、下界不十分時だけ極値候補を検査。
次は全体二次境界の交差/適合性と全体空間/行列。候補型はsolve/保存済み解へ未接続。
標準240件中238合格・2 skip、validation-g03-shared-geometry-20260908 PASS。
G03と全互換目標は継続。

## G03二次写像と局所行列 — 2026-09-08

quadratic_geometry.QuadraticTriangleで6節点写像と全域det J最小値候補を検査。
節点だけ正の反転反例を拒否し、面積/回転体体積/物理勾配を検証。
curved_fem.mapped_element_matricesで局所P2行列を積分、一定/線形場と直線極限を検証。
CURVED_ELEMENTS.mdへ全体共有性/入力/保存/場/RF/Study/GUIの未接続契約を記録。
次は元曲線パラメータ区間と共有二次幾何節点・全体適合性。
標準237件中235合格・2 skip、validation-g03-quadratic-map-20260908 PASS。
局所コアのみでG03/全互換目標は未完、継続。

## G03球形の独立電磁場参照 — 2026-09-08

analytic_sphere.SphereTMで球形PECの正則l=1,m=0 TM参照を独立実装。
DLMF R28の関数定義からPEC条件/正規化/RFを導出。中心/接線場/2Dエネルギー/有限差分curlを検証。
validate_sphere.py: out/validation-g03-sphere-reference-20260908/comparison.json。
弦0.8/0.2 mmはFAIL、0.05 mmはf/場/軸/RQ/G/壁損失の全ゲートPASS。
標準230件中228合格・2 skip、既存validate PASS。次は曲線要素写像と正Jacobian/積分/場/RF/保存の設計。
接線構築/旧形式対応と全互換目標も継続。

## G03双曲線の総合経路 — 2026-09-08

双曲線例curved_hyperbola.jsonを追加。独立z積分の面積/体積、弦体積差の正符号/減少、
両端×電気/磁気4鏡映・別全領域solve・保存再読込、寸法3倍のf/RQ/G/TTF不変量を検証。
直角rotationを完全一致時のみ座標入替えとして扱い、接続の丸め誤差を修正。
幾何/FEM最終比較PASS: out/validation-g03-hyperbola-refinement-20260908/summary.json。
実ブラウザー5検査PASS: out/gui-g03-hyperbola-browser-20260908/report.json。
標準226件中224合格・2 skip、validate PASS。
次は独立の電磁場参照と曲線FEM設計/実装。接線構築/旧形式対応と全互換目標も継続。

## G03メッシュ停滞解消と独立細分 — 2026-09-08

低品質内点に8方向×4段階の候補を追加し、平均位置で停滞する独立矩形扇を検証。
境界/正面積/面積/回転体体積/サイズ制約を保持。楕円の品質停滞を解消。
out/validation-g03-directional-smoothing-20260908/summary.jsonは幾何/FEM最終比較PASS。
幾何の粗い比較はFAILを保持。最細メッシュ29007三角形・最小角10.1878度。
標準222件中220合格・2 skip、validation-g03-directional-regression-20260908 PASS。
次は双曲線等の総合受入と独立の電磁場参照、曲線FEM/接線構築/旧形式対応。
G03と全互換目標は継続。

## G03メッシュ停滞の切分け — 2026-09-08

対角線交換に明示max_edge_mを追加し、サイズ内の長くなる交換を許可。
独立四角形で角度10.49→24.78、面積/体積/境界不変。品質生成へ接続。
標準221件中219合格・2 skip、validate PASS。
out/validation-g03-bounded-flips-20260908/summary.jsonはFEM PASS、幾何列は依然品質FAIL。
1反復後の最悪三角形は軸上2点とr=.0002188 mの内点。次は内点移動候補を切分ける。
G03と全互換目標は継続。

## G03の独立細分列 — 2026-09-08

幾何/FEM独立列をscripts/validate_curved_refinement.pyで再現。
24反復の幾何列は0.125 mmで最小角7.60043279度のまま品質FAIL、数値UNVERIFIED。
FEM列は弦0.03125 mm固定で20/10/5 mmの両比較PASS。
out/validation-g03-separated-refinement-round24-20260908/summary.jsonに保存。
次は幾何列のメッシュ品質停滞を再現し、独立幾何不変量を保って修正する。
標準220件中218合格・2 skip、validate PASS。G03全体/全互換目標は継続。

## G03の解析曲線GUI — 2026-09-08

元曲線保持・弦誤差/分割上限編集・幾何誤差表示・P2計算/保存再読込を接続。
実ブラウザー5検査PASS: out/gui-g03-curves-browser-20260908/report.json。
標準220件中218合格・2 skip。次は独立した幾何/FEM収束と双曲線等の総合受入。
曲線FEM/接線構築/旧入力対応を含むG03と全互換目標は継続。

## G03の幾何/FEM Study分離 — 2026-09-08

curved_contourのgeometry_convergenceを追加。弦誤差だけを変更し元曲線/FEM設定を保持。
mesh_scaleは弦Contourを保持し最大辺長を変更。Study各点へ幾何誤差記録を転記、P2表示修正。
標準219件中217合格・2 skip、validation-g03-curved-study-20260908 PASS。
examples/curved_ellipse.jsonを追加。study-g03-ellipse-geometry-20260908は操作成功だが数値判定FAIL。
弦体積誤差は減少。次はGUI元曲線/弦誤差/表示接続と、G03総合の幾何/FEM収束を続ける。
曲線FEM/接線構築/旧入力対応も残り、全互換目標は継続。

## G03の曲線鏡映/FEM — 2026-09-08

CurvedContour.reflectedで元曲線を鏡映/逆順接続し、全閉輪郭を再検証。
reflect_solutionへ接続して全Caseの弦Contourを再導出。楕円の両端×電気/磁気4条件で
解析面積/体積/U2倍、全メッシュ別solveのf/RQ/G一致、保存再読込を検証。
標準218件中216合格・2 skip、validation-g03-curve-reflection-20260908 PASS。
次はGUI/Studyへcurved_contourと幾何/FEM細分を接続、双曲線等の追加総合受入も残る。
曲線FEM/接線構築/旧入力対応と全互換目標は継続。

## G03の解析回転体体積 — 2026-09-08

curve_moments.pyで-π∮r²dzを線分/楕円/双曲線の解析指数積分として実装。
CurvedContour.volume_m3と保存geometry_approximationに解析体積・弦体積・差を追加。
円柱/円錐台/楕円体、双曲線の別変数積分、回転開弧の細分積分で独立検証。
標準217件中215合格・2 skip、validation-g03-analytic-volume-20260908 PASS。
次は元曲線の鏡映とGUI/Study連携。曲線FEM/接線構築/旧入力対応・全互換目標は未完。

## G03の元曲線Case/保存 — 2026-09-08

v3 geometry.type=curved_contour、曲線列のstrict入出力と弦誤差/全体分割上限をCaseへ追加。
Case.contourは導出、同時指定時は完全一致を要求。保存に弦表現/元曲線対応/調整/面積差を記録。
P2再読込と再計算係数が一致。標準214件中212合格・2 skip、validation-g03-curved-case-20260908 PASS。
解析曲線の鏡映は明示拒否。GUI/Studyは未移行なので次に元曲線/解析体積と併せて接続する。
Case置換で弦誤差を変えるときはcontour=Noneを指定して再導出。
曲線FEM、接線構築、旧入力対応と全互換目標は未完。

## G03の弦Contour変換 — 2026-09-08

CurvedContour.linearize→ChordApproximationを追加。タグ/元曲線対応・端点調整・解析面積差を保持。
端点調整を誤差予算から差引き、全体分割数上限とContour再検証・向き検査を行う。
半楕円の面積/独立楕円体体積収束、タグと元曲線不変を検証。
標準212件中210合格・2 skip、validation-g03-chord-contour-20260908 PASS。
次はCaseへ元曲線/弦誤差を保持する契約と保存、一般の解析体積。曲線FEM等は未完。
G03と全互換目標は継続。

## G03の単一曲線閉輪郭 — 2026-09-08

curved_contour.CurvedContourを追加。軸鎖/タグ/範囲/全辺対/正面積を検査し、
検査用二分で軸+半楕円の2辺形状も扱う。位置許容差は軸長1e-10以下、元形状は修復しない。
半楕円解析面積/寸法変換・分割軸混在タグ・交差/不正タグ/隙間を検証。
標準210件中208合格・2 skip、validation-g03-closed-curves-20260908 PASS。
次は弦近似Contour変換と幾何誤差/体積、Case元曲線保持。曲線FEM/旧入力対応も未完。
G03・全互換目標は継続。

## G03の隣接曲線検査 — 2026-09-08

directional_derivative_boundsとcertify_adjacent_curvesを追加。共有端点近傍は共通方向の
厳密な投影単調性、残り区間対は通常の離隔検査。許容差内の逆順重なりをUNVERIFIEDで拒否。
中心差分・線分/楕円・直角・逆向き・探索上限を検証。標準207件中205合格・2 skip、
validation-g03-adjacency-20260908 PASS。次は閉輪郭/軸連続性/辺タグ/全辺対/モーメント統合。
Case/GUI/曲線FEMは未接続、G03と全互換目標は継続。

## G03の区間包絡と離隔 — 2026-09-08

curve_bounds.pyに線分/楕円/双曲線の座標極値と余裕付き包絡箱、区間対細分の離隔検査を追加。
距離不足FAILと探索上限UNVERIFIEDを分離。共有端点を持つ隣接辺にはまだ適用しない。
解析極値・軸横切り・既知距離・交差/接触・同心円弧の検証が合格。
標準205件中203合格・2 skip、validation-g03-bounds-20260908 PASS。
次は閉輪郭への統合、共有端点近傍と非隣接辺の検査、軸/タグ契約。
Case/GUI/曲線FEM・旧入力対応は未完、全互換目標は継続。

## G03の線分・接線接続検査 — 2026-09-08

LineSegmentとcheck_curve_joinを追加。端点SI許容差と有向接線角を別判定し、形状を修復しない。
G1とC1/曲率連続を区別。線分↔楕円↔双曲線接線、逆向き/隙間/角/元形状不変を検証。
標準202件中200合格・2 skip、validation-g03-joins-20260908 PASS。
次は曲線区間の位置/誤差包絡、閉輪郭の交差/軸/隙間検査。
Case/GUI/曲線FEMと旧入力対応は未完、G03と全互換目標は継続。

## G03の双曲線弧コア — 2026-09-08

conics.HyperbolaArcに有限区間/枝±1、点/接線/曲率/最小半径/面積寄与/弦近似を追加。
両枝の陰関数・勾配直交・頂点半径・反転/面積・寸法と誤差を検証。
標準199件中197合格・2 skip、validation-g03-hyperbola-20260908 PASS。
次は線分/楕円/双曲線の接線接続契約と、曲線境界の交差/軸/隙間検査へ進む。
旧入力対応、Case/GUI/曲線FEMは未接続。G03と全互換目標は未完。

## G03の楕円弧コア — 2026-09-08

CONIC_GEOMETRY.mdで幾何/曲線FEMを分けた仕様段階を定義。
conics.EllipseArcに回転楕円の点/接線/曲率/最小半径/面積寄与/誤差上限付き弦近似を実装。
陰関数・直交・円極限・回転/反転・四分面積・寸法変換で独立検証。
標準196件中194合格・2 skip、validation-g03-ellipse-core-20260908 PASS。既存mode/hash不変。
次は双曲線プリミティブと接線接続契約、曲線の交差/軸/隙間検査へ進む。
Case/GUI/曲線FEM未接続、G03および全互換目標は未完。

## G02受入完了 — 2026-09-08

GENERAL_MESH.md末尾で全要件/実装/証拠を照合しG02.S/I/Vを受入。
実Chrome初回で結果表示のprofile前提を検出し、長さ取得/掃引/バンドを修正。
再検証5操作PASS、外部通信0、サーバー停止済み。細分Studyが最大辺長を変更しない問題も修正。
標準192件中190合格・2 skip、validation-g02-gui-fixed-20260908 PASS、旧mode/hash不変。
次はG03.S（円/楕円/確認済み双曲線、接線・曲率・丸め、幾何と曲線FEMの分離）へ進む。
C00未確認と残り親課題・全互換目標は継続。

## G02の自動solve/CLIとGUI欄 — 2026-09-08

make_meshをCase.contour_meshへ接続、未指定時は明示拒否を維持。自動/明示mesh一致、
保存Case再計算係数一致を検証。実CLIの合成folded例も全RF/hash/係数完全一致。
GUIに4設定欄とSI保持を実装し、contourでnr/nz/triangulationを無効化。
標準191件中189合格・2 skip、validation-g02-auto-20260908 PASS、JS構文PASS。
次は実Chromeでcontour読込→設定編集→solve→出力/再読込を検証し、G02全要件を照合。
examples/contour_folded.jsonは粗い操作例。全互換目標とG02は継続。

## G02の方式判断とCase制御契約 — 2026-09-08

ADR-017で測定に基づき自前品質判定方式を選択。ContourMeshControlsとv3
mesh.contour_meshへ最大長/最小角/要素・反復上限を追加しstrict解析・保存往復を検証。
標準191件中189合格・2 skip、validation-g02-controls-20260908 PASS。
次はmake_meshが設定から自動生成する接続とCLI/保存再実行、GUIの欄/読込保持/実操作。
現時点make_meshのcontourはまだ拒否する。新設定をGUIcollectはまだ保持しないので要対応。
G02全体・全互換目標は未完。

## G02の非円筒独立照合 — 2026-09-08

compare_contour_ngsolve.pyを追加。円錐台はPASS、折返しの初回周波数未収束FAILを残し、
.0015/.00075/.000375の双方追加細分でPASS。CONTOUR_RF_COMPARISON.mdに閾値/数値/費用を記録。
最終差f1.34e-5/RQ1.56e-5/G1.54e-5、内部H/EもPASS。最細NG36万DOF/84秒。
標準189件中187合格・2 skip、参照専用7件PASS。全ジョブ完了。
検証環境/tmp/superfish-g02-reference（隔離、NGSolve6.2.2606/NumPy2.5.3/SciPy1.18.1）。
次は方式ADRと製品のサイズ/品質/停止上限のCase契約、保存/CLI/GUI接続へ進む。
一般輪郭make_meshはまだ明示拒否。表面角ピークは未受入、G02・全互換目標は継続。

## G02の点追加と品質判定 — 2026-09-08

quality_contour_meshで悪い要素の最長辺へ境界を含む点追加、組替え/移動を反復。
目標最小角を全要素で達成したときだけ返し、反復/要素上限は明示失敗する。
測定mesh-g02-quality-20260908: 幅0.05は831要素12.61度、0.01は2336要素10.03度。
幅1e-5は4000要素上限でFAIL。標準188件中186合格・2 skip、validation-g02-quality-20260908 PASS。
次は独立非円筒RF参照との収束、方式/資源判断、Caseサイズ品質契約と製品経路を進める。
G02全体および全互換目標は未完。make_meshのcontour公開はまだ拒否のまま。

## G02の内部頂点移動 — 2026-09-08

smooth_contour_interiorで境界を固定し、関係要素の最小qを改善する内部点移動を追加。
正の向き・サイズ・タグ・独立モーメント/再現性を検証。標準187件中185合格・2 skip、
validation-g02-smoothing-20260908 PASS。幅0.5で最小角14.0→15.6度、幅1e-5は
0.000286→0.000368度に留まる。次は境界点追加を含む配置/必要要素数/品質拒否条件を評価。
G02の製品契約/自動solve/独立非円筒RFも未完。全互換目標は継続中。

## G02の内部辺組替え — 2026-09-08

improve_contour_anglesで境界/頂点を保ち2要素の最小角が改善する内部対角辺だけ交換。
最大長/局所サイズ保持、幾何モーメント、再現性/固定点を検証。標準186件中184合格・
2 skip、validation-g02-flips-20260908 PASS。測定mesh-g02-flips-20260908では品質中央値は
改善したが狭い経路の最小角は不変。次は頂点配置/追加方式と必要要素数を評価する。
Caseサイズ契約/自動solve/独立非円筒RF受入も残り、G02・全互換目標は未完。

## G02の適合細分化と品質測定 — 2026-09-08

refine_contour内部APIで共有中点/最長辺閉包/タグ継承、全域・境界・角サイズと停止上限を
実装。独立面積/体積・局所タグ長とサイズ達成が合格。標準185件中183合格・2 skip、
validation-g02-refinement-20260908 PASS。measure_contour_mesh.pyの測定で狭い経路の
最小角は細分しても改善しない（幅1e-5で0.000286度）。次は品質改善方式と必要要素数・
失敗条件/依存判断を測定。Case全域サイズ契約/自動solve/独立非円筒RF参照も残る。
G02は未受入、全互換目標は継続。

## G02の初期三角形分割 — 2026-09-08

GENERAL_MESH.mdで段階と受入条件を定義。contour_mesh.triangulate_contourは
全頂点/辺タグを保つ初期分割を実装し、独立矩形/円錐モーメント・狭い経路を検証。
標準182件中180合格・2 skip、validation-g02-initial-20260908 PASS。
make_meshの一般輪郭はまだ明示拒否。次はタグ継承を保つ細分化、全域/局所サイズ契約、
品質改善と停止制限を実装・測定する。G02.S進行中/I部分/V未受入、全互換目標は継続。

## G01受入完了 — 2026-09-08

GENERAL_CONTOUR.md末尾で要件/実装/証拠を照合しG01.S/I/Vを受入。
一般輪郭と混在タグのGUI実ChromeもPASS。最終標準178件中176合格・2 skip。
能力表はcontour対応と外部mesh必須を別表示。次はG02.Sの一般輪郭自動メッシュ方式・
品質検査・依存採用判断を仕様化し、実装/検証へ進める。全互換目標は継続中。

## G01の後処理点検 — 2026-09-08

一般輪郭のradial probe/plotは領域外の隙間をNaNで表現。CSVにinsideと
metadata規約を追加し、矩形分割の既知ギャップで検証。円筒参照/バンド/反復組立は
適用外を明示拒否。標準178件中176合格・2 skip、validate PASS。
次は混在タグGUIの実ブラウザ確認とG01全要件の受入照合。自動meshはG02。

## G01の局所端面タグ — 2026-09-08

混在端面をCaseの導出mixed要約で保持し、外部meshは辺タグを正として検証。
P2局所拘束と全面PEC/部分磁気/全面磁気の変分周波数順序、鏡映拒否が合格。
178 tests中176合格・2 skip、標準validate PASS。
GUI混在要約を実装・構文確認済み。次は混在GUIの実ブラウザ確認と、G01全経路の
未対応profile前提（解析比較/半径プローブ/組立等）を点検し、適切に移行/拒否して受入する。

## G01の実ブラウザ往復 — 2026-09-08

一般輪郭のファイル読込/8頂点表示/Case出力/再読込が実ChromeでPASS。
端面欄の無視される編集を修正し、読込辺タグの無効化表示にした。
証拠gui-g01-browser-final-20260908/report.json、標準validate PASS。サーバー停止済み。
次は局所端面タグをCaseで制限している箇所を整理し、G01仕様/証拠を最終照合する。
G01全体は未受入。

## G01の一般輪郭プレビュー接続 — 2026-09-08

gui.preview_documentを追加し、閉輪郭/タグ/面積/体積を返す。web/app.jsは
読込contourを保持し閉多角形として描画。ファイルによる形状編集を画面で説明する。
API往復・解析モーメントとJS構文は合格。次は実Chromeでcontourファイル読込・
プレビュー・Project/Case出力・再読込を検証する。局所タグ制限整理も残る。G01未完。

## G01のCase/FEM鏡映 — 2026-09-08

reflect_solutionでContour.reflectedを全Caseへ渡し、P2外部meshの
全領域再計算とf/RQ/損失を比較した。z折返しの両端×電気/磁気4条件PASS。
標準176件中174合格・2 skip、validate PASS。
次はgui.pyの/api/preview付近のlinearize_profile前提とweb/app.jsの形状保持を
一般輪郭へ移行する。局所端面タグの暫定制限も整理し、G01受入へ進む。

## G01の外部メッシュ接続 — 2026-09-08

mesh_from_dictを一般輪郭へ対応。辺単位タグ/投影区間の完全被覆、面積/接続/軸を検査。
矩形分割のz折返し外部meshでP2 solve→保存→読込が合格。
176 tests中174合格・2 skip、標準validate PASS。
次はプレビューと鏡映Case/FEMをprofile前提から移行し、局所端面タグの制限も整理する。
自動生成はG02まで未対応。G01全体は未受入。

## G01のCase v3連携 — 2026-09-08

Case((),contour=...)とv3 contour geometryを追加。profileは偽造せず空、
length/areaは輪郭から取得。175 tests中173合格・2 skip、標準validate PASS。
make_meshはG02、mesh_from_dictはG01検証移行待ちとして明示拒否中。
次は外部meshの境界検証・プレビュー・鏡映Case/保存を移行する。
同端面内の混在タグはCaseで暫定拒否。局所タグ契約も移行時に解決する。G01未完。

## G01の変換・鏡映 — 2026-09-08

Contour.from_profileとreflectedを実装。独立円錐台体積・z折返し鏡映の
面積/体積2倍を検証。標準174件中172合格・2 skip、validate PASS。
次はCase v3のcontour geometryを追加し、profile前提の長さ/境界/プレビュー/保存を
移行する。一般輪郭の外部mesh検証もG01対象。自動メッシュはG02まで未対応と明示する。

## G01の一般輪郭コア — 2026-09-08

GENERAL_CONTOUR.mdへ仕様を追加。contour.Contourでz折返し多角形の
厳密検証・向き/始点正規化・面積/体積を実装。矩形分割・円錐・寸法変換で独立検証。
172 tests中170合格・2 skip、標準validate PASS。
次は既存profile変換・鏡映・Case v3統合・外部mesh検証を進める。
G02の一般輪郭メッシュ生成は別段階で、現行R(z)生成へ黙って通さない。G01未完。

## N02受入完了 — 2026-09-08

HIGH_ORDER_FIELDS.md末尾で仕様・実装・証拠を照合しN02.S/I/Vを受入。
能力表・現在仕様をP1/P2へ更新。標準169件中167合格・2 skip、総合13チェックPASS。
次はG01.S（z折返し可能な単一外周・軸閉領域・厳密な不正輪郭拒否）から実装/検証へ進む。
G02の任意輪郭メッシュは別依存段階。C00の未確認行とC03/C04、他の全親課題は継続対象。

## N02の総合数値検証 — 2026-09-08

validate_quadratic_fields.pyで独立J0/J1/cos/sin場・ピーク・RF・同DOF比較を検証。
13チェックPASS、証拠quadratic-fields-n02-final-20260908/fields.json。
Job取込再実行の係数/RF一致と寸法スケーリングも追加。標準169 tests中167合格・2 skip。
次は能力表・PHYSICS/README/進捗のP1限定記述を現実装へ整え、N02.Sの全移行箇所・
受入条件と証拠を照合してN02を受入する。全32項目・33親課題の目標は引き続き未完。

## N02のGUI次数選択 — 2026-09-08

P1/P2選択、v3/model生成、Project読込往復を接続。実Chromeの4操作と
標準validate PASS。証拠はgui-n02-order-browser-final-20260908/report.json。
今回のGUIサーバー停止済み。次は能力表・現在仕様の記述を更新し、
Bessel全場/ピーク/誤差対DOF/Job再実行を総合検証してN02全体を受入する。

## N02のCase/CLI次数 — 2026-09-08

v3 solver.element_orderで1/2をstrict受理。solveが次数を選択し、Project・保存・
再読込・再実行まで保持。旧Case研究P2保存は次数2をCase/鏡映元へ明示する。
167 tests中165合格・2 skip、標準validate PASS、P1 mode/hashは不変。
次はGUIの次数選択と入出力保持、能力表/文書を更新し、総合Bessel場・ピーク・
誤差対DOF/半全・Job再実行を検証する。N02全体は未完。

## N02のバンド・細分比較 — 2026-09-08

analyze_bandはP2セル中心と軸停留点、compare_refinementは高次Hと
P1/P2差の正確な軸積分を使用する。既定read_solutionでP2を読める。
165 tests中163合格・2 skip、標準validate PASS、P1のRF全量/hashは不変。
次はCase/Project/CLI/GUIへ次数を保持して再実行を可能にする。
Job取込は保存P2を保持できるが、Case次数がまだ無いため再実行の次数保持は未完。
Bessel場/ピーク/誤差対DOFの総合証拠を整え、N02全体を受入する。

## N02の保存P2解析/probe — 2026-09-08

export_radial_probeとcompare_pillboxが高次reader/samplerを使用する。
円筒解析の軸L2はP2軸辺の8点Gauss評価へ対応。3モード同定・全ゲート、
元解とのCSV場一致を検証。164 tests中162合格・2 skip、標準validate PASS。
次はanalyze_bandとstudiesの高次場/軸評価を移行し、既定読込の暫定拒否を撤去。
Case/CLI次数指定と総合Bessel/ピーク/DOF比較も残る。

## N02の保存P2描画 — 2026-09-08

plot_modeを検証済みreader/display_fields/高次samplerへ移行。保存P2から
電場・磁場・軸・radialを描画し、元解とのprobe一致と未完了拒否を検証。
163 tests中161合格・2 skip、標準validate PASS。PNG目視証拠は
out/p2-plot-20260908/mode2.png。次はsaved解析/probe・studiesへ高次場を渡し、
read_solutionの既定拒否を撤去する。Case/CLI次数と総合N02検証も残る。

## N02のP2保存・明示読込 — 2026-09-08

save_runでP2全係数/4空間配列/field_space宣言を保存。read_solutionの
allow_quadratic=Trueで再構成空間との一致を検証して読める。
162 tests中160合格・2 skip、標準validate PASS、P1のRF全量/hashは不変。
次はsavedのprobe/比較/バンド、visualize、studiesへ空間を渡す。移行完了後に
読込の暫定制限とplot_modeの拒否を撤去する。Case/CLI次数指定も残る。N02未完。

## N02の表示用分割・VTK — 2026-09-08

display.pyへP2の4分割表示データを追加し、write_vtkに接続。
二次多項式の場・面積・VTK値を検証。161 tests中159合格・2 skip、標準validate PASS。
P1のRF全量/hash/VTKバイト列は不変。次はsave_run/read_solutionへ次数・全係数・
接続情報を保持して移行し、plot_modeと追跡へつなぐ。N02全体は未完。

## N02のP2鏡映 — 2026-09-08

reflect_solutionを全中点の偶奇写像へ拡張。両端×電気/磁気対称について
独立全領域solveと周波数/RQ/損失の一致、場の偶奇、U/損失2倍を確認。
159 tests中157合格・2 skip、標準validate PASS、P1のRF全量/hashは不変。
次はP2保存/再読込/表示/追跡とBessel場・ピーク/誤差対DOF証拠を進める。
HIGH_ORDER_FIELDS.mdに記録。N02全体の受入とCase/CLI次数公開は未完。

## N02の表面積分とRF量 — 2026-09-08

quadratic_rf.surface_integrals_p2を実装し、rf.quantities/cell_fieldsへP2を接続。
既知多項式の損失/内部極値、3モードのRQ/G収束・Uスケーリングを検証。
158 tests中156合格・2 skip、標準validate PASS。P1 mode全量とhashは不変。
次はBessel全場/ピーク/誤差対DOFの証拠とP2保存・再読込・鏡映/描画/追跡統合。
HIGH_ORDER_FIELDS.mdを参照。Case/CLIのP2指定はまだ未公開でN02は未完。

## N02の軸電圧積分 — 2026-09-08

quadratic_rf.pyへ二次軸場の複素電圧/絶対値積分とP2解アダプタを追加。
低beta・部分区間・符号反転を独立積分で検査。155 tests中153合格・2 skip、
標準validate PASS。HIGH_ORDER_FIELDS.mdに式と証拠を記録した。
次はPEC表面損失/極値、quantities/cell_fields統合、その後保存/描画/鏡映/追跡。
N02全体と継続目標は未完。

## N02の場評価を開始 — 2026-09-08

HIGH_ORDER_FIELDS.mdにN02仕様と全移行箇所を記録。FieldSamplerは明示したP2空間の
6係数を保持し、from_solutionで次数整合を検証する。独立多項式/軸極限テスト合格。
152 tests中150合格・2 skip、標準validate PASS、P1の周波数/RFとhashは不変。
次は二次軸電圧の安定積分・PEC辺積分/極値。その後RF/保存/表示/鏡映/追跡を統合する。
N02は実装途中であり、全体の受入は未完。

## N01のP2固有値コア — 2026-09-08

N01.S/I/Vを受入。QUADRATIC_ELEMENTS.mdに独立積分・収束・再現手順を記録。
研究用high_order.solve_p2のみ公開し、P1用の場/RF/保存/鏡映はP2解を明示拒否する。
150 tests中148合格・2 skip、標準validate PASS。既存の円筒/成形セルのmode全量は直前と一致。
次はN02.Sで高次係数を保つ場評価・RF積分・保存・描画・鏡映・追跡を設計し、実装/検証する。
32項目・33親課題全体の目標は継続中。以下の古い開始点は履歴として読む。

## R01の加速量規約 — 2026-09-08

R01.S/I/Vのnative範囲を完了。ACCELERATING_CONVENTIONS.mdに仕様・再現・失敗履歴を記録。
v3 rfのactive_length_m、voltage_interval_m、phase_origin_mを追加し、旧既定値/hashを保持。
解析比較、鏡映写像、CLI/GUI/保存を更新。143 tests中141合格・2 skip、標準validate PASS。
最終GUIはout/gui-r01-browser-accepted-20260908、数値はout/validation-r01-final-20260908。
初回の区間外掃引拒否と撮影待ちFAILを保持する。旧入力の任意ZCTR等はまだ受け入れない。
次はN01.SのP2要素/解契約→N01.I/V、N02の場/RF/保存・表示への移行を進める。
N02受入まで高次RFを製品公開しない。C00の未確認行とC03/C04も継続対象。

## O01の保存完了管理 — 2026-09-08

O01.S/I/Vのローカル契約を完了。SAVE_COMPLETION.mdに仕様と受入を記録した。
save_runは出力先を排他予約し、内部一時領域で全ファイルを作り、非置換hard linkで
完了マーカーを最後に公開する。read_solutionは全必須出力のhashを検査し、旧形式も読む。
Job取込の外部meshコピー漏れを修正し、新しい直接保存の完了証拠を区別して保持する。
137 tests中135合格・2 skip、out/validation-o01-accepted-20260908がPASS。
R01の加速量規約とN01/N02、C00調査、C03/C04は未完。次はR01.Sから進める。

## C02限定AF読込の受入 — 2026-09-08

LEGACY_INPUT.mdのC02初期部分集合を仕様・実装・検証まで完了。
import-afはnr/nz/modes/導電率/正規化を明示必須とし、DX/FREQ等の無適用を診断に記録する。
単一REG・全PEC・軸接続真空TM・直線/段差/NT4/5短円弧のみ受理。その他は位置付き拒否。
128 unittest中126合格・2 skip、out/validation-c02-final-20260908がPASS。
保存AF2形状からの新規NG4計算と既存SFO照合はout/c02-import-acceptance-20260908。
新規旧計算・場全体/表面ピークの受入ではない。C00/C03/C04と汎用旧入力は未完。
次はR01の加速量規約、またはO01の直接保存完了管理を仕様化して実装する。

## C01共通契約の受入 — 2026-09-07

C01.S/I/V完了。仕様・実行証拠・再現はMODEL_CONTRACT.md。
v3 modelとcapabilities/migrate-caseを実装し、v1/v2のhashと既存解を保持した。
Project/Study/GUI/鏡映/外部meshの保存でmodelを失わず、追加物理は計算前に拒否する。
122 unittest中120合格・参照環境専用2 skip、標準validateとChrome 8操作検査PASS。
最終証拠はout/validation-c01-final-20260907、out/gui-c01-browser-final-20260907。
次はC02.SでDXのNG指定への写像、FREQ等の探索指定、未指定導電率/正規化の扱いを
明記し、確認済みAF部分集合のstrict読込と変換記録を実装する。C00調査は未完了のまま継続。

## 互換開発goal開始 — 2026-09-07

ユーザーが32対応項目・33親課題の完遂をgoalに指定。作業checkoutは
`/home/sin/code/agent/reserch/superfish-ng`。C00の最新記録はCOMPATIBILITY_BASELINE.md。
全32項目の受入軸、限定TM辞書と未確認事項、保存出力のAutomesh/Fish/SFO/SF7版、
参照ファイルhashを記録した。C00.Vは未完了。次はC01.Sの共通契約とC02.Sの
メッシュ/探索/未指定RF設定の変換契約を具体化し、C00の追加ツール調査も継続する。
開始時114 unittest中112合格・参照環境専用2 skip。今回の旧計算再実行はなし。
以下の計画整備のみを対象とした指示より本節を優先する。

## 現在の入口 — 2026-09-07 計画整備

最新指示は「実態に合わせて計画更新→互換対応表→作業分割」。このターンは計画を整備する。
計画整備v0を完了。[COMPATIBILITY_MATRIX.md](COMPATIBILITY_MATRIX.md)のK01〜K32と
[COMPATIBILITY_PLAN.md](COMPATIBILITY_PLAN.md)の.S/.I/.Vを次の作業単位とする。
次はC00の版・入力集合の確定→C01.Sの共通契約。高次要素へ直ちに飛ばない。
表のH/Uは対象版未確認、Xは互換必須集合外。仕様調査未完を互換完成と混同しない。
[IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md)と[BACKLOG.md](BACKLOG.md)を正本とし、
以下の履歴内の「次は…」やseed開始プロンプトより優先する。
製品基準1f5cd84で114テスト中112合格・2 skipを再確認。物理範囲や製品コードの変更はない。
P1-03は平坦z端で完了、P2-04はGUI範囲で完了。一般追跡・tune・直接保存の原子的完了は残る。

以下は日付付きの実施履歴。テスト件数・実行環境は各時点の値を保持する。

## 互換性拡張の再開 — 2026-09-07

ユーザーは可能な範囲で互換拡張を進め、区切りごとのローカルコミットを指示した。
P0-01のNGSolve独立照合を完了。仕様と再現はINDEPENDENT_COMPARISON.md。
通常環境の基準101テストは合格。検証専用venvは
`/tmp/superfish-ng-independent-20260907`。本体の依存・FEM・RFは変更していない。
次はP0-02のタグ付き非構造メッシュ。旧入力互換や物理範囲拡張の完了ではない。

同日P0-02/P0-03も完了。`solve case.json --mesh mesh.json --out ...` と
`solve(case, mesh_data=...)` を追加。仕様・受入はMESH_INPUT.md。
114件中112件合格・参照環境専用2件skip、標準数値検証PASS、既存周波数差ゼロ。
次の数値拡張候補はP1-01。メッシュの読込で対応物理範囲は増えない。

## 汎用GUI・共通入出力の計画 — 2026-09-06

ユーザー依頼に基づき [GUI_IO_PLAN.md](GUI_IO_PLAN.md) を作成した。
例題専用の処理を作らず、対応物理範囲の汎用操作を提供し、KEK対象操作と例題外の
合成ケースで受け入れる。追加機能・抽象化は全体品質への寄与で判断する。
追加指示でG0〜G5の受入完了を `/goal` に設定した。ADR-009/010により
Project・JobManager・保存結果読込・Study・ローカルGUIを共通化した。
新規Web/Qt依存なし。形状編集、旧結果取込、掃引/収束/比較/分散を実装済み。
32数値受入、101 unittest、別環境へ展開したwheelのGUI計算/描画がPASS。
G0〜G5の技術的受入を完了。実行証拠・対象外・主観評価の未実施はGUI_ACCEPTANCE.md、
操作はGUI_GUIDE.mdを参照。
`python -m superfish_ng gui --workspace out/gui-workspace` で起動する。
既存の半端部バンド同定を任意形状へ適用しない。一般mode tracking・tuneは本計画の対象外。

## 境界・局所メッシュ改善 — 2026-09-06

任意のv2 mesh設定で境界辺と角周辺の内部辺を実長制御する。既定は従来経路。
設定仕様はINPUT_OUTPUT.md、検証数値と制約はPHYSICAL_MESH_REFINEMENT.md。
最終9計算は `out/physical-mesh-final-20260906/`。1 mm固定点変化26.14%→2.21%、
PEC接線比7.95%→1.52%。節点約3.25倍であり同コスト優位の証明ではない。
円弧には境界サイズのみ対応。P1電場復元と鋭角特異性は変わらない。

## 角部診断の追加 — 2026-09-06

ユーザーの質問を受け、P1-04の切り分け評価を実施。
[SURFACE_FIELD_DIAGNOSTICS.md](SURFACE_FIELD_DIAGNOSTICS.md)に新規計算と解釈を記録する。
鋭角のEpkは細分で上昇するため、過去のNG–Wine差14.8%を有限厳密値の誤差と解釈しない。
実装本体は変更していない。現checkoutには過去out/がなく、ユーザー許可でWine比較環境も新設した。
NG25計算（元の19＋真空側固定点6）とWine鋭角/接線円弧各4段階を完了。
最終参照は `out/surface-wine-arcs-20260906/report.json`、図と集約値は
`out/surface-wine-report-final-20260906/`。鋭角の生結果は検査して再利用した。
Wine最細の鋭角ピーク変化17.48%、丸み対照ピーク変化2.81%を未収束として残す。
丸み対照のNG–Wine差は1.21%。今回の診断をP1-04全体の完了やEpk精度保証と呼ばない。
78テストと `out/validation-surface-final-20260906/` の既存数値検証は合格。
Wineランタイムは `/tmp/superfish-wine-runtime/`。一時領域の掃除後は再作成が必要。

## 現在の優先目標（2026-09-05更新）

ユーザー指定の [セミナー4資料の例題計算・可視化](MILESTONE_SEMINAR.md) は完了。
最終結果は `out/seminar-suite-final-20260905/index.html`、受入監査は [MILESTONE_ACCEPTANCE.md](MILESTONE_ACCEPTANCE.md)。
9数値ジョブ・69テスト・7ページ検査がPASS。全NGは新規計算、Wineは入力・hashを検査して再利用した。
最終suite.jsonはPASSかつsource_changed_during_run=false。継続待ちの計算プロセスはない。
以下の個別試行・失敗も履歴として保持する。次の機能拡張はユーザーの次の指示で選ぶ。
Wine版SUPERFISHとの3形状の基本モード照合は完了し、[比較結果](SUPERFISH_COMPARISON.md) を保存した。
S1の全領域TM010/TM011・長さ掃引・図・CSV・HTMLとWine/SF7照合は実装済み（[記録](SEMINAR_PILLBOX.md)）。
S1の半領域の電気／磁気対称境界・全空洞鏡映も完了。`seminar_symmetry.py` で再現可能。
段差・円弧、4/7モード同定と分散曲線も実装済み。[記録](SEMINAR_MULTICELL.md)を参照。
flat4はNG nr=128/256/512とWine dx=0.05/0.025/0.0125/0.01で全照合・収束PASS。
`out/seminar-flat-ready-20260905` とheadless検査 `out/gallery-test-flat-ready-20260905` が最終結果。
rounded4はNG・形状近似・Wine3段階の全検査合格（`out/seminar-rounded4-wine-comparison-20260905`）。
rounded7は任意のcrossed分割を追加し、nr=64/128/256で全量PASS。
`out/seminar-rounded7-crossed-native-20260905` と `out/seminar-rounded7-crossed-geometry-20260905` を参照。
円弧半領域の鏡映にも対応したが、対称反射だけのR/Q改善試験は不成功。失敗試験も保存済み。
rounded7のWine3段階は `out/seminar-rounded-wine-20260905/rounded7` で完了。
full-end切断面を実装した `scripts/seminar_end_cells.py` も追加。初回検査はflat/halfのR/Qだけ1.1521%でFAIL。
追加nr=384で変化0.32373%を確認し、`out/seminar-end-cells-ready-20260905` の最終レポートはPASS。
`out/gallery-test-end-cells-ready-20260905` で全8選択肢・51リンク/画像のheadless検査も合格した。
Pillbox/rounded4/7のHTMLはheadless Chromeの実キー入力で検証済み。Orcaの既存デスクトップ操作は行っていない。
S6の `scripts/seminar_suite.py` と入口HTML生成を実装し、`out/seminar-suite-20260905` の全NG計算・全7画面検査は終了。
全体FAILの原因は7セルπモードのWine側R/Q細分1.98217%とTTF。NG–Wine差は全モード合格。
RAM設定で追加DX=0.01/0.011 cmはSFO生成前に失敗。ローカルSF.INIのStoreTempDataInRAM=Noを使う
`out/seminar-rounded7-wine-extra-20260905/disk-dx0.01/mode7` が正常終了。既設SF.INIは変更していない。
πの追加R/Q細分変化0.658403%、NG–Wine差0.757236%で合格。元の未達履歴は消さない。
モード別追加細分の検証を実装し、`out/seminar-suite-final-20260905` で全NGを再び新規計算してPASS。
参照は既存Wine生出力を検査して再利用し、必要なrounded7出力は最大14400秒の読取専用待ちを明示した。
開始時のsource/tests/scripts/examples hashと終了時の一致を確認した。今後も一括実行中にはソースを編集しない。
最終suite.json、全子レポート、参照ファイル、画面とリンク先のhashも再監査した。
追加参照を含む比較はfinal_legacy_modesを読む。legacy[-1]は追加前の履歴であり、πの旧FAILが意図的に残る。
操作手順と判定仕様は [SEMINAR_SUITE.md](SEMINAR_SUITE.md)。
以下の開始プロンプトはseed時点の記録で、次課題P0-01の優先順はこの更新で置き換える。

## 開始プロンプト

以下をそのままCodexへ渡せる。

```text
このSuperfish-NGリポジトリを継続開発せよ。
AGENTS.md、README.md、docs/PHYSICS.md、docs/PROVENANCE.mdを最初に読み、
ローカルでテストとscripts/validate.pyを実行して初期状態を確認すること。
旧SUPERFISHのソースやバイナリは参照・使用せず、公開された数学と
明示的なライセンスを持つ現代のOSSだけを使用する。

次の目標はdocs/BACKLOG.mdのP0-01「外部ソルバでの独立照合」である。
同じ幾何形状・境界・phasor・単位・R/Q規約を固定し、NGSolve等で
独立に計算して比較する。参照ソルバを導入できなければ、比較済みとは
主張せず、実行可能な比較用入力と未実行の理由を残すこと。
その後P0-02の境界タグ付き非構造メッシュ対応へ進む。

科学的な回帰を起こさず、小さなコミットで進めること。
周波数だけを解析値に合わせてRF量の精度を保証したことにしない。
変更内容、検証結果、未解決事項、次に実行するコマンドを最後に報告せよ。
```

## 現在の動作経路

`Case.load → make_mesh → assemble → solve → quantities → save_run`。
式と積分は `src/superfish_ng/fem.py` と `rf.py`、独立解析解は `analytic.py`。
テストは `unittest` 69件。seedの主要数値は `benchmarks/validation/`、最新照合は `docs/SEMINAR_PILLBOX.md` と `docs/SEMINAR_MULTICELL.md`。
出力は別の新規ディレクトリへ作る。既存ベンチマークを直接上書きして初期値を失わないこと。

## 直近の注意点

- P1のuはr³重みのエネルギーでは良好でも、軸上Ezの点値収束はより遅い。
- 自由度は節点u=Hφ/r。VTKに出すHφはrを掛ける。軸上uを0にしない。
- 電場のP1微分を節点平均で平滑化すると見た目は改善してもピーク値が偏る。未評価の平滑化を設計指標に混ぜない。
- 無限に鋭い角を持つ形状ではEpkのメッシュ独立値が存在しない可能性がある。丸め半径を仕様にする。
- 既定のactive lengthは全長。多セルやビームパイプ追加時に自動流用しない。
- seedのQR/直交化はeigshに任せ、物理的な勾配nullspaceを除去したことにはしない。現在のTM縮約に3D機能を足す際に再設計する。
- `save_run`は出力ディレクトリを新規作成するが、ディスク書込み全体のトランザクション化は未実装。途中失敗したディレクトリは完了扱いしない。

## 環境の再現

通常は `pip install -e .`。納品時のPython 3.12系に揃える場合は
`pip install -r requirements-reproduce.txt` の後 `pip install -e . --no-deps`。
このファイルはプラットフォームごとの依存ハッシュを固定したlockfileではない。
OS・BLAS・CPUや縮退モードの基底は変わり得る。期待値は許容誤差で比較する。

CIはLinux/Python 3.10と3.12を対象とする定義を同梱したが、納品時の実行実績はローカルPython 3.12のみ。
依存環境を整えたユーザーPCでのテスト結果を次の記録として保存する。

## 完了報告の基準

新しいバックエンドは、関数がimportできるだけでは完了ではない。
入力ケース、出力、参照値、誤差、実行バージョン、未対応条件を記録して初めて完了とする。
外部参照値が入手できないときはその事実を示し、架空のSUPERFISH/CST比較表を作らない。

最新メッシュ改善の検証: 82テスト、`out/validation-physical-mesh-final-20260906/` PASS。
seed周波数差ゼロ、RF相対差最大6.67e-16。既存ベンチマークの更新なし。
