# D02の元要件と明示残件

2026-09-15 JST：[TE対称曲線のアフィン調整・Study](TE_SYMMETRY_AFFINE_WORKFLOWS.md)をAPI/nativeへ接続。
対称面を保つ式全体のゼロせん断を要求し、元セクター順位・保存再開・Eφ/Maxwell尺度を検証。
新4件は分割成功、関連20件と非アフィン2件PASS。専用5成功＋2診断FEM、65ファイル保持。
1 Hz目標の停止と別の1 MHz要求のTUNEDを分離。追加GUI Study12/新旧画面各3項目PASS、2FEM・16配列/全RF一致・57ファイル保持。
調整/逐次/適応の実GUI・CLI専用検証と非アフィン対称接続等は残る。
親33=10/16/6/1、全計画goal ACTIVE。

2026-09-15 JST：[TE曲線の対称領域・鏡映比較](TE_CURVED_SYMMETRY_TRACKING.md)の基盤を限定検証。
同一二次領域/せん断なしアフィンのEφ追跡、元対称セクターの順位、native再生を接続。
新3件18.547秒、関連27件39.086秒と14件6.134秒がPASS。専用半領域8 FEMと全領域dense4計算、104ファイル保持。
曲線対称/鏡映のtune・Study・非アフィン比較への接続は残る。親33=10/16/6/1、全計画goal ACTIVE。

2026-09-15 JST：[TE調整版8のGUI/CLI・個別ID回復](TE_PARTITION_TUNING.md)を追加検証。
Chrome12項目・関連14unitがPASS。専用9実FEM、5組nativeの30配列/全RF一致、99ファイル保持。
2モードの宣言集合から実EφでIDを回復し、回復失敗時の周波数未評価・停止も保存再生で確認。
全3GUIジョブ・全handle終端。曲線対称/鏡映・他物理/D03等は残り、親33=10/16/6/1、全goal ACTIVE。

2026-09-15 JST：[TE分割切替調整版8](TE_PARTITION_TUNING.md)を直接閉PEC・固定RFでAPI接続。
新3unitは分割証拠で成功、関連26件44.420秒PASS。粗いG/周波数差と比較予算の失敗も保持。
曲線26/27初期分割の原寸/倍寸調整と保存再生が合格。専用成功7＋診断8実FEM、場/RF尺度差最大3.23420e-14。
54ファイル保持、全handle終端。実GUI・ID回復・曲線対称/鏡映・他物理/D03は残り、親33=10/16/6/1、全goal ACTIVE。

2026-09-15 JST：[TE逐次/適応Studyの実GUI](TE_TRACKED_STUDY.md)を限定検証。
Chrome逐次8/適応11項目、完了再生は新ブラウザー各1項目で補強。GUI関連6unitもPASS。
専用7実FEM、7組nativeの42配列/全RF一致、144ファイル保持。全6ジョブ・全handle終端。
他TE形状/対称セクター/回復例、TE版8・曲線対称/鏡映・他物理/D03は残る。親33=10/16/6/1、全goal ACTIVE。

2026-09-15 JST：[TE逐次・適応Studyのnative読取](TE_TRACKED_STUDY.md)を接続。
新2件を含む24unitが76.496秒でPASS。逐次CLIは停止/再開後COMPLETE、既存独立掃引との2組全配列/RF一致。
適応CLIは初回BISECTから再開し、10点/17試行で元終点まで到達。専用計12実FEM。
実GUI・その他のTE形状/セクター/回復例、TE版8・曲線対称/鏡映・他物理/D03は残る。
親33=10/16/6/1、全goal ACTIVE。詳細と保存再生の検証範囲はリンク先を参照。

2026-09-15 JST：[TEアフィンStudy](TE_AFFINE_STUDY.md)を直接閉PEC・固定RFで限定受入。
新規を含む23unit、GUI実経路12項目、説明修正後の定義/画面3項目がPASS。専用4実FEM。
2組nativeの12配列/全RF一致、57ファイル保持、Maxwell場/RF尺度差最大8.990e-15。
完了StudyのEφ追跡は接続済み。逐次/適応の実計算は未接続、版8・曲線対称/鏡映・他物理/D03も残る。
親33=10/16/6/1、全計画goal ACTIVE。以下の未完表記は各段階の履歴。

