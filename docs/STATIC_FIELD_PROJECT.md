# O02: 静的Projectの入力・保存・CLI

2026-09-13 JST。固定874sourceを主880sourceへ統合し、専用入力契約の範囲で限定受入。[受入計画](STATIC_FIELD_PROJECT_PLAN.md)。

StaticFieldProjectはsuperfish_ng_static_field_project/project_version=1の専用文書。軸対称/平面静電、平面/軸接続/正半径の線形磁静・反跳・B-Hの11種類を、それぞれ既存の厳密Case parserへ渡す。線形/反跳P1/P2、B-H P1という元の対応範囲を保持する。CaseのSI値を保持し、display_length_unit=m/mmは表示選択だけを保存する。

bare Case/Projectのload/from_dict、dumps/to_dict、非上書きのsaveを提供する。全JSONを一時ファイルへ書いてflush/fsyncし、公開直前にProjectの変化を検査してから同じディレクトリ内のhard linkで完全ファイルを公開する。既存出力・リンク先を上書きしない。CLI normalize-static-project INPUT --out OUTPUTは同一JSONを標準出力にも返す。表示単位の明示変更は--display-length-unit mまたはmm。成功0、不正/保存失敗2。正規化は入力文書の構成だけで、物理量のスケーリングやFEM求解を意味しない。

単体6件と既存capability 3件が合格。11形式/対応次数の19 Caseとm/mm、厳密未知項目/型/重複キー拒否、入力の所有コピー、B-H初期係数・反復条件・材料来歴、非上書き/中断/途中変更を検査した。元CaseとProject経由の全実FEM結果、およびCLIの全JSON/バイトが一致した。既存3種類のRF Projectを保持し、静的Projectとの混同を拒否する。

独立検証は受入済みnativeから各形式3例、計33元Caseを選び、元nativeを実FEMで再検証したうえでm/mmの計66 Projectを実際に再求解する。API往復・bare Case/ProjectからのCLIによる264 Projectと、再計算による330 nativeファイルの全バイトを照合する。元165ファイルを保持する。結果・時間・固定source一致と標準回帰は受入時に追記する。

先行する機能欠如は、既存Caseを正しく読み込めてもStaticFieldProjectが存在せずModuleNotFoundErrorとなること。独立検証の初回は検証側が軸対称静電partition.meshを他形式のpartition.geometryと取り違えてKeyErrorになった。既存形式に沿って検証の参照選択だけを修正し、失敗ログ/出力を保持した。数値実装、入力、許容差、ベンチマークは変更していない。

この工程は入力契約だけを対象とする。実worker/成功・失敗保存/CLI求解は[次工程](STATIC_FIELD_JOBS_PLAN.md)、GUI描画・編集・Studyは後続。O02親や全計画は未完。新規依存・外部資料・旧版コード/実行の再利用なし。

独立比較は125.550秒、134 CLI、全594出力/元165ファイル不変でPASS。標準は3369.590秒、1395合格・任意NGSolve参照2件/HTTP環境1件skip、ResourceWarningなし。主6unitは32.636秒でPASS。標準/独立の固定874sourceと主880source（不変egg-info 6件）は完全一致。独立全例を主で再実行したとは扱わない。統合証拠はout/validation-static-field-project-candidate-20260913/seed_regression.json。
