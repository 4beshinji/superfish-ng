# 標準検証のプロセス並列化

2026-09-14 JST。主915sourceへ統合・限定受入。全299ファイル・1456テストを16プロセスで実行し、718.595秒で1453合格/3skip、失敗0。主統合後と配布物の展開先でも専用41テストが合格した。既存9モード19量の周波数差は0、最大相対差は8.882e-16。数値ソース・許容差・ベンチマークは変更していない。

```bash
python scripts/validate.py --test-workers 16 --out out/validation-new
```

既定は最大8プロセス。`--test-workers 1`は従来の1プロセスunittest discoverを使う。出力先は新しいディレクトリを指定する。通常のインストール済み環境で実行する。

scripts/run_tests.pyはunittest discoverと同じ一覧を収集し、ファイル単位の別Pythonプロセスへ割り当てる。同じモジュール/クラスのfixtureは一緒に実行する。親の一覧と各ワーカーの一覧を照合し、実行数、skip理由、失敗/エラー、期待された失敗/予期しない成功、終了コードと所要時間をJSONへ残す。出力欠落や異常終了を合格にしない。現在のflatなtests構成を対象とし、入れ子のパッケージ等で一覧が一致しない場合は拒否する。

各ワーカーのOPENBLAS_NUM_THREADS/OMP_NUM_THREADS/MKL_NUM_THREADSは1。同時プロセス数とBLAS内部の並列化を掛け合わせない。POSIXでは各ワーカーを別のプロセスグループにし、中断/異常終了で子孫も停止する。Windowsの子孫終了は実測していない。

各ファイルの完了を即時表示し、指定出力先のtest-run/にファイル別ログ/結果と全一覧を保存する。集計はtest-run/report.jsonが正本。統合tests.logはファイル順にまとめるため、最初の「Ran … tests」は全体件数ではない。周波数/RF検証はテスト合格後に従来の手順で実行する。

同じ非線形B-H保存/再読込18テストを、元unittest逐次123.557秒、3プロセス83.882秒で確認した。全ID/件数/結果が一致し、観測した高速化は1.473倍。両測定時に旧逐次標準が別途動作していた。全suiteへ同じ倍率を一般化せず、中断した旧全件検証の時間から倍率を算出しない。ファイル単位の分配なので、最後の長い1ファイルの実行時間は残る。

ランナーの6テストで成功/skip/期待された失敗、通常の失敗/エラー、import失敗、異常終了、プロセスの実重なり、fixture、中断時の子孫終了、空一覧/不正worker数/既存出力の拒否を確認した。初回の実FEM比較では、script起動でcwdがsys.pathから外れてscripts.*の参照importが失敗した。失敗記録を保持し、元python -m unittestと同じcwd検索を追加。cwdの補助moduleを読む回帰を含めて再確認した。

最終固定ソースは909ファイル。G03の907ファイルからの差はscripts/run_tests.py、scripts/validate.py、tests/test_parallel_test_runner.pyの3ファイルのみ。実行記録はout/parallel-validation-development-20260914、全標準はout/validation-parallel-checkpoint-20260914。[今回の受入範囲](G03_FINITE_OFFSETS_CHECKPOINT.md)を参照。Python標準ライブラリだけを使い、新規依存・外部サービスは追加していない。