2026-09-15 JST：[TEアフィン調整版4](TE_AFFINE_TUNING.md)のGUI/CLI・場/RF追加検証を限定受入。
アフィン係数の重複JSONキーを元テキストのままサーバーへ渡し、FEM前に拒否する修正も実施。
Chrome TE12/TM10項目、GUI関連5件PASS。専用比較21実FEM＋解像度/目標pilot3実FEM。
7組native全配列/RF一致、元108ファイル保持。TE affine Study・版8・曲線対称/鏡映・他物理/D03等は残り、全goal ACTIVE。


2026-09-15 JST：[TEアフィン曲線調整版4](TE_AFFINE_TUNING.md)を固定RF契約でAPI接続。
Eφのアフィン/同一曲線領域比較、native保存再開、Maxwell周波数則とせん断体積比を検証。
新2件は分割で成功、関連35件134.814秒PASS。実GUI・追加場/RF尺度・TE affine Studyは後続。
版8・曲線対称/鏡映・実ID回復例・他物理/D03を保持し、全計画goal ACTIVE。


2026-09-15 JST：[曲線TE調整版5/7](TE_CURVED_TUNING.md)の実GUI・場/RF追加検証がPASS。
直接閉PEC・固定RFメタデータ・凍結履歴の範囲を限定受入。Chrome多項式14/exp式11項目、専用21実FEM。
原寸/倍寸/4倍エネルギー、全係数・全要素の場・RF/PEC積分尺度を分離検査。8組native全配列/RF一致、元108ファイル保持。
版4/8・曲線対称/鏡映・実ID回復例・他物理/D03は残る。親33=10/16/6/1、全goal ACTIVE。


2026-09-15 JST：[曲線TE調整の固定RF契約](TE_CURVED_TUNING.md)を多項式版5・式版7へ接続。
TEでは加速区間を追加せず、形状変形・凍結履歴・Eφ比較・最終細分・保存再開を保持。
新3件の分割検証と関連34件482.550秒がPASS。独立Green積分、専用TE Study2実FEMも確認。
実GUIと追加場/RF尺度検証は未実施。版4/8・曲線対称/鏡映等を保持し、全goal ACTIVE。


2026-09-15 JST：[曲線TEの宣言比較写像](TE_CURVED_TRACKING.md)をpiecewise_remesh版2/3/4/5へ接続。
実Eφと可変体積重みを保持し、非アフィン変形・独立積分・Maxwell尺度・native再生を検証。
型検査順と共通参照分割のTE入口を修正、最後の関連22件がPASS。旧TM保存互換も照合。
閉PECの直接曲線P2が対象。曲線TE tune、曲線対称/鏡映、他物理/D03は残り、全goal ACTIVE。


2026-09-15 JST：[TE一般profile調整](TE_PROFILE_TUNING.md)をnormalized_profileへ接続。
非円筒の連動寸法・局所半径式、閉PEC/半領域/鏡映、保存再開と最終粗細判定を検証。
新2件51.729秒＋関連48件94.247秒PASS。専用尺度8FEM、Chrome11項目/4FEMがPASS。
5組native全配列/RF一致、元81ファイル保持。曲線TE・他物理調整とD03は残り、全goal ACTIVE。


2026-09-15 JST：[TE一般profile追跡](TE_PROFILE_TRACKING.md)の体積重み付きEφ写像を追加。
閉PEC・同端条件の一対称面・鏡映に対応。解析積分、P1/P2左右両対称条件、保存再生、実FEM尺度則を検証。
関連40件は39成功＋失敗入力修正後1成功の分割証拠。専用4実FEMもPASS。
一般profileのtune接続と曲線TEは残る。D02と全計画goalは継続中。


2026-09-15 JST：[TE円筒チューニング](TE_TUNING.md)を同端条件の直線円筒へ接続し、限定受入。
EφによるID、半領域・鏡映の元セクター順位、加速量N/A、保存再開・回復・最終粗細ゲートを保持。
関連53unit（52＋1の分割実行）、専用44実FEM、Chrome閉PEC9/鏡映11/旧TM9項目がPASS。
8組native全配列/RF一致、元114ファイル保持。一般TE形状・他物理調整とD03は残る。
親33=10受入/16進行/6他未受入/1範囲外、D02と全計画goalは継続中。


