# 多極抽出結果の保存・元native照合・CLI

2026-09-13 JST。固定836sourceを主842sourceへ統合し、専用API範囲で限定受入。

[受入計画](PLANAR_MAGNETIC_MULTIPOLE_NATIVE_PLAN.md)に従い、元の平面線形磁場nativeから多極結果を保存・再検証するAPIとCLIを追加した。厳密なframe/次数/標本数のrequest、元5ファイルのSHA256、元FEM抽出の全4系列・係数・診断を完了JSONへ保持する。元nativeを読み取り専用の出典とし、再検証には同じ内容のnativeを明示的に指定する。出典の自動探索や保存場所への暗黙依存はない。

CLIはextract-planar-magnetic-multipoles RUN --request REQUEST --out REPORTとreplay-planar-magnetic-multipoles RUN REPORT。成功0、不正入力/上書き/改変/出典不一致2。保存はnative外へ、一時JSONからリンクで完了出版する。出典不一致、未知キー/型・原係数/標本/円板/規約/診断の改変、シンボリックリンク、途中変更と出版中断を拒否する。保存物のSHAだけでなく、元FEMと全Fourier結果の再計算を照合する。

最初の追加6unitは6.925秒、出典差の検査1件で失敗した。比較用に指定したoffset=.125がfixture既定値と同じだったためであり、異なるoffset=.25へ修正した。製品コードや許容差は変更しない。失敗ログ/修正前テスト/判断はout/planar-magnetic-multipole-native-development-20260913に保持。修正後6unitは5.500秒、既存capability3unitは6.637秒でPASS。

独立24例は47.709345秒でPASS。前段の解析/細分参照から双極/厳密四極16例とP1細分8例を選び、元の全4系列を完全一致で照合した。各元nativeの5ファイル、APIの2報告とCLIの1報告を保持し、API/CLIの全JSONとバイトが一致。再検証を含む74 CLI、元native120ファイル、72報告/24requestの全216出力と48参照ファイルが不変。純粋な複製nativeは出典として受理し、異なるCaseのnativeは拒否した。

固定sourceと判断はout/planar-magnetic-multipole-native-development-20260913、独立報告はout/planar-magnetic-multipole-native-independent-trial-20260913/report.json、標準はout/validation-planar-magnetic-multipole-native-candidate-20260913。専用capabilitiesは版付きrequest/report/series/extraction、2コマンド、線形スカラーP1/P2の範囲とGUI/Project/Study未対応を明示する。

元の線形FEMと自前出版方式を接続した。追加外部資料・新規依存・旧版実行なし。合成解析場のみ。GUI、反跳/B-Hモデルの対象拡張、力/トルクとS05全体は未完。

標準2718.746秒、1324合格・任意NGSolve参照2件/HTTP環境1件skip、ResourceWarningなし。主6unitは5.434秒でPASS。標準/独立の固定836sourceと主842source（不変egg-info 6件）は完全一致。独立全例を主で再実行したとは扱わない。旧ベンチマーク・許容差不変。統合証拠は標準出力内seed_regression.json。
