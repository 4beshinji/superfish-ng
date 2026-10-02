# 区分形状の実調整と全試行所有保存（P04-b-b）

2026-10-02、基準 `afd6fdd`。本カードは新版要求の実runner、全trial所有保存、可搬再生、新所有先への再開を対象とする。queued時の先行trial所有、実worker中止/管理器再起動と親P04-b監査はP04-b-c、GUI/親P04監査はP04-cで別に受け入れる。

## 保存と実行の契約

調整要求schema_version4を `planar_tuning_saved.py` の所有runnerへ接続した。物理判断は既存 `_assemble` と元参照比較を再利用し、探索の固有値・場・RFは全て実FEMと専用planar nativeで計算する。旧要求1〜3と旧checkpoint1の挙動を維持する。新版checkpointは同じformatのschema_version2とし、request4を必須にする。新版のこの受入はstandalone/API/CLIに限る。workerのqueued所有prefix・相対resultの読込・所有ファイル集合照合はP04-b-cで接続する。

各所有trialは元Project、job状態、完了manifest、worker.claim、solution内のcase/mesh/fields/results/manifestの合計9ファイルを保持する。許される下位ディレクトリはsolutionだけであり、追加ファイル、リンク、特殊entryを拒否する。完了metadataとclaimは元の実行来歴としてbyte単位で保存し、コピー先で再実行したとは主張しない。claimのPIDは生存証拠ではない。

所有先には必須 `request.json` と各 `checkpoint-NNN.json` を保存する。保存JSONは順序通りの相対名 `trial-NNN`、実行時の検証済み返却値は所有先の絶対pathを持つ。再生は宣言ownerの直下に限定し、余分なpath要素/順序違い/異なるowner/リンク成分を拒否する。ディスク上の絶対trial pathも拒否する。

再生は元要求から各trial Projectを再生成し、専用nativeのmesh、係数、FEM残差/正規化/最低正スペクトル、RF量、元場比較、個別ID回復、親関係、探索判断と最終gateを再検証する。hashの一致だけを物理的正しさの証拠にしない。保存要求のコピーとcheckpoint要求も照合する。

再開は新ディレクトリだけへ書き、全確認済みprefixを所有コピーして物理再生した後、新trialを実行する。コピー前後の元/先hashと全判断を照合し、元Project/native/checkpointを上書きしない。新trial失敗時も所有先の確認済みprefix checkpointを保持し、その地点から別所有先へ再開できる。初回空prefixにもcheckpoint-000を保存する。失敗は周波数評価にならない。

## 基準で失敗する不変量

出力ディレクトリの移動は、その内部に保存された完全な物理結果の再生可能性を変えない。基準版で実非アフィンrequest4の初回trialを保存し、出力を移動すると、絶対path参照のため `read_planar_tune` がnative不在として拒否された。`out/p04bb-planar-owned-20261002/baseline-rejection.json` に基準hash・要求のPAUSED状態・例外を保存した。

初回の再現スクリプトでは、テスト工場rectangleのimport先とNumPy scalarを修正してからこの不変量を再現した。これは製品ソルバーの数値不具合ではない。

## 条件別検証

