# C02: 限定AF入力の読込仕様

2026-09-07。C00で記録したローカルR25 VI.1/2の入力仕様と保存AFを根拠とする。
全AF文法や旧ソルバーの再実装ではなく、確認済みの真空・軸接続m=0 TM部分集合を
v3 Caseへ変換してNGのFEMで解く。C00全体が未確定でもこの部分集合は先に受け入れる。

## 受理する文法と物理

UTF-8（既定）または明示したLatin-1のテキスト。最初のnamelistは行頭（空白可）から開始し、
それ以前はタイトル。タイトル途中の`&`や`$`はnamelistの開始と解釈しない。
REGは先頭に1個、その後はPOだけ。大小文字を区別せず、`$REG ... $`、
`&REG ... &`、`$END`/`&END`終端を受理する。開始・終了の記号は一致させる。
`!`と`;`から行末はコメント。整数・小数・E/D指数の有限数値だけを受理し、
配列・式・文字列値・STOP/ENDFile・未知namelist・未知変数・重複を位置付きで拒否する。
整数変数は整数リテラルを要求する。曖昧な旧入力を推定修復しない。

| REG変数 | 受理・変換 |
|---|---|
| KPROB/ICYLIN | 必須、1/1だけ |
| NBSLO/NBSUP/NBSLF/NBSRT | 必須、0/1/1/1だけ。全外壁PEC・軸正則条件へ変換 |
| BETA/KMETHOD | 必須、1/1だけ。一定β=1、全長通過電圧 |
| ZCTR | 必須、入力全長の中央だけ。位置の照合は相対1e-12以内 |
| MAT | 省略または1だけ。真空 |
| CONV | 正の有限値。省略1 cm/入力単位。長さはCONV×0.01でmへ |
| DX/DY | 指定時は正。旧メッシュの長さ指示としてSI換算して記録するがNGへ適用しない |
| FREQ/EPSIK | 指定時は正。旧探索初期値[MHz]/反復条件として記録し、NGへ適用しない |
| XDRI/YDRI | 両方指定または両方省略。長さをSI換算して記録し、NGの固有値問題へ駆動点を追加しない |

POはX/Y必須。最初は(0,0)、次は(0,Rstart)、壁点をz非減少で並べ、
最後は(L,Rend)、(L,0)、(0,0)の順とする。回転開始点や逆順輪郭の自動並べ替えはしない。
孤立した垂直段差と短円弧はCaseの形状検査へ渡す。初期/末尾の壁区間の垂直、
半径非正、z折返し、穴、未閉鎖、自己接触は拒否する。
NTは省略1（直線）、4（ccw円弧）、5（cw円弧）。4/5はRADIUSを必須とし、
Rを半径の別名としない。円弧は壁点間だけで、軸や端板に指定できない。
NT=1にRADIUSを与える入力、NT=2/3、X0/Y0、極座標はこの版では拒否する。

## NG設定と意味の差

変換API/CLIはNGのnr、nz、modes、conductivity_s_per_m、normalization_jを必須とする。
DXからnrへ暗黙変換せず、指定したNGメッシュ設定で再現する。modesは低周波側からの個数で、
FREQ近傍の旧探索結果や物理モードラベルではない。探索・メッシュに意味の差があることを
変換診断へ必ず記録し、CLIも表示する。必要なモードの照合はC04/D01の別受入。
導電率はNGの摂動壁損失用、正規化は計算領域内のピークphasor全エネルギー[J]。
旧の暗黙の銅抵抗率や正規化を推定しない。円弧の弦誤差はNG設定（既定1e-5 m）として記録する。
SEGは読まない。全実PEC面を壁損失へ含めることと、旧SEGの選択は未移行であることを診断する。
この制約をもって旧側の部分面損失を再現したとはしない。

## API・CLI・保存

`superfish_ng.legacy_input.parse_af(text, *, nr, nz, modes, conductivity_s_per_m,
normalization_j, arc_chord_tolerance_m=1e-5)` はCaseと変換レポートを返す。
不正入力は `AFInputError(ValueError)` に1始まりの行・列・理由を付ける。

`superfish-ng import-af INPUT --out NEW_DIRECTORY --nr N --nz N --modes N
--conductivity-s-per-m SIGMA --normalization-j U` は新ディレクトリへ
case.json、原入力バイトを保つsource.af、conversion.jsonを出力する。
`--encoding utf-8|latin-1`、`--arc-chord-tolerance-m`は任意。
原入力hash、encoding、全変数の位置/値、SI換算、NG指定、意味の差、case hashを記録する。
不正入力は出力ディレクトリ作成前に拒否。既存出力は上書きしない。
I/O中断で残る不完全ディレクトリの管理はO01の後続対象。conversion.jsonは最後に書く。
実際のNG計算は通常の `solve NEW_DIRECTORY/case.json --out NEW_RUN` を用いる。
ローカル照合の原入力・旧出力はignored out/へ保管し、配布へ同梱しない。

