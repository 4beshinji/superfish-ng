# O02: 静的Studyの入力と厳密な尺度変換

2026-09-13 JST。[入力/尺度変換の実装記録](STATIC_FIELD_STUDY_INPUT.md)の限定範囲を受入。[静的Study全体](STATIC_FIELD_STUDY_PLAN.md)の最初の限定課題。全体のAPI/CLI/worker/GUIと各条件保存の完了要件は維持する。

専用StaticFieldStudyとnormalize-static-studyを追加する。全11 Case形式・対応P1/P2を基底StaticFieldProjectと二つの明示パラメータへ接続し、元Caseの対応する全座標、源密度、固定ポテンシャル/Neumann・Ht境界値、反跳残留Bを変換する。uniform_scaleは正有限、excitation_scaleは符号付き有限値（零を含む）。入力順を保持し、全派生Projectを保存前に専用parserで検証する。未知のフィールド、重複キー、RF入力、非有限値を拒否する。

元Case/Projectと表示m/mm・材料構成/方向/来歴を保持し、B-H初期係数と反復条件を自動調整しない。変更した固定境界に初期値が適合しない派生Caseは入力エラーとして出力予約前に拒否し、元FEMによる表範囲/反復失敗とは区別する。専用形式と解釈・対象外の追跡/収束をcapabilityと文書で示す。

受入は全形式・次数の完全派生Case/JSONと非上書き保存、API/CLIの全バイト一致。線形静電/磁気/反跳に対する励起比例・エネルギー二乗則と固定電位静電の幾何尺度則を、実FEMの元場標本/積分量で検査する。符号・零と全境界種、穴/領域/材料方向・来歴、B-H初期値保持/不適合拒否を別に確認する。基準許容差や専用FEMは変更しない。

この入力段階の完了をStudy実行/worker/GUIの完成として扱わない。後続は同じ各条件Projectの実FEM・成功/実失敗native保存と実worker/API/CLI/GUI接続。対象版、O02親と全計画は未完。
