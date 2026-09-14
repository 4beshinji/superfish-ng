# TEモード追跡の接続計画

2026-09-15 JST：[TE円筒チューニング](TE_TUNING.md)を同端条件の直線円筒へ接続し、限定受入。
EφによるID、半領域・鏡映の元セクター順位、加速量N/A、保存再開・回復・最終粗細ゲートを保持。
関連53unit（52＋1の分割実行）、専用44実FEM、Chrome閉PEC9/鏡映11/旧TM9項目がPASS。
8組native全配列/RF一致、元114ファイル保持。一般TE形状・他物理調整とD03は残る。
親33=10受入/16進行/6他未受入/1範囲外、D02と全計画goalは継続中。


2026-09-09追補: [同端条件のTE円筒追跡](TE_SECTOR_TRACKING_PLAN.md)を半領域・鏡映部分スペクトルへ拡張し、限定受入。同じ側の一対称面を持つ直線P1/P2円筒が対象。実Eφで対応し、異なる端条件・通常/鏡映の混在を拒否する。独立32FEM、8Study、Chrome9操作、旧追跡8文書の再生、標準801件（799合格、2skip）と既存TM/TE数値回帰を確認。一般形状の追跡・TE調整は未対応。

2026-09-09。閉PEC・直線円筒TEの追跡をAPI/保存/CLI/GUIへ接続し、限定受入を完了。
TE Studyと一般形状の追跡は未実装。D01/O02/P01の全体完了を意味しない。

標準9994・最終比較40142とも終了0。標準771件中769合格・2skip（unittest1200.915秒、command1201.284秒）。TM seed9モード19量の周波数差0、RF/エネルギー差最大8.882e-16、旧TE保存7件の差0。標準・独立・固定時・終了後452対象hashとブラウザー実装hashが一致。out/validation-te-tracking-20260909に全ログ・比較結果を保持。

## 物理的な比較量

既存の汎用track_sampled_mode_subspacesは場成分の物理意味を呼出側へ委ねる。
円筒用track_cylindrical_modesはTMのHφとTEのEφを偏波別に比較する。
TEには専用アダプターとnative読込を用いる。係数vをTMのuへ別名付けしない。
閉PEC円筒ではr=Rρ、z=Lζの同じ規格化点へEφを引き戻し、ρ dρ dζで比較する。
一定のε0・体積係数は列規格化で消える。Eφは実ピークなので磁場quadratureを実場と混同しない。
この点ごとの比較写像は、一般形状の共変場変換や連続経路上の追跡保証ではない。

## 独立反例と初期試作

R35の円筒TEスペクトルで、J1正零点χ1,χ2を使うと、
(radial=1, axial=3)と(radial=2, axial=1)は
L/R = π sqrt(8/(χ2²−χ1²)) = 1.5120139382210656で交差する。
その0.97倍/1.03倍の円筒で第3・第4順位が入れ替わるため、順位を永続IDとして使うと誤対応する。

out/te-tracking-candidate-20260909/verify.pyはP2 nr32/nz48、6モード、2実FEMを計算。
32×32 Gauss点のEφを汎用部分空間追跡へ渡し、PASSを確認した。
保存reportを別途照合し、全6IDが独立スペクトルによる移動先順位と一致した。
source448対象は試作前後一致。driver/command.log/report.jsonを保持。
これは1尺度・1標本次数の候補であり、製品アダプターや保存replayの受入ではない。

## 実装と受入の順序

1. TE同士・閉PEC円筒・明示写像だけを受理する入口を追加。TE/TM混合は具体的理由で拒否する。
2. P1/P2・両尺度・符号/規格化・標本次数を変え、交差でのID保持、縮退時の部分空間のみの保持、計算帯域からの退出を検査する。周波数・場・RFの精度確認とは区別する。
3. TE nativeの全必要ファイル・Case・幾何を完全再検証し、前後hashを保持する専用保存経路を接続。改変・異種physics・不完全保存を拒否し、公開replayの結果一致を確認する。
4. CLI/GUIの比較入力・保存・再読込へ接続し、既存TM保存の版と意味を保持する。
5. Study・固定形状/細分・曲線・一般写像へ段階的に拡張する。個別IDが未確認なら調整/設計探索へ周波数を渡さない。

新規外部資料は取得していない。既存R35と自作部分空間追跡の数学を再利用する。

## 両尺度・両次数の追加候補検証

`out/te-tracking-crossing-scales-20260909` のdriverを実行、38529終了0。
P1/P2・尺度1/2・交差前後の8実FEM、6モード、nr64/nz96。
Gauss標本次数12/24/48の全12比較で、全IDの交差後順位が独立スペクトル予測と一致した。
列ごとの符号と異なる振幅を掛けた比較でも全IDが同じ。正規化主重なり最小0.999924801496。
周波数のMaxwell尺度則も相対1e-10以内で一致、448対象source前後一致。
これは候補アダプターの予備検証であり、近接縮退/帯域退出、保存replay、CLI/GUIの製品接続は未検証。
この検査の重なり値を場の離散化誤差として解釈しない。

## 製品API・保存経路の実装中

