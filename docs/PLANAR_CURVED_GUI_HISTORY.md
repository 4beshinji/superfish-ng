# 曲線GUIの実比較・履歴回復・延長

2026-10-07、P09の[専用GUI](PLANAR_CURVED_GUI.md)の実ブラウザー受入。
有界条件は、strict要求/結果の実保存とファイル読込、実running worker取消しと新比較、
TEの反射parity付き順位交換、真縮退のID集合継続、元nativeが連続する独立履歴、
実過去anchorによる個別ID回復/後続延長、元五byteの取り込み/表示と親不変である。
P09はIN_PROGRESS。円/非円形の大容量調整checkpointとP09全条件監査は継続する。

## 実操作と独立対照

新 `scripts/verify_gui_planar_curved_history.mjs` は共通browser-sessionの資源管理を使う。
Chromeで実JSON入力・button・file input・download・画像表示を操作する。
比較/履歴/回復は専用typed APIから実子プロセスへ投入する。
先行API受入の実TE楕円→円→楕円→後続の元四nativeを新workspaceへ取り込む。
元E/H/反射parity/rankの対照は先行受入から保全し、新しいnative固有解は生成しない。
比較と有限guard、元nativeの全FEM帯/RF検証は実行する。

曲線比較要求の全二次chart・E/H controls・元IDを保存/再読込する。
実running比較をGUIで取消し、別jobで同じ比較を完了する。
楕円間の個別対応は `[even-x, odd-x]` の実順位交換を保持し、E/H/位相/guardの
完全結果をダウンロードする。前後の元五nativeは全byteで取り込み、親jobも不変。

楕円→真円doublet→楕円を比較し、集合継続PASSと個別ID `[null,null]` を区別する。
2段/max_steps=3の独立履歴要求と、anchor=0の回復要求も保存/実ファイル読込する。
元未解決履歴を保持した別jobで個別IDを回復し、実後続比較を追加する。
3段で `can_extend=False` /GUI延長button disabledとなることを確認する。
全継承比較/回復/IDを結果保存し、最後の元nativeを取り込んで既存RFページへ開く。
SI単位長U′と二つの名前付きR/Q N/A、実元場画像を確認する。

## 表示修正

回復後の完全履歴診断を展開すると、全参照chartが無制限の縦長preとなり、
Chromeの全ページ撮影が `Page is too large` で失敗した。
`#planar-curved-workspace pre` だけに24remのmax-height/overflow autoを追加した。
全JSONを保持しながらパネル内でスクロールする。科学結果/輸送/許容値は変えない。
全数値/browser/server handle終端後にだけCSSを編集し、元版をarchiveに保持した。
修正後は完成済み履歴から不足する元場/診断/画像表示だけを補完する。
診断欄は高さ360px、全文のscrollHeightは947,280pxで、内容を削除せず表示を制限した。
画像で過去段階のnull IDが空欄に見える問題も確認し、表だけ「未確定」と表示する。
元データのnullは維持し、追加のrender-only 1項目で元null/可視表/scrollを確認する。

## 記録と範囲

rawは `out/p09-planar-curved-history-gui-20261007/`、基準 `1f9dce2`。
前準備で元四nativeを完全再生して取り込み、元sourceの全hashとtyped要求をfixtureに保持する。

| report/log | 受入範囲と終了 |
|---|---|
| browser-acceptance / browser-test.log | 要求往復・実取消しの2項目成功、その後検証器のID期待式誤りで終了1 |
| browser-continuation / browser-continuation-test.log | 同じ実完了比較を再利用し、順位交換・全結果downloadの2項目成功、その後取り込み完了待ち不足で終了1 |
| browser-history-acceptance / browser-history-test.log | 元五byte/親不変、真doublet、履歴、回復、延長、全結果保存の6項目成功、最後の元場リンク更新待ち不足で終了1 |
| browser-final-acceptance / browser-final-test.log | 実完了延長履歴を再利用し、元場のbyte照合後に展開診断のPage is too largeで終了1、check記録0 |
| browser-render-acceptance / browser-render-test.log | CSS修正後の元場/親byte・SI/RF・実画像の不足3項目PASS/終了0、診断欄の高さ/scrollを実測 |
| browser-null-render-acceptance / browser-null-render-test.log | 元null維持/「未確定」表示/全文scrollの1項目PASS/終了0、新native求解/worker/import0 |

元13項目＋最終null表示1項目、計14項目の分割受入であり、一括検証器PASSとは数えない。
初回期待式と二つの非同期リンク待ちの誤りは検証器だけを修正した。
5版の元検証器と全FAIL/ERROR report/logを保持する。
既存実作成pair/extended-historyを再利用する引数を設け、新比較/履歴を重複生成しない。
元場の取り込みはbyteコピーであり、新固有解へ帰属させない。
製品の実表示問題と検証器の期待/待ち誤りを区別する。

入口（未使用out、準備済みfixture/workspace、localhost起動logを指定）：

```sh
node scripts/verify_gui_planar_curved_history.mjs --server-log LOG --out NEW_OUT --request FIXTURE_JSON --workspace GUI_WORKSPACE
```

今回のコマンド/準備/サーバー/最終監査器はraw内へ保全する。
製品源はCSS/JSの表示2件だけの変更、元420源中418と全科学kernel/全123 TSVは不変。
保存manifestの420 creator源は元CSS/JS archiveで照合し、現在のreader sourceへ書き換えない。
実取消しworker −15、比較4/履歴3のworker全0を元サーバーの実process handleで観測する。
後続2サーバーの再表示は新worker0。全3server/Chrome終端、外部要求0/slot 0。
最終byte監査は新FEM/物理再構築0、全7完了job/510外側manifest entryと元native/履歴prefixを照合する。

表示修正に必要な実GUI検証だけを行い、数値unit/full/seedは再実行しない。
Hosted CI、Wine/GPU、新外部資料/依存/legacy参照は今回未実施。
大容量円/非円形TE調整checkpointの実GUIとP09全条件、原互換条件/全goalは継続する。
