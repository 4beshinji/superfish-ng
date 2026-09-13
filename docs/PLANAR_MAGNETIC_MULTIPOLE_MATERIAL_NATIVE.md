# B-H/反跳モデルの多極報告保存・CLI

2026-09-13 JST。固定841sourceを主847sourceへ統合し、専用API範囲で限定受入。

[受入計画](PLANAR_MAGNETIC_MULTIPOLE_MATERIAL_NATIVE_PLAN.md)に従い、元nativeの厳密manifestから平面線形/B-H/反跳の専用readerを選ぶ。成功した元FEMの材料/係数/反復履歴を再検証し、全円板の線形・等方・非残留・無源条件と全4標本系列を検査する。失敗native・軸対称・未知形式は拒否する。5ファイルSHAだけで物理の妥当性を代替しない。

材料モデルの報告は版2として元manifest形式と物理を明示する。線形スカラー報告版1、共通request版1、extract/replay-planar-magnetic-multipolesの2コマンドは維持する。capabilitiesは報告/抽出1・2、元形式3種類、B-H P1と線形/反跳P1/P2、円板の限定を明記する。上書き/出典差/改変/途中変更・不完全出版を拒否し、元nativeを変更しない。

新規6件・既存保存6件・capability3件の15unitが16.246秒でPASS。B-H線形極限、円板外の非線形/異方性/永久磁石、反跳P1/P2、元反復履歴と4系列の保持、元形式/物理/規約/材料主張の改変、再hashした元係数の改変、失敗native/未知形式/欠落/リンク/途中変更と出版中断を検証した。

独立24例は75.162571秒でPASS。前段参照から厳密16例とB-H P1細分8例を選び、元4系列の全JSONを照合。元native120ファイル、72報告と24requestの全216出力、48参照ファイルが不変。API/CLIの全JSONとバイトが一致。98 CLIには新24例の抽出/再検証と従来線形24例の再検証が含まれ、旧72報告と旧192ファイルも不変。従来報告は版1のまま再検証できる。

固定sourceはout/planar-magnetic-multipole-material-native-development-20260913、独立報告はout/planar-magnetic-multipole-material-native-independent-trial-20260913/report.json、標準はout/validation-planar-magnetic-multipole-material-native-candidate-20260913。既存専用nativeの読出しと元FEM/Fourier検証を接続した。新規依存・追加外部資料・旧版実行なし。合成場/材料のみ。GUI、力/トルクとS05全体は未完。

標準2735.945秒、1335合格・任意NGSolve参照2件/HTTP環境1件skip、ResourceWarningなし。主6unitは4.103秒でPASS。標準/独立の固定841sourceと主847source（不変egg-info 6件）は完全一致。独立全例を主で再実行したとは扱わない。旧ベンチマーク・許容差不変。統合証拠は標準出力内seed_regression.json。
