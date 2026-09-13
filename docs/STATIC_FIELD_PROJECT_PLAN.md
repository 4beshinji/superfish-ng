# O02: 静電場・静磁場の専用Project入力契約

2026-09-13 JST。[実装記録](STATIC_FIELD_PROJECT.md)の専用入力契約を限定受入。[O02](COMPATIBILITY_PLAN.md)の追加物理をProject/Study/GUIへ渡す工程の最初の限定課題。

対象は受入済みの11種類の専用Case：軸対称/平面の線形静電、平面/軸接続/軸非接続の線形磁静、同3座標系の線形反跳材料と等方非線形B-H。各Caseの厳密format/schema/physicsと既存parserを保持し、新しい汎用RF Caseへ読み替えない。

StaticFieldProjectは専用format=superfish_ng_static_field_project、project_version=1、case、display_length_unit=mまたはmmを持つ。表示長さ単位は編集表示の選択だけであり、保存CaseのSI座標・材料値・電流/電荷・境界/基準ポテンシャル・求積次数・B-H初期値/反復条件を変更しない。幾何/材料/境界の既存制約は各専用parserで引き続き検査する。未知のProject/Case/材料フィールド、型違い・重複キー、RF入力と未知physicsを拒否する。

bareの専用CaseまたはProjectからの読込、JSON往復、非上書きの完全Project公開とCLI normalize-static-project INPUT --out OUTPUT（任意の--display-length-unit m/mm）を提供する。完了0、不正/保存エラー2。これはProjectの作成/検査であり、場の正規化やFEM求解を行わない。有効な入力が後で非線形求解に失敗する可能性も、Project作成の成功と混同しない。

受入は全11形式、対応P1/P2、二つの表示単位、全領域/穴/材料/向き/境界/求積・B-H来歴/初期値の完全往復、未知項目/重複キー/型違い拒否、入力不変、上書き/中断拒否、API/CLI全JSON/バイト一致。独立に検証済みの実FEM入力をProjectへ通した後も、元Caseと同じ専用ソルバーへ渡して元結果が一致することを確認する。既存RF Projectと磁気報告の入出力も維持する。

この工程は入力契約だけの限定受入。静的Projectの実worker/成功・非線形失敗保存・CLI求解、GUIでの入力/求解/描画、Studyは後続のO02子課題とし、このProject追加でO02親や全計画を完了扱いにしない。新規依存やsolve時の外部接続は導入しない。
