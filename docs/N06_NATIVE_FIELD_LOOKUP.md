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
