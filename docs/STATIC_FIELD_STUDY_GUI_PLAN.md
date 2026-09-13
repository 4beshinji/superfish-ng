# O02: 静的StudyのGUI入力・実行・各条件表示

2026-09-13 JST。[実装記録](STATIC_FIELD_STUDY_GUI.md)の専用Study GUI範囲を限定受入。[Study実worker](STATIC_FIELD_STUDY_JOBS_PLAN.md)に続く[静的Study全体](STATIC_FIELD_STUDY_PLAN.md)のGUI接続。

専用Study JSONの読込・編集・厳密検査・非上書き取得を既存のStaticFieldStudyへ接続する。全11形式の基底Project、uniform_scale/excitation_scaleと入力順、表示m/mm、元の全材料/境界/初期値/反復条件を保持する。求解は既存の専用Study実workerを使用し、HTTPやJavaScriptでFEM/派生Caseを別実装しない。

親Studyの実行状態と全点成功/失敗数、各点の値と成否を別に表示する。成功点は元の専用FEMによる各材料セル中心の場・全SI量とCase、失敗点は元の全停止履歴を表示し、失敗に場を作らない。表示単位、平面の単位長量と軸対称の全周量、零中心配色・元標本位置/表示近似、RF量N/Aを維持する。値の順序を枝追跡や収束系列と呼ばない。

初回と再起動時に全Study/各条件の元FEM・manifestを非同期で再検証し、検証前や改変後の結果を表示/取得しない。Studyと各点Project、元native、全Study結果を元バイトで取得できるようにする。成功点と実失敗点の切替、別Studyへの切替、RF履歴からの正しい専用画面誘導を確認する。中止/強制終了/未完を完了Studyとして表示しない。

受入は全11形式/対応次数・両パラメータ、API/CLI/実workerとの全量・単位・元場/失敗履歴・バイト一致、厳密JSON/符号付き零、全点の選択・描画・保存、実ブラウザーの初回/サーバー再起動・中止/強制終了/改変拒否。B-Hの成功と実失敗を含むStudy、既存の単体静的ProjectとRF/磁気報告の操作も確認する。ローカルブラウザー/目視の証拠をユーザー業務評価や対象版互換性へ拡張しない。

この工程の後に[O02原要件照合](O02_ACCEPTANCE_PLAN.md)で受入証拠を監査する。対象版C00.Vが未確認なら親/全計画の完了を宣言しない。新規数値モデル・依存・外部サービス・旧版コードの利用は追加しない。
