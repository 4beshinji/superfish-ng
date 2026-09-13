# O02: 静的Studyの入力・厳密な尺度変換

2026-09-13 JST。固定886sourceを主892sourceへ統合し、静的Study入力と尺度変換の範囲を限定受入。[限定受入計画](STATIC_FIELD_STUDY_INPUT_PLAN.md)と[Study全体の計画](STATIC_FIELD_STUDY_PLAN.md)。

StaticFieldStudyは `superfish_ng_static_field_study`、study_version=1、kind=sweep、基底StaticFieldProject、parameter、2個以上のvaluesを持つ。全11静的Case形式と対応P1/P2を保持し、入力順に独立な各条件Projectを返す。未知の型/フィールド、重複キー、非有限値、RF入力を拒否する。表示m/mmは全CaseのSI値と分離する。

uniform_scaleは正有限値で、原点を中心に元メッシュ節点・外周・穴の全座標を同じ倍率で変更する。三角形・境界edge ID・領域/材料割当、源密度、境界値は保つ。excitation_scaleは符号付き有限値で零を許し、電荷密度またはJz/Jphi密度、固定電位・Az・Aphi/r・psi、外向き電束密度・向き付きHt、反跳材料の局所残留Bを同じ倍率で変更する。axis_symmetryとaxis_regularityへ値を作らない。未知の源/境界/材料の励起規則を黙って無視しない。

epsilon/mu、反跳の主値・材料方向、B-H構成表と来歴を保つ。非線形初期係数と反復条件も元の値を各条件へそのまま渡す。前の解を次の初期値へ利用せず、変更後の固定境界と初期値が矛盾する派生Caseは専用parserで出力予約前に拒否する。入力エラーと、正しいCaseの元FEMで生じる表範囲/反復失敗を区別する。

全派生Caseを保存前に検証し、Study JSONを一時ファイルへの完全書込・fsyncとexclusive publicationで公開する。既存ファイル、途中変更、部分保存を拒否する。normalize-static-study INPUT --out FILEは同じAPIのJSONをファイルとstdoutへ返し、成功0・不正/IO失敗2。入力の正規化をStudyの求解完了として扱わない。実worker・各条件の実FEM結果保存・再検証/GUIは後続工程。

検証は全19 Case次数組合せと2パラメータ/m/mmの完全JSON比較、B-H初期値/条件/来歴、境界Aphi/rを含む全境界種、穴と非零の体積源、非上書き/途中変更・CLIバイトを対象とする。線形静電/磁気/反跳の励起比例・二次積分量の二乗則、固定電位の静電場でPhi不変・E/Dの逆長さ則、平面J/mのエネルギー不変と軸対称Jの長さ比例を、実FEMの元場と解析解で別に照合する。反跳の構成ポテンシャルを磁石の絶対内部エネルギーと解釈しない。B-Hへ線形比例則を適用しない。

最初はStudy未実装で不変量テストを実行できず、その記録を保持した。capability関数の接続前のimport失敗も保持する。接続後の9unitは8合格・幾何尺度の1検証失敗。理論上零の横成分の丸め差を、その微小成分自身で正規化したことが原因だった。別の24組の解析場診断では、元/尺度変更後の差が場全体に対して最大5.968e-14、解析解との差が最大7.398e-14だった。ベクトルの同一単位の成分へ共通の解析場尺度を使い、元と変換後の両方を解析解とも照合する検証へ修正した。rtol=2e-11/atol係数2e-12、FEM・元場・ベンチマークの変更はない。独立の穴/非零源1unitも合格。非現実的な1e308の尺度は、元の幾何parserによる拒否までにoverflow警告を出したが、出力を作らず入力エラーとして拒否した。

独立比較は受入済み33成功Caseから2種類66 Study/165条件を作成し、同じ変換を別のCase構築処理と元FEMの330回で照合する。元の材料/境界/初期値、各条件の全量/実失敗履歴、nativeバイト、API/CLIを保持する。合格結果・固定source・標準回帰・主ツリー統合は受入時に追記する。新規ソルバー・依存・外部資料・旧版実行/コード再利用はない。

1024要素の参照Caseで入力処理を計測し、3条件の生成は基底Projectを毎回検査する方式で8.001秒、一度検査した基底から各条件を独立コピーする方式で6.476秒だった。全派生Caseの完全一致を確認した。条件ごとの専用parserによる検査と所有権は保持し、基底だけの重複検査を削減する。これは一回のローカル測定で、一般的な速度保証ではない。

独立初回は33 Case・66 Study・165対のnativeを出力し、全CaseのDONE記録まで進んだが、最後のcoverage assertionで失敗した。検証側が物理名をelectrostaticと比較し、実際のlinear_electrostaticを選択しなかったため、幾何尺度の検査件数が零だった。初回を合格へ読み替えず、attempt-summary.jsonへ失敗理由と出力件数を記録した。正しい物理名と同一単位のベクトル場尺度へ修正し、固定電位の幾何尺度4条件を必須として別出力で再検証する。この初回の派生165条件は全て求解成功で、実非線形失敗が含まれていたとは扱わない。

候補段階の最終10unitは231.638秒で合格。最終独立比較は537.463秒、33参照Case・66 Study・165条件・330直接FEM対比較・66 CLI、励起比例72点/幾何尺度4点が合格し、元297/新1914ファイルが不変だった。今回の165派生条件は全て求解成功で、実非線形失敗点は零。B-Hの実失敗を含むStudy実行は後続工程で検証する。固定886sourceとして全1417件の標準回帰を開始した段階で、主ツリーへの統合・受入はまだ行っていない。

Study実行/保存・worker/GUI、対象版、O02親と全計画は未完。この限定入力工程を静的Study全体の完了とはしない。

最終独立比較は537.463秒でPASS。全165条件の完全Case/全量・履歴とnativeバイト、66 CLIが一致。全165条件が求解成功。実非線形失敗の検証はworker段階に残し、元297ファイルと新1914ファイル不変。最終証拠はout/static-field-study-input-independent-final-trial-20260913/report.json。検証尺度・対象名の修正前の初回試行は最終coverage assertionで失敗し、合格とはせず保持した。最終の全sourceへの拘束と必須の幾何尺度4点を別出力で確認した。

標準は3778.058秒、1414合格・任意NGSolve参照2件/HTTP環境1件skip、ResourceWarningなし。主7unitは219.970秒でPASS。固定886sourceと主892source（不変egg-info 6件）は完全一致。独立全例を主で再実行したとは扱わない。統合証拠はout/validation-static-field-study-input-candidate-20260913/seed_regression.json。後続は[静的Study workerと各条件保存](STATIC_FIELD_STUDY_JOBS_PLAN.md)。