2026-09-15 JST：[曲線分割切替tune版8](PARTITION_TUNING.md)を実装・宣言分割方式で受入。
初期接続/PEC境界分割/履歴の異なる候補を実値から選び、式変形・実FEM・比較版5・保存再開/ID回復へ接続。
関連36unit、専用39実FEM、Chrome新10/旧9項目がPASS。8組のnative全配列/RF一致、元124ファイル保持。
親D02の他物理調整とD03一般制約付き探索は残り、親33=10/16/6/1、全計画goal ACTIVE。


2026-09-15 JST：[単位付き式によるtune版7](EXPRESSION_TUNING.md)の追加実経路検証がPASS。
Chrome profile9/曲線9/旧版7項目、曲線Maxwell RF/場尺度則、指数軸長の実ID回復・再開/拒否を確認。
追加58実FEM、全9GUIジョブ終端、取り込み3場の全配列/RF一致、元29ファイル保持。
親D02の境界分割変更・他物理は残り、親33=10/16/6/1、全計画goal ACTIVE。


2026-09-15 JST：D02の[単位付き式によるtune版7](EXPRESSION_TUNING.md)をprofile/曲線の実形状生成へ接続。
実FEM円筒調整・保存再開・途中定義域エラー保持、非アフィン曲線の独立面積/体積則を検証。
GUIコードも追加したが、実ブラウザーと曲線の専用RF/場検証は残る。親33=10/16/6/1、全計画goal ACTIVE。


2026-09-15 JST、開始HEAD `7061866`。親D02は進行中のまま。
原`e6271c2:docs/COMPATIBILITY_PLAN.md`のD02は、変数/範囲/目標/停止条件、
メッシュ差と周波数許容差の分離、追跡付き1変数tuneと再開履歴、無効形状/失敗処理、
円筒の寸法–周波数解析、モード切替拒否、最終細メッシュ再計算を要求する。

これらの基本経路はTUNING、POLYNOMIAL_TUNING、CURVED_TUNING、CURVED_HARMONIC_TUNING、
TUNING_IDENTITY_RECOVERYで実装されている。D01は元要件監査を終えて受入済み。
ただしBACKLOGのP2-02行と個別仕様が明示した次の残件を保持する。

| 明示残件 | 現状 | 次の処理 |
|---|---|---|
| 任意関数・非多項式の連動 | 要求版7で宣言式をprofile/曲線へ接続。実FEM、単位/定義域、保存/CLI/worker/GUI、独立指数例と回復を検証済み | 宣言した式構文の範囲をEXPRESSION_TUNINGに保持し、境界分割変更へ進む |
| 境界分割変更を含む調整 | 版8で実値に依存する明示分割候補と式変形を実FEM・比較版5・保存/再開/ID回復/GUIへ接続済み | 宣言分割方式をPARTITION_TUNINGに保持し、他物理調整と親要件を照合する |
| 他物理の調整 | 同端条件TE円筒/profileと直接閉PEC曲線の版4/5/7は接続・限定検証済み。TE affine Studyの独立掃引/完了追跡も接続済み。逐次/適応のアフィンTE実計算・CLI停止再開も接続済み。アフィンTEの実GUIも検証済み。直接閉PECのTE版8 API/保存再開も限定検証済み。版8実GUI/CLI・宣言集合からのAPI回復も検証済み。曲線対称/鏡映の同一領域・せん断なしアフィン比較とProject変換は限定検証済み。アフィンtune/StudyのAPI・保存再開は限定検証済み。独立Study実GUIも限定検証済み。調整/逐次/適応の実GUIとCLI、非アフィン対称比較、他TE形状/回復例、階段形状と未接続物理は残る | 曲線TEのEφ写像・重みと独立不変量を先に定義し、各物理の周波数/ID/単位と元要件を照合する |
| 一般形状の制約付き探索 | D03の実装と受入が別途必要 | D02完了の代わりとして数えず、D03の元要件へ対応付ける |

今回の限定課題は[非多項式の式評価](SCALAR_EXPRESSIONS.md)。式を保存可能な厳密な木として宣言し、
単位・定義域・予算を検査する。解析式から周波数を返す機能にはしない。
親33=10受入/16進行/6他未受入/1範囲外、全計画goalは継続中。
