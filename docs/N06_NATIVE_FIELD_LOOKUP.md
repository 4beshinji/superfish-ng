# N06：全供給点の元TM場評価

2026-10-08 JST、`adaptive_efficiency_fields.EfficiencyFieldSampler` を限定受入する。
先行は[量別精度leaf](N06_SAMPLE_ACCURACY.md)と[N05の固定条件](N05_ADAPTIVE_EFFICIENCY_PLAN.md)。
N06はIN_PROGRESS、12独立benchmark実行は未実施である。

曲線P2では元`CurvedFieldSampler`のBernstein外接boxを使い、全boxを包む
infinity-norm半径のKD-treeで候補を検索する。検索eps=0、最近傍個数の打切りなし。
丸め分の保守的余裕は候補検索だけに付け、最終box条件は元と同じである。
全候補を元の要素番号順に並べ、元`QuadraticLocator.inverse`の30反復/1024boxを使う。
各点の座標を一度求め、元`fields_in_cell`で全要求モードのEr/Ez/Hφを評価する。
要素ごとの点索引を一度sortし、要素数回の全点mask走査を避ける。
直線P2は元`FieldSampler.evaluate`をそのまま使う。
FEM・物理微分・規格化・閾値・既存samplerは変更しない。

未知物理/次数、不正モード番号・重複、非有限/complex型、不正shape/半径、
曲線のCase/spaceに合わない係数とモード数を拒否する。
領域外点を落とさず失敗し、逆写像未確認の理由を保つ。
元KeyboardInterrupt等のBaseExceptionはそのまま伝播する。
戻り値ALL_SUPPLIED_POINTS_LOCATEDは供給点のlookupだけの主張であり、
領域全体の標本被覆・元source・Case/境界・実個別ID・独立参照は外側で検査する。
振幅fit/平滑化/解析場への置換をしない。physical_error_boundはnull。

## 独立不変量と検査範囲

未実装時のImportErrorをbaselineとして保存した。
物理座標の一次関数u=A+B*r+C*zは任意の二次幾何写像でもP2空間に厳密に属する。
その物理微分(B,C)から独立に導いたHφ=r*u、Er=-r*C/(omega*epsilon0)、
Ez=(2*u+r*B)/(omega*epsilon0)と、全要素の内部/境界/軸を含む二モードを照合した。
これは製造係数の微分不変量であり、PEC固有解や物理精度の証明には数えない。
全供給点/各box上下端/中心でKD候補と元の全box走査が一致し、
元曲線samplerの全点・全モード値、係数byte不変を確認した。

実球二モードの新FEMを保存/再構築して全要素内部点で元samplerと照合した。
実円筒二モードも軸/境界/内部で元samplerと完全array一致を確認した。
欠測/不正物理・番号/非有限場、元逆写像の未確認と元中断を検査した。
新6個別unitの初回は0.569秒・終了0/PASS。曲線係数数/Caseモード数の
拒否を追加して共通入口を強化したため、同じ6件を一度再実行し0.583秒・終了0/PASS。
反復分は新個別件数へ加算しない。開発FEMは計4回（各実行の球/円筒各一回）。
既存原源1419点は全byte不変、新1421点/1214 Python源。
先行N06の41件と合わせ47個別unit、追加前N03 fullの証拠とは区別する。
全6検査は主のuv環境、BLAS1、明示PYTHONPATHで実行した。
最初のsnapshot用uv呼出しは既定cacheのread-onlyで終了2、solve/書込は0。
UV_CACHE_DIRを/tmpへ固定した後に原1419源をhashした。元環境失敗をrawに残す。

rawは `out/n06-cost-recording-20261007/field-sampler-{baseline,first,final}.log`、
`field-sampler-source-before.json`、`field-sampler-acceptance.json`。
本段階のseed/full/legacy/12benchmarkは0。
実丸め格子と元保存場への全点接続、source/domain/参照束縛、費用の実worker接続は後続。
この限定受入でN06・N04・親G03・全goalを閉じない。

## 元丸め保存場と独立全格子の実consumer

commit f749923の1421源を固定し、N03丸め二ローブ幾何2のFEM0/2を再構築した。
N05の完全初期Case/source mesh、末尾uniform2回だけのCase差、元source mesh不変、
全P2境界係数と全curve parameter被覆、元matrixの全九節点/実三IDを確認した。
全参照manifest/inputを含む1505束縛byteを前後/終端監査で再hashした。
独立三h水準の量別二変化と、全五mode/元選択IDを保持したNPZを使用する。
Case名や周波数順位だけで個別IDを推測しない。

