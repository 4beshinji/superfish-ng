# RF-11：直線TMの求解契約と後処理条件

2026-10-13 JST、[RF-11](REFACTORING_PLAN.md#rf-11) **DONE**。
対象は真空・軸接続m=0 TMの直線P1/P2、通常生成/外部メッシュ/鏡映、RF評価・保存・読込。
リファクタリング計画11枚のうち最初の修正であり、残る10枚と既存機能の受入は未完。

## 入力と場を結び付ける契約

`Solution.solve_contract`はfrozen dataclassで、求解時の物理Case、実メッシュ/自由度/境界役割、
生成元、外部入力mesh、鏡映元を文字列とSHAで保持する。呼出元の可変dictとは共有しない。
既存`source_case`は鏡映元として維持し、通常求解の契約を代入する用途には使わない。
RF評価と完了保存の前に、渡されたCaseと契約、現在のメッシュ/自由度と元snapshotを照合する。
電気・磁気の体積エネルギーを別々に指定U/2へ照合し、振幅をfit/補正しない。
既存のverified affine readerの1e-7整合条件を使い、物理精度の許容差は変えていない。

β、導電率、加速区間、位相原点、有効長、表示名は求解契約から分離する。
Caseによる有限/単位検査に加え、加速区間が実メッシュの軸領域内にあることを確認する。
旧v1の暗黙の真空モデルと後処理指定による明示v3の既定モデルは、同じ物理として比較する。
既存`solve_p2(case)`のP1入力宣言からP2場への明示昇格も保持する。

公開`quantities`は求解契約を検証する。内部`_affine_quantities`は元のRF積分式のままで、
人工的な試行場の数学検査はこの層で行う。規格化済み固有解を人工場と周波数へ上書きしていた
既存の電圧打消しfixtureを、この積分検査へ明示移行した。公開契約の拒否を緩めていない。
通常のFEM、求積、固有値、規格化、両R/Q、RF/表面量の数式bodyは維持する。

## 保存版と旧成果物

新しい保存項目は追加しない。結果schema 1と完了protocol 1、canonical入力hash、
既存native配列を維持する。新runtime契約を保存hashだけの物理証明として扱わない。

直線readerは再求解せず、全メッシュの宣言領域・位相幾何・軸と境界役割を検証する。
通常生成は宣言Caseからのメッシュと照合し、外部入力は元mesh.json/全配列を照合する。
鏡映は宣言した半領域から導出する全領域・境界・Uの2倍を照合する。
P2自由度を再構築し、元場の電気/磁気体積エネルギーを別検査する。
読込時に組み立てた行列はverified affine readerで再利用し、同一読込内の二重組立を避ける。
再保存に必要な外部入力と鏡映元も所有コピーとして保持する。

hashが一致しても宣言半径/長さ/Uと実配列が矛盾する成果物は理由付きで拒否する。
不正な新規保存は出力directoryや完了マーカーを作る前に拒否する。
正常な旧保存は読み、元の場・周波数・RFを保持する。
ここでのエネルギー/領域照合を、離散化精度・表面peakの物理誤差上界とは呼ばない。

## 実検証

rawは`out/rf11-input-contract-20261013/`。
科学レビューと同じR=.1 m、L=.2 m、U=1 J、nr=nz=8のP1/P2で、半径・長さ・9 J差替えを再現した。
改修前の自作source四つを別名で読み、その元source SHAを束縛して実行した。
外部/旧SUPERFISH sourceではない。P2長さのRF拒否は元から成立しており、新規失敗と数えない。
実際に旧保存が完了した不整合5件は新readerが拒否、正しい旧保存2件は全場/RFを保持した。
完了hashを付け直したCase差替え六件も拒否した。

新6＋直接61の計67個別unitを分割PASS。
P1/P2の差替え拒否・後処理変更・現場/外部入力/鏡映元の変異、通常/外部/鏡映保存、
既存Bessel場・体積エネルギー・軸電圧・壁積分・両R/Q/G/表面量、完了保存の失敗地点、
直線適応/調整の再開を確認した。人工場の境界、モデル自動昇格、test名/タグfixtureの先行ERROR/FAILは保全した。
CLI診断/Matplotlib警告がtest行を分けたため、証拠集計の初稿65件も保全し、元logから67件を収集した。
成功済みの検証を件数更新のために再実行していない。

seed validatorは`out/validation-rf11-seed-20261013/`、`--skip-tests`の範囲でPASS。
対象sourceの開始/終了hashは全一致。benchmarkのpillbox/shapedに対し全周波数差0、
全12 RF量の最大相対差8.882e-16。独立場/周波数/積分/表面の検査は上記unitと別判定した。
full validator、GUI、外部/実測比較の新規受入には数えない。

seed後の外部入力所有guard追加は数学bodyを変更していない。
seed時の三sourceをarchiveし、元hashと最終sourceとの差を別記した。
当該外部/鏡映consumerを追加検査し、seed全保存を最終reader/RFで再構築した。追加固有求解は0。
RF積分bodyの元AST一致も確認し、初回seedを最終sourceで再実行した記録には書き換えていない。

既存1485対象源の変更は六moduleと既存fixture一つ、他1478源はbyte不変。
新契約module/test二つで最終1487。`acceptance.json`へ元/最終source・全raw SHA・67unit・
seed前後監査とその後のmetadata限定差分を記録し、`commit.json`へコミットを結合する。
新規依存/外部資料/legacy参照はない。次はRF-01のvalidator本体の前後監査。

## 2026-10-14 広範統合での追補

RF-03の初回fullで、RF-11の直接検査だけでは捉えなかった計測・反射・テストfixtureの接続を検出した。
初回fullは終了1のまま保持し、1492 sourceの実前後監査がUNCHANGEDであることを確認してから修正した。

- `affine_saved.assemble/assemble_p2`の旧計測名を復元した。実保存解のP2組立は既存`high_order`経由で1回だけ計測され、旧名の呼出は0回。余分な組立や人工的な費用を加えない。
- `reflected_case`の宣言/加速座標検査を場のparity検査より前へ戻した。混在端・非連結電圧区間の元の拒否順を保ち、反射の数値計算bodyは変えない。
- hyperbolaの独立比較は4 modeで求解したCaseをRF評価にも渡す。元のf/RQ/G比較許容差と、入力/解の照合を維持する。
- 共用直線調整fixtureは検証済みaffine readerから復元する。実保存P2で元の行列/場/残差/全RFとの完全一致を確認し、fixtureの独立行列再組立と全Bessel参照/検査class bodyはAST不変。

追補のrawは`out/rf03-lower-helpers-20261013/integration-fix/`。
validatorの直接4件を含む58個別unitを隔離した同じ自作sourceで分割PASSした。
直線探索3形状の各18 FEM試行はpause/resumeと完全再生を通過し、元のFINAL_UNVERIFIEDを保持する。
隔離コピーの試験用JSON欠落で起きた初回ERRORは保全し、元fixtureをbyte一致で追加して再検証した。
終端後に検証済み5 sourceだけを主ツリーへbyte一致で反映した。
この58件は主ツリーでの実行記録やfull成功ではなく、修正後の固定source fullとseed f/全RF比較は未受入。
最初の67 unit/seed受入はその当時のsourceと範囲の履歴として保持する。

## 2026-10-14 最終統合での確認

上の追補は受入前の記録として保持する。RF-03の固定full受入を経て、
[全11カードの最終受入](REFACTORING_ACCEPTANCE.md)で現行1507 source/2698実行枠/530moduleの
実full終了0・前後source一致とseed全9modeのf差0/全RF物理量差最大8.882e-16を確認した。
metadata/拒否順の追補はRF-03受入commitへbyte結合し、元FEM/RFとRF-11の物理契約を保持する。
過去の未受入や初回失敗の記録を、最終sourceで行った検査として書き換えない。
