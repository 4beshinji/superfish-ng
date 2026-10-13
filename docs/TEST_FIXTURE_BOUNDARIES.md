# Hφ調整テストのfixture境界（RF-08）

2026-10-14 **RF-08 DONE**。RF-05受入後に検証済み21 test moduleと六新規support/入力test fileを主ツリーへ反映した。

最初の対象はHφ調整worker/保存/GUIで再利用する要求生成と、同じ要求が利用する曲線形状。
`tests/support/`へ元の四生成関数を移し、21 test moduleの18か所のテスト間importを
直接fixtureへ向けた。直線、曲線、材料の要求を専用moduleに分け、材料の独立参照を
直線/曲線fixtureがimportする必要をなくした。元の`request`/`coax`はimport aliasで残る。

| fixture | 内容 | 依存境界 |
|---|---|---|
| hphi_tuning_fixtures | 直線workerの元同軸要求 | Case/Project/controls生成、求解なし |
| curved_hphi_geometry | 元宣言二次同軸形状 | 元node/cell/edge/写像のみ、求解なし |
| curved_hphi_tuning_fixtures | 曲線所有保存の元要求 | 上記形状と物理宣言、求解なし |
| material_hphi_tuning_fixtures | 材料二層の元要求 | 既存scripts.material_hphi_reference、FEM求解なし |

独立参照は既存scriptに残す。`material_hphi_reference.py`/`validate_coaxial.py`と
製品sourceはRF-08内でbyte不変で、製品の新しい共通数値helperへ依存を追加していない。
生成関数のsignature/default/bodyは改名以外AST一致、21 moduleの全元関数/TestCase bodyは
完全一致。26組の旧新要求/形状canonical byteも一致した。元の期待値、拒否条件、形式、
状態/場/ID/RFの検査と2689個別test IDを全て維持し、新しい入力専用3 IDを追加した。
現在のrunner収集は2692 ID/529 module。テスト削除や重複FEM実行の削減は行っていない。

検証の選択を次のように分ける。環境は既存uv runner/Python3.12、BLAS thread1。

| 選択する証拠 | unittest対象 | 実行/範囲 |
|---|---|---|
| 三系worker入力の全3形式 | test_owned_tuning_input | 3件。全三系solverを禁止し、元入力受理/不変、別物理、未知キー、版/bool/非有限/予算を検査 |
| 収集/skip/失敗/中断伝播 | test_parallel_test_runner | 6件。実子processでserial/parallel、class fixture、skip/expected failure、import/異常終了/子中止、既存出力保持 |
| 実保存/再開/全量比較 | test_hphi_tuning_saved、test_curved_hphi_tuning_saved、test_material_hphi_tuning_saved | 15件。実native/Project/全RF、pause/resume、移動、失敗prefix、改変/リンク/要求差替え拒否 |

上記24個別unitは入力/runner9件が5.365秒、保存15件が195.481秒、全て終了0/PASS。
runnerテスト内部の意図したskip/failed childと、製品検査自体の成功を混同しない。
worker/GUIの実cancel・管理器再生成・保存地点選択はRF-04の20個別証拠を保持する。
今回移したfixtureの元body/生成byteとTestCase bodyが一致することを結合し、同じ状態遷移を
証拠更新だけのために再実行していない。新しいブラウザー受入/全solver性能比較ではない。

rawは`out/rf08-fixtures-20261014/`、実行rootは
`/tmp/superfish-rf08-fixtures-20261014`。`fixture-compatibility.json`に全ID、生成byte、
TestCase/参照/sourceを束縛した。監査初稿の元geometry namespace不足は保全し、
正しい元依存を渡して修正した。製品/testの許容差変更で監査を通していない。
時間は実行記録であり、速度改善を主張する比較測定はしていない。

主ツリー反映時に候補の全byteと他1473 sourceの不変を確認した。
`acceptance.json`が元全ID/fixture/参照、24個別unit、反映前後sourceとraw SHAを結合する。
