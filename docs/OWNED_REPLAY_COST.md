# 曲線Hφ所有履歴の再生費用と検証内再利用（RF-10）

2026-10-14 **RF-10 DONE**。RF-04/05/08後の曲線Hφ worker完了検証を一件の測定対象に選んだ。planarのprefix組立、直線/材料Hφの費用は今回測定していない。後述の限定測定とguardを受入条件とし、一般の性能/精度保証を行わない。

## 測定した元データと条件

raw索引は`out/rf10-replay-cost-20261014/acceptance.json`。実workerで履歴1・2・4試行の完了PAUSED、周波数nullのUNVERIFIED、実中止後1試行のPAUSED prefixを生成した。完了nativeは9試行。中止processは終了-15で完了manifestを公開せず、保存済みcheckpointだけを通常readerで再生する。完了PAUSEDは求解履歴の検証成功であり、TUNEDや精度達成を意味しない。

各nativeは自由度25、計算mode数3（TEMの個別ID＋upper guards）。元fixtureの要求/周波数・mesh gateを保持。UNVERIFIEDだけcluster guardを0.9に変更し、中止用は実測f0/1.0625の目標と厳しい探索条件を使用した。元場を解析式や数値表で置換しない。

Python 3.12.3、NumPy 2.5.2、SciPy 1.18.1、`OPENBLAS_NUM_THREADS=1`で、一測定processずつ実行した。先に全生成processを終端させ、旧/新各30操作（五条件×plain/観測×cold1/warm2）、計60操作を測定。測定とFEM unitを並行させていない。

coldはmodule import後の新しいPython processで、native物理検証を初めて呼ぶ条件。所有byteの事前SHA照合がOS page cacheを温め得るため、cold diskは主張しない。warmは同じprocessで独立に二回再検証する。毎回新しい検証contextであり、測定器も検証結果をcacheしない。

[measure_curved_tune_replay.py](../scripts/measure_curved_tune_replay.py)は新規求解を禁止し、元checkpoint/全ID/判断との完全一致、source/所有fileの前後SHAを確認する。plain時間を別に測り、観測時は実関数を同じ引数/戻り値で転送してnative read/組立/全再生/prefix時間を数える。binary byteは`Path.open`読取量、SHA byteはhash投入量であり、物理disk I/Oではない。20 msのRSS sampleとprocess累積high-waterを区別し、入れ子の関数時間を加算しない。

## 観測値と採否

表の時間はplain warm二回の中央値、回数/byteは同条件の観測値。cold、plain/観測の各値・RSS・hash量はrawの`measurement-table.tsv`と`measurement-comparison.json`に保持する。

| 条件 | 履歴長/DOF/mode | 元→新の秒 | 元場read | 行列組立 | binary読取量 byte |
| --- | --- | --- | --- | --- | --- |
| 完了PAUSED | 1 /25 /3 | 5.569→2.889 | 2→1 | 28→14 | 2,040,799→11,054,799 |
| 完了PAUSED | 2 /25 /3 | 12.905→5.251 | 5→2 | 70→28 | 4,756,797→13,533,742 |
| 完了PAUSED | 4 /25 /3 | 34.482→9.954 | 14→4 | 196→56 | 13,016,881→20,801,187 |
| UNVERIFIED | 1 /25 /3 | 5.564→2.844 | 2→1 | 28→14 | 2,040,945→11,054,945 |
| 実中止prefix単独reader | 1 /25 /3 | 2.577→2.595 | 1→1 | 14→14 | 192,814→192,814 |

元の履歴4は観測34.262秒中prefix再生24.455秒（71.4%）だった。native readは最終全再生4＋prefixの0＋1＋2＋3＋4＝14で累積する。同じ検証呼出内の全再生済み履歴から各prefixを確認する実装を採用し、測定したplain warmで1.93/2.46/3.46倍の時間比を得た。これはこの合成条件の観測比で、一般的な速度保証ではない。

実装束縛のため全Python sourceを前後hashする費用が増え、binary読取量は短い履歴で特に増加する。この不利も表に示す。RSSは旧/新で約98〜108 MiB、1試行のplain sampleは約0.70 MiB増、他条件はほぼ同程度であり、メモリ改善を主張しない。中止prefixの単独readerは旧経路を維持しており、約0.7%の遅速差を変更の効果としない。

## 再利用の境界

[curved_hphi_tuning_prefix_replay.py](../src/superfish_ng/curved_hphi_tuning_prefix_replay.py)のprivate contextは、曲線workerの完了検証一回だけで使用する。

1. 元の所有file集合/manifest検査とsubmission祖先の完全再生を保持する。
2. 結果ファイルを元readerで全native・FEM/RF・ID・回復・判断まで新しく再生する。metadataだけのhashを確認済み場へ昇格させない。
3. そのreportの私有copyだけを持つ。各prefixのstrict format/型/キー、所有path、元byte SHA、要求copy、trial/ID/親を照合し、確認済みprefixから元の純粋停止判断を再計算する。場配列を保持して再利用しない。
4. source実装hashと元共有workerの最後の全file snapshotを検査してから結果を返す。新しいread/失敗/context終了で状態を捨てる。

public checkpoint読取、外部submission、再起動にはこのcontextを渡さず、元の全再生を行う。次の完了検証も新しい全再生を必須とする。永続cache/検証済みflagの保存/schema変更なし。共通worker本体、直線/材料adapter、CLI/GUI、数値核/規約/物理許容差は変更していない。旧曲線prefix helperも元signature/bodyを保持し、撤回時は元callbackへ戻せる。

## 受入と確認範囲

`test_curved_hphi_tuning_prefix_replay`新6、`test_curved_hphi_tuning_jobs`旧5、`test_curved_hphi_tuning_recovery_saved`旧2の13個別unitが737.939秒・終了0/PASS、SKIP0。元/新の再生回数と全結果、再hashした周波数/親/要求/source hash/状態/形式改変拒否、実byte/要求copy変更時のcache失効、新read/検証終了/実装変更時の状態破棄を確認した。既存実pause/resume/cancel/manager再作成/成果物移動/失敗prefixと、回復IDを持つTUNED履歴・穴付きProject/全RFの所有を保持する。

全test収集は2698 ID/530 module、元2692 IDを保持してguard6 IDを追加した。収集のみをfull実行の証拠としない。候補四ファイルを主ツリーへbyte一致で反映し、他1503 source不変、新三ファイルで1507 source。

60測定操作の全report/ID/判断は元結果と完全一致し、全所有fileのSHA不変。元9 native/27 modeを元係数から再構築し、全係数/周波数配列と全RFが完全一致した。独立なU=Ue+Uh、指定正規化、Q=ωU/P、G=Q Rsと1.125のMaxwell/体積/固定U時の壁loss/Q/Rs/G尺度を確認。r>0の非軸domainなので加速量/両R/Qは明示的にNoneを維持する。再検証のスペクトル確認/行列再構築は数え、新試行求解は0。残差の小ささを離散誤差の証明としない。

実装guardはstubのunitに加えて専用copyの実source file変更で拒否を確認し、context失効/byte復元/元native不変を記録した。準備時のraw相対path誤りを保全し、製品/科学gateの失敗へ読み替えない。新外部資料・依存・旧SUPERFISH資産参照なし。

カードの受入後、全11枚の原条件と証拠の最終監査、固定sourceのfull validatorを一度実施する。過去RF-03の2689件/3 SKIP fullを今回の全件証拠に読み替えない。原V02/V03/V05その他未受入機能カードの完了をこのリファクタリング受入で代替しない。
