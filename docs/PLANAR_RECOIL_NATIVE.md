# S03: 平面の反跳材料の保存・再構築・CLI

2026-09-13 JST。固定761sourceを主767sourceへ統合し、専用API範囲で限定受入。

[限定計画](PLANAR_RECOIL_NATIVE_PLAN.md)の5ファイル保存とsolve/replay/probe-planar-recoilを実装した。元Caseと全材料テンソル/残留B/向き、所有/界面/面積、電流/残留/境界荷重、自由/固定DOF、基準と相対/絶対Azを保存する。同じ実FEMの再求解と元セル評価で、元5場・三荷重・電流/磁束/反力・全構成ポテンシャルと規約を照合する。

manifestを最後に公開し、既存出力・不完全ファイル・symlinkを拒否する。入力と結果を単に再hashした改変も物理の再構築で拒否する。能力表のplanar_recoilは有限境界の専用API/CLIとして公開し、GUI/Project/Studyは未対応とする。Az/B/Hと二つの構成ポテンシャルの基準を保持し、一般名の絶対磁石エネルギーへ変換しない。

追加4unitは3.750秒でPASS。P1/P2の二材料/二層/零場、凸/凹の二次対照の8保存を使い、テンソル・残留B・向き・三荷重・所有・dtype・係数/参照・各構成ポテンシャル・境界/磁束/反力・規約・manifestの改変と公開中断を検査した。片側プローブのHは返却されたmuテンソルとB−Bremから別に解いて照合した。旧能力表3unitと3CLIスモークもPASSし、API/CLIの5ファイルと全プローブJSONが一致。

独立24例48native/80CLIと標準1223件がPASS。元240native/98参照ファイルは不変。証拠はout/planar-recoil-native-independent-20260913/report.jsonおよびout/validation-planar-recoil-native-candidate-20260913。固定候補は編集しない。新規依存・外部資料・旧版実行なし。軸対称・対象版の材料モデル確認、S03/全計画は未完。

独立24例は28.722秒でPASS。標準2422.683秒、1220合格・任意NGSolve参照2件/HTTP環境1件skip、ResourceWarningなし。主4unitは3.738秒でPASS。標準/独立の最終固定761sourceと主767source（不変egg-info 6件）は完全一致。候補hashに結び付く独立例を主で全再実行したとは扱わない。旧ベンチマーク・許容差不変。統合証拠は標準出力内seed_regression.json。
