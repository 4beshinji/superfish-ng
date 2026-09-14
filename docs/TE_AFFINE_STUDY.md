# TEアフィンStudyの限定受入

2026-09-15 JST。D02のTE形状経路に関連する限定課題。
受入条件は、直接閉PEC/axisの二次曲線Projectを固定RFメタデータで掃引し、
実TE FEM・native保存・完了StudyのEφ追跡・GUI/CLIへ接続すること。
加速区間を補わず、両R/QはN/A。独立スペクトルの計算完了を収束確認としない。

`validate_affine_study` のTE一律拒否を、既存のTE case検査、固定RF、直接閉形状の
明示条件へ変更した。TMの固定/軸方向RF規約は維持する。
GUI検証器はTEのnull/nullがNaNとなってR/Q検査をすり抜ける経路を修正し、
TEでは両R/QのnullとG尺度を検査、TMでは有限のR/Q比を要求する。
完了Study追跡では相対アフィン写像とEφを確認する。画面の旧TM専用説明も修正した。

## 検証

生記録は `out/te-affine-study-20260915/`。旧TE拒否をbaseline.logで再現した。

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=tests:src .venv/bin/python -m unittest \
 test_te_affine_study test_curved_affine_study test_curved_project_transform test_te_jobs
```

新2件を含む23件、214.275秒PASS。実掃引、定義往復、未対応RF/鏡映/加速指定の拒否、
保存ファイル改変拒否、Maxwell尺度を確認した。共通FEMの変更はなく全suite/seedは再実行していない。

専用計算はGUI2点＋CLI2点の4実FEM。Chrome実経路12項目PASS、外部要求0。
完了Study追跡のダウンロードと保存再生もPASS。元の独立スペクトルはUNVERIFIEDを維持する。
2組のnative保存について12配列と全モードRF値が完全一致し、読取前後の57ファイルhashを保持した。
倍寸でfは1/2、固定エネルギーでE/Hは2^(-3/2)、GとUは不変、Q0は√2、壁損失は2^(-3/2)。
保存解の全要素重心のEφ/Hr/HzとRFを別々に検査し、最大相対差8.990e-15だった。
係数の2^(-5/2)則はunitでも検査した。離散化誤差や表面ピーク精度の保証ではない。

実計算中の製品hashは一致。終了後に説明文のみ修正し、追加FEMなしのChrome定義往復・
レイアウト3項目がPASS、最終ソースhash一致とスクリーンショット目視を確認した。
説明文修正前後の画面・報告を別保存し、先の12項目を最終文字列での再実行とは扱わない。
追加GUIサーバーはPID 2382719へSIGINT、終了0を回収した。

## 残件と出典

逐次/適応Studyは要求準備だけをGUIで検査し、実計算は未検証・未接続である。
`tracked_study._point_sources` のTM専用readerが残るため、完了Study追跡との混同を避ける。
次は厳密なTE native読取と保存再開をこの経路へ接続し、独立物理則と停止再開で検証する。
TE版8、曲線対称/鏡映、実ID回復例、その他の物理とD03も残る。
親33=10受入/16進行/6他未受入/1範囲外、D02と全計画goalは継続中。

既存のTEアフィン変形・保存追跡実装とMaxwell尺度則を再利用した。
新規外部資料・依存追加・旧ソルバー参照はない。
