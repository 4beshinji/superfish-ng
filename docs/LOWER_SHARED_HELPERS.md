# 下位共通処理の受入（RF-03、2026-10-14）

値検査、JSON、来歴を別々の下位モジュールへ抽出した。旧入口signatureと転送関数を
保持し、各段階で一つの専用物理と直接消費者を接続した。下位三モジュールは標準
ライブラリだけに依存し、Case/Project/jobs/GUIや数値solverをimportしない。

| 処理 | 下位モジュール | 主な旧入口/直接消費者 | 検証 |
|---|---|---|---|
| keys/integer/positive | input_validation | config転送、同軸入力 | 10 unit、75旧新/転送probe |
| 重複キー拒否JSON/canonical | json_codec | Project、saved_mode_tracking転送、同軸native | 17 unit、143 probe、113例題hash |
| SHA/可変metadata JSON置換 | artifact_provenance | jobs/completion転送、Hφ所有hash | 25 unit、2 MiB超hash/例外/byte/失敗保存保持 |

三段階は52テスト実行、重複を除いて48個別ID。元bodyのAST一致と例外文言、bool/int、
NaN/Infinity、重複キー、-0.0、Unicode/encoding、canonical順序を確認した。
物理parserの受理方針とnative完了の排他公開は呼出側に残す。可変metadataの置換writerを
native完了公開へ流用しない。新しい依存、保存schema、数値式、物理許容差は導入していない。

初回fullは2689 test/528 module、2 FAIL/18 ERROR/3 SKIPで終了1。
`out/validation-rf03-integration-20261014/`に失敗と実UNCHANGED監査を保持した。
計測alias、反射の拒否順、独立比較Case、保存場fixtureの求解契約、失敗reportの旧期待値の
五点を修正し、隔離sourceで58個別unitを分割確認した。数値式/参照/許容差を維持し、
実P2の組立一回と行列/場/全RF一致、独立Bessel、3形状54 FEMの再開/完全再生も確認した。
検証済み五ファイルだけを主ツリーへbyte一致で反映したコミットは`6ac525a`。

固定sourceでの再検証は`out/validation-rf03-integration-fixed-20261014/`。
8 process、528 module、2689 testを3910.941秒で完了、終了0/full PASS。
失敗/エラー0、SKIP3は任意NGSolve環境の2件と専用circle/TE native証拠rootを要する1件。
これらの外部/専用受入が実行されたとは主張しない。CI設定はテンプレートで、hosted実行は未観測。
実validatorの前後1492 source/file一覧は完全一致、変更/追加/削除はゼロ。

同じfull内のseed計算でpillbox6modeとshaped3modeの全RF fieldをbenchmarkへ照合した。
周波数差はゼロ、物理量の相対差最大8.882e-16。残差/エネルギーbalanceは絶対診断として
別に確認し、離散化誤差の保証には使わない。保存解から追加求解なしで全量を再構築し、
両R/Qの比2、U=Ue+Uh、元Case hashと全既存規約も確認した。
現行の追加domain説明を別記し、古いbenchmarkの規約を改変しない。

最終証拠は`out/rf03-lower-helpers-20261013/full-fixed-terminal.json`。
各段階のreceipt、初回失敗full、修正の分割検証とbyte反映、固定fullの命令/元source一覧、
全RF差分とraw SHAを結合する。監査scriptの旧規約全体一致という初稿失敗も保全し、
既存domain説明の追加を明示して再監査した。新FEMを同じ証拠更新のために繰り返していない。

RF-03をDONEとする。後続の所有worker、調整判断、CLI/HTTP/画面、fixture、再生費用の
カードと、計画全体の最終統合受入は別に残る。既存V02/V03/V05の必須依存は維持する。
