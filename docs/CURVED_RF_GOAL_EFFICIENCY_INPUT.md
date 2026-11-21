# RF版5対照の固定計画・要求検査

2026-10-13 JST、`ADD-N04-rf-goal-02` **DONE**。
[仕様01](CURVED_RF_GOAL_EFFICIENCY_SPEC.md)の固定36行を検査し、実行方式ごとの厳密な要求を導出する。
新規モジュールは`src/superfish_ng/curved_rf_goal_efficiency_plan.py`。
元N05計画・公開版4/5・FEM・RF・指標・停止条件を変更しない。
新参照package、worker、全費用計測、36実行、保存GUI/親N04受入は03〜06である。

## 入口と返却値

| API | 入力と結果 |
| --- | --- |
| `build_curved_rf_goal_efficiency_plan` | 配布済みの固定planと四原入力・六要求を再検査し、13項目/36行のplanを新しいobjectとして返す |
| `validate_curved_rf_goal_efficiency_plan` | 呼出し側planの全階層key/厳密型/値/順序を固定planへ照合し、検査済みコピーを返す |
| `parse_curved_rf_goal_efficiency_plan` | raw JSONの全階層重複・構文を検査し、同じ全plan検査へ渡す。非有限/巨大数、bool/intやint/floatの取り違えを拒否 |
| `request_for_curved_rf_goal_efficiency_execution` | 固定36行の全項目に一致する一行から、その方式のCase/初期mesh/全ID付き要求を新しいコピーとして返す |

全APIの任意keyword `base_directory`は固定入力を置くrepository根で、既定値は現checkout。
計画fixture自体をmodule内のSHA256とbyte数で固定し、呼出し側がmanifestを再hashしても
受入済み入力を置換できない。別計画は別のレビュー・source更新を必要とする。
要求pathの宣言を比較し終えるまで、呼出し側のpathを開かない。

全11ファイル（plan＋四原入力＋六要求）を通常ファイル/SHA/byte数で検査する。
ディレクトリをdescriptorから`O_NOFOLLOW`でたどり、途中のsymlinkも拒否する。
最終fileは非blockingで開いて通常fileであることを確認するため、FIFO待機やdirectory読取も拒否する。
これは既存費用supervisorと同じPOSIX環境の比較用入口で、今回のLinux実機で確認した。
必要なdirectory/no-follow機構がない環境はactionableなValueErrorとなり、弱いpath検査へfallbackしない。

元四入力から球/長球/丸めの要求を照合する。球のcell上限250000は元N05の明示条件で、
配布済み球例の20000からの変更を隠さない。長球の12event/100000cellはそのまま。
球/長球の元暗黙meshは仕様01で保存したSHA固定の明示meshを使い、検査で再生成しない。
丸めは元N05の全Case・明示mesh、targetと二guardを保持する。
二尺度の全座標/長さとU=a² Jを原要求から導出して照合し、全六要求を公開版5validatorへ通す。
この検査には元Case・全tag付きmeshの厳密な物理/幾何入力検査が含まれる。

一様方式だけはsurface_refinement_policyを取り除いてschema4とし、公開版4validatorで確認する。
RF二方式はschema5のpolicyを各行の明示値にする。他のCase/mesh/ID/求積/許容/予算は保持する。
要求の導出・公開検査の後に全11ファイルを同じpath規則で再読取/再hashする。
返却後の変更は別返却値やcaller入力へ伝播せず、後続呼出しで以前の検査をcache再利用しない。

## 確認した条件

新`tests/test_curved_rf_goal_efficiency_plan.py`の12個別unitと直接利用先6件が全てPASS。

| 新検査群 | 確認した範囲 |
| --- | --- |
| 固定計画/方式 | 全36のID/順序・二反復・三方式、最大336event、NOT_RUN/null維持。全36要求を公開版4/5で再解析し元Case/mesh/全IDと一致 |
| SI相似/元規約 | 三形状の全初期座標が正確に2倍、全接続/辺/タグ不変、有効加速長/電圧区間2倍、規格化は尺度1で1 J・尺度2で4 J |
| 厳密JSON/型 | 二深度の重複、NaN/Infinity/overflow/6000桁integer/深すぎるJSON/不正構文/非text、13項目とnested key/型/許容/policy/ID/状態の拒否 |
| 全行/入力コピー | 欠落/追加/並べ替え/重複/tupleを各listで拒否。IDだけが一致しても改変行を拒否。返却plan/mesh/Caseとcallerの非alias |
| 元byte/改変 | 全11fileの変更/欠落を公開要求検査前に拒否。mesh座標とbindingを再hashしたplan、plan自体の置換も拒否 |
| path/検査中変更 | `..`/絶対/空/非canonical path、file/親directory/rootのsymlink、FIFOを拒否。公開検査中の原入力変更を最後の再読取で拒否し、復元後の新呼出しは成功 |

新検査はsolver、実eigsh、公開版4/5のsolveとmesh生成を禁止するguardの下で実行した。
独立Green/別P2積分・4/8/32尺度の科学的証拠は、元六要求と全旧源byteが同じ
[仕様01のprobe](CURVED_RF_GOAL_EFFICIENCY_SPEC.md#仕様段階の確認と来歴)を再利用する。
新しいFEM/RFの数値変更はなく、新物理精度の受入は行っていない。

直接利用先は旧`test_adaptive_efficiency_plan`の全5件と、公開版5の
`CurvedRFAdaptiveTests.test_strict_request_and_event_budget`の1件。
旧N05の全Case/元mesh/12行/コピー隔離/改変拒否と、旧版5の要求/event予算を維持した。
参照/保存/費用/GUIに関する仕様上の拒否例は後続03〜06の条件であり、この18件へ含めない。

## コマンド・raw・来歴

rawは`out/n04-rf-goal-input-20261013/`。実装前の一件はmodule未実装ImportErrorで終了1、
`before-implementation.log`を保全した。実装後は次を一度実行し、
**18件、10.751秒、終了0、OK**（handle60298、実終端確認済み）。

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-uv-cache \
  uv run --no-sync python -m unittest -v \
  test_curved_rf_goal_efficiency_plan \
  test_adaptive_efficiency_plan \
  test_curved_rf_adaptive_refinement.CurvedRFAdaptiveTests.test_strict_request_and_event_budget
```

`source-before.json`は元1468対象源を固定する。新module/testの2源だけを追加し、
元全1468源のbyte不変を監査する。原入力・仕様01の固定plan/六要求は変更しない。
新FEM/seed/full/専用物理validator/GUI/legacy/外部取得/依存追加は0。
標準ライブラリのunittestを使用し、ソルバー共有核を変更していないためfull/seedは不要。
源・元log・全固定入力と受入台帳を`acceptance.json`へ結合する。
初稿receiptのtest ID末尾重複は元receipt/script/logを別名で保全し、
元unittestログの完全IDと各testのASTを照合して訂正した。製品コード・検査結果は変わらず、再試験は行わない。

全141カードは90 DONE/2 IN_PROGRESS/49 PLANNED。原123は76/2/45のまま。
次は`ADD-N04-rf-goal-03`の独立全域参照package。親N04と全goalは継続する。