| 条件 | 独立対照または操作 |
| --- | --- |
| 全域非アフィンTE | 右半分だけの伸長、同じ長方形境界のTE10解析cutoff、独立uniform mesh/異なる対角分割のFEM、粗細で解析差の減少、G比較 |
| 全域非アフィンTM | 同じ変位法則でDirichlet TM11解析cutoff、独立uniform mesh、粗細で解析差の減少、電気/磁気各0.5 J/m |
| 相似極限 | 2倍拡大の実検索/最終細分、fの1/2、G不変、Qの平方根2倍、J/m正規化保存 |
| 実個別回復 | 近接する矩形modeの主比較nullから固定先行anchorの元場比較で検索/最終個別IDを回復し、コピー後にも同じeventを保持 |
| 未確認停止 | 真の初回/現trial縮退、上側guardとの接続、利用不可anchorでUNVERIFIED、周波数/目標誤差null、再開不可 |
| gateの分離 | 同じ完全nativeに別宣言の厳しい粗細gateを適用し、refined_target_metのままmesh_difference_met=falseを確認。保存判断を改変しない |
| 所有再生/CLI | 初回出力移動、複数段階の新所有先への全prefixコピー、祖先移動後CLI最終細分、完成出力移動後CLI再生、全元係数配列/Project/hash/判断不変 |
| 失敗prefix | 新solveを例外で止め、別所有先のprefix再生と再開、元checkpoint byte不変、失敗に周波数なし |
| 改変拒否 | native係数、mesh、RFを各階層で再hashしても拒否。元lawの両要求コピーの改変、親index、保存周波数の改変も拒否 |
| 厳密path/旧版 | 相対名/単一owner/リンク/宣言ファイル集合/元要求の束縛、既存出力非上書き、終端再開拒否、旧調整/回復/workerの選択回帰 |

独立TM1件は、8/16分割で154.024秒にITERATION_LIMITを確認（session12993、終了1）した後、12/24分割と独立24分割へ改善し、192.929秒PASS（session11671、終了0）。元の目標/粗細gateと解析相対許容差3e-6は保持した。選択21件は846.030秒、20PASS/1ERROR（session99948、終了1）。ERRORは移動後CLI再開のテスト側60秒deadlineでsubprocessをkill/waitしたことによる。旧要求1〜3の14件は全PASS。数値許容差を保持し、CLI実行期限だけ300秒としてこの1件をsession65480で再確認し、256.734秒PASS（終了0）。合計は選択20件成功＋独立TM1件＋CLI再確認1件の分割22件成功（新8/旧14）であり、一度の22件成功や全suite成功とは扱わない。新版worker所有操作の受入はこの表へ混在させない。

## 実行と初回失敗

標準unittestを既存lock環境で実行する。`OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-ng-uv-cache uv run --no-sync python -m unittest -v ...` を使用した。

初回新7件は85.712秒、2PASS/3FAIL/2ERROR（終了1、session30100）。2ERRORは小数幅の6分割rectangle工場で角座標の計算順序が異なることによる。3FAILは4分割の粗格子で検索が期待通り細分へ進まない/iteration limitになる、および相似対照の相対解析誤差1.6071e-5が3e-6を超えたことによる。許容差/期待値を維持し、元gridを8分割、最終gridを16分割へ改善した。TE独立meshも16分割の異なる対角線を使う。TMは上記の12/24分割で別検証する。path・再hash改変の2件は初回からPASS。

修正後は新7件と旧 `test_planar_tuning test_planar_tuning_recovery test_planar_tuning_jobs test_planar_tuning_recovery_jobs` を選択し、session99948で検証した（21件）。このmodule読込後に追加した独立TM1件はsession12993/11671で別検証した。395製品hash不変を確認した。初回のnew7/修正後21/TM1/CLI1を一度の全件成功として扱わない。製品srcは全実行中に固定し、395製品ファイルの不変を照合した。全handleは終端、src固定解除。開始hashと終端auditを `out/p04bb-planar-owned-20261002/` に保持する。

canonical軸対称TM経路、FEM算術、既存追跡/回復の許容差を変更していない。seed/全validateは実行しない。全planar/GUI/曲線/材料の受入や連続pathのmode同定をこの選択検証から推論しない。

## 来歴と限界

既存Hphi所有checkpointの保存/コピー設計を参考に、専用planar job/nativeと元場判断へ適合させた。旧solverソース/実行物の読取・コピー・実行、新たな外部資料/依存はない。解析対照はテスト専用で、製品固有値は実FEMのまま。二格子周波数差と小さな代数残差を離散化誤差の上界とは扱わない。