## 受入

合成円筒の寸法・面積RL・体積πR²LとBessel周波数/RQ/G、単位を変えた等価入力、
段差の区分面積、既知中心と半径を持つ円弧の面積を独立検査する。
直接指定したcanonical Caseと同一メッシュの周波数・場・全RF量が一致することを要求。
未知/重複/式/非有限数/別物理/境界/閉鎖/円弧の拒否と位置、ファイルhash・保存再読込を検査する。
標準unittest/validateと直前基準の周波数・RF差を別々に確認する。
旧全入力互換や未実行の旧計算をPASSにせず、C02のこの限定部分集合の証拠を記録する。

## 初期部分集合のC02.S/I/V受入 — 2026-09-08

仕様は `0868545`。6つのunittestを追加し、未実装時の失敗を先に確認した。
タイトル途中の&/$をnamelistと誤認する失敗も追加検査で確認し、先頭namelistの行境界を修正した。
円筒の面積/体積・直接Caseとの全場/RF一致、段差面積、両円弧方向の既知中心/面積、
CONVでの単位等価性、位置付き拒否、原入力バイト保存、CLI計算再読込がPASS。
円筒の16→32段階で周波数/RQ/Gの解析誤差が減少し、f 1e-4、RQ/G 0.5%以内。

標準検証: `out/validation-c02-final-20260908/validation.json`、PASS。
128 unittest中126合格・NGSolve参照環境専用2 skip。
直前のC01最終検証と円筒/非円筒の全modes辞書・canonical case hashが完全一致した。
既存ベンチマーク・許容差は変更していない。

さらに既存の合成鋭角/接線フィレット形状のAFを実際に読込み、各nr=32/64、nz=64/128で
NGを新規計算した。β=1、U=1 J、導電率はSFOの明示抵抗率から1/1.7241e-8 S/mを指定、
弦誤差は3e-6 m。原入力・変換記録・計算・集約は `out/c02-import-acceptance-20260908/`。
参照は既存の `out/surface-wine-inset-20260906/sharp-dx0.05/0.025` と
`out/surface-wine-arcs-20260906/rounded-dx0.05/0.025` に対応する各ディレクトリ。
表記の0.05/0.025は2つの独立ディレクトリを示す。旧計算は今回は再実行していない。

| NG最細と保存SFOの相対差 | f | Q0 | G | RQ | TTF |
|---|---:|---:|---:|---:|---:|
| 鋭角 | 0.01052% | 0.00440% | 0.00965% | 0.00690% | 0.08069% |
| 丸み | 0.00272% | 0.00038% | 0.00174% | 0.00648% | 0.05255% |

各量のNG/旧差と両側最終2段階の変化は、既定f 0.1%、Q0/G/TTF 0.5%、RQ 1%を通過した。
両参照段階のAFを変換した物理caseが一致することも確認。
これは基本モードの周波数/RF照合であり、一般モード追跡・場全体・表面ピークの新規受入ではない。
最終パーサーで4変換caseと原入力hashを再監査し、保存済み計算入力との一致を確認した。
conversion.json単体のlegacy_compatibility_statusはUNVERIFIEDのまま。
変換そのものでは数値照合を行わず、上記の別レポートが限定した量の受入証拠になる。

再現例（新しい出力名を使う）:

```bash
OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/validate.py --out out/validation-c02-new
.venv/bin/python -m superfish_ng import-af out/surface-wine-inset-20260906/sharp-dx0.025/cavity.af --out out/af-sharp-new --nr 64 --nz 128 --modes 1 --conductivity-s-per-m 58001276.028072625 --normalization-j 1 --arc-chord-tolerance-m 0.000003
OPENBLAS_NUM_THREADS=1 .venv/bin/python -m superfish_ng solve out/af-sharp-new/case.json --out out/af-sharp-run-new
```

上記原入力がない環境でも合成unittestは実行できる。元AF/旧出力は配布物へ同梱しない。
C02初期部分集合のF/I/O/N/Wは上記限定でPASS。部分集合外は拒否し、全旧入力互換は未完。
両側再実行を統合した再利用可能な回帰ドライバーはC04、旧出力の製品変換はC03で継続する。
