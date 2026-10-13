# RF版5対照：保存した全native・全場・停止判断の再検証

2026-10-13 JST、`ADD-N04-rf-goal-04` **IN_PROGRESS**。
[新規worker](CURVED_RF_GOAL_EFFICIENCY_EXECUTION.md)の四記録・12イベントを、
保存係数から両Gauss次数の全場・全比較量・採用祖先・停止判断まで再構築した。
全24 sample archiveの5,007,024成分値が完全一致し、新たな固有値求解は0。
親・棄却probe・確認回数・初回達成・初期ID・実電場の6改変を、SHA更新後も拒否した。
これは04の保存読取部分の受入。実中止再開、追加一様確認の実証、全費用/CLIは残る。
固定36実行05、GUI/原条件監査06、親N04と全goalを完了へ昇格しない。

## APIと保存原本

`curved_rf_goal_efficiency_saved.read_curved_rf_goal_efficiency(path, *, expected_sha256,
bindings=None, implementation_aliases=None)`は原journalのSHAを必須にする。
raw JSONの重複キー、非有限値、未知/欠落項目、厳密型、順序、event上限、元固定要求を検査する。
`replay_curved_rf_goal_efficiency(document, ...)`は既読文書をdeepcopyして同じ再構築を行う。
元費用の来歴を主張するには、読取側が信頼する原journalのSHAが別途必要である。
今回のSHAは前工程の`acceptance.json`とその`commit.json`から取得した。
変更したjournal自身の新しいSHAだけで、過去の測定が真正だとは扱わない。

通常fileだけを読み、symlinkを拒否し、読取前後と最終段階で元byteを照合する。
元journalに宣言された実装449源、native全file、sample、独立参照を保持する。
過去workerの同一byteは明示`implementation_aliases`で指すことができる。
aliasは既存宣言名・絶対archive path・元SHA一致を要求し、archiveを実行しない。
今回の唯一のaliasは前工程の`worker-tested-12-native.py`である。
任意の自己申告source mapだけから過去の網羅性を証明するものではなく、
最終process/failure bundleの受入は後続に残す。

公開RF prefixは元`assemble`と`_VerifiedRFPrefix`で逐次再構築し、全eventと完全checkpointを照合する。
独立一様対照と公開成功後の比較専用continuationは、元P2一様制限と実親から計画を復元する。
各nativeの全Case/source/二次領域、全mode/RF、幾何積分とRitz、実親の個別ID追跡を検証する。
元native readerも保存RFを係数から再評価する。周波数順位を物理IDの代用にしない。

workerの`_sample_event(..., verify_samples=...)`は元係数から全Er/Ez/Hφと物理軸を再評価する。
NPZは`fields`と`mode_ids_json`だけを許し、dtype、全要素、scalar文字列のID配列を照合する。
sampleへの書込は行わない。volumeだけに元の正体積密度平方根を適用し、軸場をfitしない。
独立参照との差、実際の採用親との差、初期の全独立候補とのID対応、全履歴の九量判定を再計算する。
採用祖先/初期ID/記録内判定の不整合は、重い参照読取と全場評価より先にも拒否する。

比較対象のruntime NumPy scalarとtupleだけをproducerと同じJSON表記へ変換する。
保存側の型は厳密に維持し、bool/int、float/int、数値差を許容差で吸収しない。
再検証結果には原文書、全束縛、`new_eigensolves=0`、今回の別観測費用を返す。
再構築には随伴の線形求解が含まれ得る。固有値求解0を「全求解0」とは記さない。

## 過去費用と今回費用

過去のphase階層/順序/包含時間/排他時間、root和/全wall、全event・accuracy phase数、
累積native費用とprefix wallを検査し、元秒数をそのまま保持する。
浮動小数点で保存した時間の和だけに相対/絶対1e-12の算術照合を使う。物理判定の閾値ではない。
RSSは正整数byte/RECORDED、またはnull/UNKNOWNと理由を要求する。
投入時計がある場合はworker内時計以上の時間を覆い、全prefixで連続かつ非減少であることを要求する。
再検証の現在時刻で過去秒数を置換しない。結果は`STRUCTURE_VERIFIED_NOT_REMEASURED`、
final costのない途中checkpointは`PREFIX_ONLY_NOT_REMEASURED`と明示する。
SuperLUのC線形solve単独境界の計測と全process/failure bundleはまだ未受入である。

