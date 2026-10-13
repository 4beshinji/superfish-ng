# RF版5対照：予算停止の保存と追加求解ゼロの再開

2026-10-13 JST、`ADD-N04-rf-goal-04`の予算停止処理を限定検証。
04全体は **IN_PROGRESS**。固定36実行05、GUI/原条件監査06、親N04も未完。

## 今回の受入条件

幾何上限または追跡予算で止まった保存結果を、元場・元分岐を再構築するreaderで読めること。
上限を検査したphaseのFAILEDと元elapsed値を残し、成功した計測へ書き換えない。
再開の最初の計画が拒否された場合は、追加求解なしの終端結果として保存する。
元prefixの全event/native/sample/費用と元要求を保持し、新しい計測区間を別に扱う。

対象はworker、保存reader、再開metadataとその直接consumer。
FEM・幾何細分・RF量・物理閾値の数学ソースは変更していない。
旧保存結果には追加のplanning metadataを要求せず、宣言された元byteと分岐を検証する。

## 保存と検証

比較用の次の一様計画が拒否された結果は、`planning_stop`にstage、最後の親event、
未実行の次event、非成功statusと元reasonを残す。
通常の計画は`next_uniform_plan`、再開直後は`initial_resume_plan`を使用する。
公開RF分岐が自身で捕捉した上限停止は、元public checkpointとnative_statusで保持する。

費用readerは、非成功のREFINEMENT_LIMIT/TRACKING_BUDGETに限り、実際の計画/品質検査の
ValueErrorをFAILEDのまま受け入れる。public側で捕捉された場合は、外側のnative/replay
phaseはCOMPLETEDであり、拒否された内側phaseだけがFAILEDになる。
他の失敗、固有求解失敗、成功/PAUSEDへの失敗費用混入、偽のCOMPLETE費用は拒否する。
親子phase算術、全eventの計測範囲、C solve対応、有限値の条件は維持する。
返却値は`STRUCTURE_VERIFIED_WITH_CAUGHT_BUDGET_FAILURE_NOT_REMEASURED`。
元時間の真正性を再計測したという意味ではない。

追加eventなしの再開結果には、明示した再開直後の終端budget stopを要求する。
その親は必ず元PAUSED journalであり、終端結果を再開元へ昇格しない。
同じ長さの終端journalへ再帰する前に親statusを拒否し、PAUSEDの再開連鎖は長さが減少する。
最後に、元の一様計画をもう一度実行し、同じ上限拒否と元reasonが実際に再現することを要求する。

## 検証の範囲

証拠は`out/n04-rf-goal-budget-20261013/`に保存する。
中断前のcost reader失敗と、その後のfixture ERRORも上書きせず残す。
public replayの外側までFAILEDにしていたfixtureを、元の捕捉位置に合わせて修正した。
幾何testのimport誤記は当該testだけを修正し、成功済みの検証を再実行していない。

独立な幾何条件は、一様参照細分による4倍の要素数である。
上限4T−1では新空間の割り当て前に拒否され、上限4Tでは実際に4T要素となり、元空間は不変。
費用・入力/保存metadata・prefix保持・再帰拒否・直接consumerを選択して検証する。
seed TMの数学経路へ変更がないため、seed/full validatorは今回の対象外とした。

新3＋直接16の19個別unitが分割PASS。`metadata-after.log`の成功13件、
修正後の`geometry-after.log`1件、`consumers.log`5件を使用する。
初回の費用testのFAIL、停止前のfixture ERROR、幾何importのERRORは別logで保持した。

実workerの異常系には、元固定requestを変更せず、検証中だけ小さい上限を与える。
幾何では元の4T上限guardを実行する。追跡については元guardのValueErrorを注入する
制御フロー検査であり、大きな追跡空間の実資源検証とは数えない。
PAUSED結果、通常実行中の幾何停止、公開RF分岐の幾何停止を実FEMで作成し、
幾何/追跡の再開直後停止では新FEMを行わず、全保存再検証を行う。
注入を外した元固定計画では、これらの異常系停止結果がreaderに拒否されることも検査する。
終端budget結果からの再開は拒否され、新出力先を作らない。

実検証processは終了0、140.908411秒、最大RSS106659840 byte。
新FEMは3回、保存再検証の新FEMは0回。3 nativeの全33配列と全RFが元の同一水準と完全一致し、
Ue/Uhの0.5 Jからの相対差は最大1.333e-15。
四つの停止結果を注入なしで読む試行と、終端budget結果の再開をすべて拒否した。
元PAUSED journalのbyteは不変、新しい再開先にはevent directoryを作っていない。
`runtime-verified.json`と実process記録へこれらを束縛する。

原1484対象源のうちworker/reader/resume以外1481はbyte不変、新test一源で1485。
全検証handleは終端。`acceptance.json`に検証log・元/最終source・raw SHAと残件を記録し、
`commit.json`に今回のコミットを結合する。

この異常系検証を固定36実行の成功、物理誤差上界、性能比較へ数えない。
外部資料/依存/legacyの追加はない。原計画・元未達・物理規約と許容値を維持する。

## 残る作業

04には全process/failure manifest、最終result書込までの外側費用、専用CLI、
SIGTERM/強制killからの一般的な再開が残る。
実固定予算での全36実行と精度/費用/未達の受入は05、GUIと原条件監査は06で行う。
全141は91 DONE/3 IN_PROGRESS/47 PLANNED、原123は76/2/45を維持する。