Gauss16の22528体積点+1408軸点、Gauss24の50688体積点+2112軸点をすべて評価した。
元の完全native P2 radial fan/density/重みを旧保存値と完全一致で確認し、
同じsqrt-volume-density規約で元Er/Ez/Hφを単位的L2比較へ写した。
全76736空間点/三native mode/690624場成分が元N03保存場と**完全一致**、
最大絶対差は両次数とも0だった。native volumeと元全域momentも元1e-5以内。
振幅fit/標本削除/境界再投影は0。全五参照mode/三h水準を保持する。

元native-norm、単一H符号で量別leafへ実接続した。両次数で全九gateがPASS。
次数16の相対差はE=1.26066e-4/H=1.03610e-4/軸Ez=1.21662e-4、
f=1.47729e-8/両R/Q=2.25355e-6/G=2.28449e-4。
元全PECの離散peak上下端を再計算し、対参照の最悪差Epk=8.73803e-5/Bpk=1.85626e-4。
既存N03の元場誤差も別に再現した。周波数を場/RF/peakの代替にしない。
独立参照のpeakはsolver推定であり、physical/peak error boundはnull。

初回consumerは計算されたU=.9999999999999982 Jへ厳密な1.0比較を要求したため停止した。
その時点の新場標本/FEMは0。元Case指定の1 J完全一致と、計算Uの既存1e-12条件へ
検証器だけ訂正し、元FAILを保持した。再生consumerは51.600610秒・終了0/PASS。
記録秒はrecorder lifetime（import/プロセス開始は含まない）、peak RSS=1196466176 bytes。
これは共有の再生/参照確認費用であり、12実行の片方式のFEM費用へ算入しない。
終端監査は新場/FEM0で全1421源/1505入力/二出力NPZ/全gateを確認した。
raw consumer自身のSHAはreport生成前の束縛には入っていなかったため、終端監査で
実行後のhelper byteを明示してpinした。この束縛時点の違いを隠さない。

rawは `rounded-native-grid-replay/report.json`、二native NPZ、
`rounded-native-grid-replay-acceptance.json` と元/修正/監査log。
ここで使ったnativeはN03の受入済みFEM2保存場で、新N06 benchmarkではない。
新FEM/12benchmark/seed/fullは0。新一様/適応実行への同じ参照/域束縛は後続。

## 元保存readerからの直線/曲線接続

元直線read_solutionはSolutionではなく検証済みnamespaceを返すため、
新`EfficiencyFieldSampler.from_saved_run`を追加した。
元strict reader/completion検査を先に実施し、閉PEC/真空/m=0 TM/P2の完全Caseを確認する。
直線は元mesh/space/係数/周波数の同じobjectをsampling containerへ接続するだけで、
新solve/規格化/係数置換は行わない。曲線は元の再構築objectをそのまま使う。
sourceの前後SHA/同じ初期Case/全域/実IDの束縛は外側に残す。

未実装classmethodの二AttributeErrorをbaseline0.236秒として保存した。
新二unitは0.242秒・終了0/PASS。実円筒を保存/再構築し、solve禁止下で全mode場と
元reader/samplerの完全array一致、元係数/周波数一致を確認した。
元reader例外の同一object、P1/TE/対称端のsampling前拒否、曲線の元object保持を確認した。
開発FEMはbaseline/final各一回、計2回。新個別件数は二つだけでN06計49件。
旧六検査と旧sampler moduleは追加二method/一classmethodを除いて完全AST一致。
旧二byteはgit f749923とSHA照合してraw `before-saved-field-factory/` に保全した。
したがって元六unitと全丸め格子再生の証拠を再利用し、場を再計算しない。
1421対象/1214 Python源は同じ数、1419点不変・変更二点は追加だけ。
監査器の秒数仮定(.260秒)のFAILも保存し、実logの.242秒へ監査だけ訂正した。
最初のtest挿入位置で旧method末尾が新methodへ移ったため、実行前に元ASTへ戻した。
新baseline/finalは追加二件だけを実行し、旧検査の省略版を受入へ数えていない。
rawは `field-sampler-saved-factory-{baseline,final,audit,audit-followup}.log` と
`field-sampler-saved-factory-acceptance.json`。seed/full/12benchmark0、N06はIN_PROGRESS。