## 実保存場の検証

原データは前工程の開発12FEM、各方式の反復1・尺度1・最大3eventである。
本工程の全再生も固定36実行へ数えない。全processは終了0。

| 原ケース/方式 | event数 | 再検証wall秒 | 最大RSS byte | 元の比較判定 |
| --- | ---: | ---: | ---: | --- |
| 球 / rf_goal | 3 | 18.048643 | 101670912 | PAUSED、初回達成1、確認達成null |
| 球 / uniform | 3 | 16.093327 | 100741120 | PAUSED、初回達成1、確認達成null |
| 球 / uniform_when_rf_passes | 3 | 18.047999 | 102178816 | PAUSED、初回達成1、確認達成null |
| 長球 / rf_goal | 3 | 430.938524 | 566001664 | PAUSED、初回/確認ともnull |

長球80→320の棄却probe→元親80から113の局所分岐も全て保存する。
球の公開RF `TARGETS_MET`を比較側の成功へ読み替えない。
両次数合計のvolume位置1,592,448、軸位置76,560、成分値5,007,024を照合した。
これは全sampleの一致であり、連続物理誤差の保証ではない。物理上界はnullを維持する。

6改変のうち5件は元長球journalの親差替え、棄却probe削除、虚偽確認、虚偽初回達成、初期ID変更。
6件目は元球の最初のnativeと両sampleを新directoryへコピーし、Gauss16の全Erを1.02倍して
sampleとjournalのSHAを更新した。元係数からの全場照合で拒否し、原fileは変えていない。

## 選択検査・失敗の保全・証拠再利用

新保存読取の7個別unitと直接消費する元peak区間の1件、計8個別unitを分割PASS。
実行ログは`out/n04-rf-goal-replay-20261013/`の以下に保持する。

| log | 実行数 | 役割 |
| --- | ---: | --- |
| `saved-tests.log` | 4 | sample、費用、raw読取、直接peak区間 |
| `strict-metadata-tests.log` | 3 | strict文書と全source archive、費用 |
| `json-metadata-tests.log` | 3 | JSON表記修正と直接metadata/費用 |
| `prefix-metadata-test.log` | 1 | 最後に加えた早期祖先判定 |
| `cost-guards-after.log` | 2 | RSS/投入時計の拒否と既存費用 |
| `public-guard-after.log` | 1 | 初期ID欠落・公開checkpointの型/欠落をactionableに拒否 |

重複した個別testを加算して8件を超える受入件数としない。
未実装ImportErrorを保全。初回実再生はruntime NumPy scalarと保存floatの型比較で終了1、
6.969328秒/最大RSS97943552 byteだった。JSON表記だけを修正し、上表の全場再生が成功した。
後で見つけたRSS/投入時計の6不正記録は先行testがFAILし、guard追加後に2件PASSを確認した。
最終入力点検の初期ID欠落KeyErrorも保全し、欠落/不正公開checkpointをValueErrorで拒否する1件がPASS。
どの失敗も成功ログで上書きしていない。

全場成功後の変更は早期metadataと費用guardだけで、再構築/物理指標の各関数ASTは同じ。
そのguardへ四原記録を再結合し、長時間の数値処理は再実行していない。
既存workerの既定sample保存経路とその他関数もAST一致を確認した。
元1477源のうち他1476はbyte不変、新reader/testを加えて1479源。
全1,756束縛fileを最終再hashし、原native/sample/参照を維持した。

rawの`acceptance.json`に全source SHA、各再生結果/process SHA、6拒否、8個別test、
AST監査と残件を保存し、`commit.json`にこの受入記録とコミットを束縛する。
四成功/一失敗processと全tool handleは終端。seed/full/GUI/CLI、新FEM、新固定36実行、legacy参照は0。
新しい外部文献・依存・データ取得はない。元独立参照と元科学核を再利用した。
全141は91 DONE/3 IN_PROGRESS/47 PLANNED、原123は76/2/45を維持する。
