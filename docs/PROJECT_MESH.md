# Projectに明示元メッシュを保持する

2026-09-14追補：[曲線の初期メッシュ置換API/CLI](CURVED_PROJECT_REMESH.md)で、新しいメッシュと全細分履歴を同時に宣言できる。
旧番号を自動継承せず、二次領域全体の一致を要求する。従来の単純なメッシュ置換でmarked履歴を拒否する契約は保持する。

後続実装: [外部メッシュ単体のGUI読込/解除と直線固定Study](EXTERNAL_MESH_WORKFLOW.md)を追加。以下はProject保存契約を受け入れた時点の記録。

後続実装: [曲線Project一括変形](CURVED_PROJECT_TRANSFORM.md)を追加。曲線tune接続は残る。以下はこの基盤を受け入れた時点の記録。

2026-09-09、O02/D02の実行・保存基盤。
Project第2版は既存Projectの項目に必須 `mesh_data` を追加する。
値は既存のSI/rz・0始まり・境界タグ付き三角形JSONであり、パス参照ではない。
`mesh_from_dict` でCase輪郭・接続・向き・境界タグを検証し、正規化したコピーを保持する。
第2版のnull/欠落、第1版へのmesh_data混入、未知項目は拒否する。
メッシュなしの従来Projectは第1版のままで、Caseの版・物理モデル・数値式は変えない。
例題は `examples/projects/explicit_mesh.json`。

```python
project = Project(case, mesh_data=tagged_mesh)
project.save(path)  # 新規ファイルだけに保存
execute_project(Project.load(path), new_output_directory)
```

`run-project` CLI・JobManagerの通常ジョブは同じ入力を検証し、
`solve(case, mesh_data=project.mesh_data)` へ渡す。
直線P1/P2および曲線P2の元の弦メッシュに対応する。
曲線の二次写像/細分履歴は既存Caseから構築するので、mesh_dataを高次節点の入力や
任意CADの代替と解釈しない。通常生成用nr/nz等は明示メッシュを置き換えない。
保存されたproject.jsonとsolution/mesh.jsonは既存完了manifestのhash検査対象になる。
実行開始前のproject.jsonのhashを保持し、保存後に変わっていた場合は失敗として
完了manifestを公開しない。manifestにも開始時のhashを使う。
実行中の入力変更を故障注入した検査は変更前FAIL、補強後PASSとなった。
鏡映では既存の鏡映処理を使い、直線メッシュの全領域化または曲線の元半領域再構築を保つ。

GUIで第2版Projectを開くと、明示元メッシュの頂点・三角形数を表示する。
フォームからの保存・実行・結果の再読込でmesh_dataを保持する。
新規Projectを作ると以前の明示メッシュを外す。
曲線の図上細分選択には明示元メッシュを使い、適応入力生成にもinitial_meshとして渡す。
メッシュだけの専用インポート画面はまだなく、完全なProject文書を開く方式である。

固定二次幾何の細分Studyは元メッシュを維持して実行する。
幾何/メッシュ掃引とtuneは、まだ試行ごとのメッシュ変形を宣言できないため明示拒否する。
この拒否を後続D02の曲線調整接続で置き換える。黙って生成メッシュへ切り替えない。
通常ジョブに新しい部分checkpoint再開を追加したわけではなく、既存の中止・別ジョブ再実行を使う。

受入条件は旧Project往復、入力/番号/接続の保持、改変拒否、直線P1/P2・曲線P2の
実計算/保存、CLI・管理器再起動・鏡映、GUIでの保持、相似則と標準回帰である。
追加3+既存Project5検査は0.694秒で合格。番号を反転したメッシュで生成呼出しを禁止し、
実際の指定接続使用を確認した。直後に番号置換前との周波数一致も検査へ加えた。
初回は検査側が非対応のJobManager context managerを使って1件ERRORとなった。
既存のclose契約へ直し再実行し、製品の数値条件は変更していない。

`out/project-mesh-similarity-20260909/validation.json` は寸法1/2、P2円筒で
解析周波数とf/両R/Q/G相似則、保存メッシュとProjectの一致がPASS。
相似差最大1.510e-14。`out/project-mesh-study-20260909` は明示元メッシュからの
曲線固定幾何2水準Studyを実行した出力。16→64要素、周波数は
1615401540.158→1615236801.169 HzでRitz単調性、全元メッシュ保持を確認した。
`out/project-mesh-curved-reflection-20260909` は左右×両対称の4曲線鏡映がPASS。
元半領域メッシュを保持し、生成メッシュ経路との周波数差最大6.662e-16。

実Chrome初回は適応入力の非同期生成を待たず空欄をJSONとして読んだ検証器の不備でFAIL。
製品コードを固定して、検証器の待機条件だけを修正し再実行した。
`out/browser-project-mesh-accepted-20260909/report.json` の21項目がPASS、外部要求0。
既存調整操作、明示メッシュ読込/実行/保存/再読込、適応入力への引継ぎ、新規時解除を確認。
初回out/browser-project-mesh-20260909は保持。GUI・ブラウザーは終了0。
初回標準終了後、検証済みの待機修正をリポジトリの検証スクリプトへ反映した。

初回標準 `out/validation-project-mesh-20260909` は701件、697合格・2 ERROR・2 skip、
478.010秒。Case専用のexamples直下にProject例題を置いたため、既存Case往復検査が
拒否した。Project例題をexamples/projectsへ移し、Caseパーサーや検査の厳密性を維持した。
待機修正と入力hash補強を含めて最終検証を再実行した。
`out/project-mesh-final-20260909/validation.json` は相似則・鏡映4条件・固定曲線StudyがPASS。
`out/browser-project-mesh-final-20260909/report.json` は21項目PASS、外部要求0、終了0。
最終GUIも正常停止・終了0。新規スクリーンショットの目視検査は行っていない。
`out/validation-project-mesh-final-20260909` は702件中700合格・2 skip、
unittest476.257秒、全体終了0。seed9モード19量の周波数差0、RF最大相対差8.882e-16。
最終独立/標準/終了後の399対象ファイルhashとChrome対象hashが一致した。
追加の入力変更検査を含むProject9検査は0.761秒で合格し、最終標準にも含まれる。
上記範囲のProject/実行/GUI接続を限定受入とする。

Projectは入力時と出力時にコピーを作るが、Pythonオブジェクトの内部dict自体を
読み取り専用コンテナにしたわけではない。実行準備時に再検証・保存して入力を固定する。
一般曲線tune、O02/D02全体の受入は継続する。新規依存・外部資料・legacy参照はない。