基準c5b4409の標準766件・448source一致を開始時に確認。
従来の円筒APIへ実TEを渡すとHphi_A_per_mのKeyErrorになり、TM場成分の仮定が成立しない反例を確認。
te_mode_tracking.pyを追加し、円筒APIからTEを専用Eφ比較へ分岐した。混合TE/TM・非円筒/曲線・未対応写像を拒否する。
保存経路はTEの全native/完了markerをsnapshotに含め、read_te_runで再検証後に比較し、終了時snapshotを再確認する。旧TM書式と再生結果は保持する。
新規5検査の初回16689終了1はTM生Solutionをsaved adapterへ渡したテストの誤り。保存TMとして修正後74684終了0、5件1.447秒。交差・真の近接縮退の部分空間・帯域退出・mixed/未対応写像・改変と比較中CSV変更を検査。
既存TM保存追跡6件0.277秒PASS（CLIとUNVERIFIEDのreplayも含む）。
製品独立11411終了0、out/te-tracking-product-independent-20260909。scripts/validate_te_tracking.pyで8実FEM、両次数/両尺度/3標本次数、全IDの解析順位一致、符号/振幅不変、Maxwell尺度則、4組のCLI作成/公開replay/API全文書一致がPASS。451source前後一致。
その後GUI説明を円筒TE対応へ更新したため、この独立結果を最終GUI更新後の全ソース証拠とはしない。この段階では最終統合は継続中だった。最終受入は冒頭を参照。

## GUI履歴と最終検証の進行

scripts/verify_gui_te_tracking.mjsでChrome8項目PASS、2587終了0。
独立交差前/縮退/交差後の3実FEMをGUIへ取込し、merge/splitによる部分空間のID集合保持、手動ID編集制限、履歴download全文書一致、保存再読込、改変拒否・以前文書保持、UNVERIFIED履歴の継続禁止を確認。画面を目視し、個別ID未確定が明示されることを確認した。
GUI86416/PID925463はSIGINT終了0。新管理器で取込3件をverify=True完全再検証し、元TEとの全係数・周波数・RF一致、Project元mesh、download履歴の全replay一致を確認。48208終了0、out/te-tracking-gui-independent-20260909。部分空間の両IDへtracked_frequency_hzが値を与えないことも確認。
既存TMのprofile比較・履歴と円筒merge/split履歴の3文書が全文書一致で再検証PASS。old_tm_tracking.jsonへ保持。
最終独立84610終了0、out/te-tracking-final-independent-20260909、8実FEM/4組CLI・replay/両次数/両尺度/標本次数がPASS。最終source452対象とGUI実装hashが一致。
標準9994・最終比較40142とも終了0。標準771件中769合格・2skip（unittest1200.915秒、command1201.284秒）。TM seed9モード19量の周波数差0、RF/エネルギー差最大8.882e-16、旧TE保存7件の差0。標準・独立・固定時・終了後452対象hashとブラウザー実装hashが一致。out/validation-te-tracking-20260909に全ログ・比較結果を保持。 TE Study/一般形状写像等は後続工程。

## 後続Studyの一時コピー調査

標準の主ツリーを固定したまま/tmp/superfish-te-study-candidate-20260909で試作した。
TE Studyの全拒否、execute_studyのTM読込/case hash、study_mode_trackingのTM読込が接続箇所。
パラメータ掃引だけを一時コピーで許可し、各点をTE native再検証して要約する候補を試した。
初回はNumPy scalarの値がstrict数値入力に抵触（終了1）。builtin float修正後12908は2点実FEMを完了したがStudy追跡のTM読込で拒否（終了1）。
追跡入力のTE再検証経路も追加した候補82377終了0、out/te-study-tracking-candidate-20260909。2実FEM・円筒6modeの周波数解析/加速量N/A、独立スペクトルUNVERIFIED、別途追跡PASSを確認。
verify.py/command.log/report.json/candidate.patchを保持。主ツリー452sourceは不変。主ツリーには適用しておらず、Studyの製品対応とは数えない。
次の受入にはCLI/worker中止/再起動/改変、GUI掃引・結果取込、一般条件でのN/A/未評価表示、旧TM回帰が必要。収束StudyはTM場比較のままで、別途TEの受入が必要。

一時コピーの追加worker検証44311終了0、out/te-study-worker-candidate-20260909。
TE掃引の実workerをrunningで中止→小さい2点掃引を完了→管理器再起動→全保存確認/Study追跡replayがPASS。
中止した実行は完成FEM数に数えない。candidate reportは完成2点と中止jobを別記録。
既存Study表はnull R/QをNumber(null).toPrecisionで0.000000と表示することを実保存データで確認（gui-null-red.json）。一時コピーのweb/app.jsではN/A理由へ変更し、candidate.patchに含めた。GUI実画面はまだ未検証。
主ツリー452sourceは引き続き不変で、これらは次工程の候補である。

候補GUI69859終了0、out/browser-te-study-candidate-20260909、Chrome2項目PASS。TE2点実FEM/12行のR/Q N/A理由表示、独立スペクトル・収束/追跡未実施の説明、点の保存場取込/描画を確認。study.png目視。実装hashは主ツリーではなく実際に配信した一時コピーを前後照合、外部HTTP要求0。
GUI38921/PID940536はSIGINT終了0。driverと4ファイルcandidate.patchはout/te-study-gui-candidate-20260909に保持。主ツリー452source不変。候補の基本表示確認であり、主ツリー標準・Study全機能の受入ではない。
