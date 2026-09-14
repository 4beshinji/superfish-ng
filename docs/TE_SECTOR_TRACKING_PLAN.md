# 対称面付きTE円筒の追跡：後続契約

2026-09-15 JST：[TE円筒チューニング](TE_TUNING.md)を同端条件の直線円筒へ接続し、限定受入。
EφによるID、半領域・鏡映の元セクター順位、加速量N/A、保存再開・回復・最終粗細ゲートを保持。
関連53unit（52＋1の分割実行）、専用44実FEM、Chrome閉PEC9/鏡映11/旧TM9項目がPASS。
8組native全配列/RF一致、元114ファイル保持。一般TE形状・他物理調整とD03は残る。
親33=10受入/16進行/6他未受入/1範囲外、D02と全計画goalは継続中。


## 主ツリーの限定受入完了（2026-09-09）

基準959d127からの変更。通常閉PECの追跡文書形式を保ち、対称面付きの場合だけ端条件・部分スペクトル情報を加える。固有値・場・RFの組立と精度許容差は変更していない。一般形状/曲線写像、TEの逐次追跡Study・調整・最適化、親P01/D01/O02全体の受入は含まない。

- 追加6unit、TE全58件がPASS。標準 `out/validation-te-sector-tracking-20260909` は801件中799合格/2skip（unittest1229.471秒、command1229.859秒）、convergenceも終了0。
- `out/te-sector-tracking-final-independent-20260909`：両次数・両尺度・左右・両対称条件32実FEM。3積分次数×半領域/鏡映の96比較、符号/振幅不変、8CLI保存/再生がPASS。解析周波数最大相対誤差P1 4.07820011e-4、P2 1.007970034e-5。
- `out/te-sector-tracking-study-20260909`：8Study/16実FEMと8CLI再生。独立Studyの数値状態UNVERIFIEDと、別操作の追跡PASSを区別した。
- `out/browser-te-sector-tracking-fixed-20260909`：Chrome9操作、合流/分裂の集合ID、部分スペクトル表示、保存/再読込、改変拒否、UNVERIFIEDの継続拒否。外部通信0、画面も目視確認。管理器停止後の6取込・Project/source・全係数/RF・公開履歴再生は `out/te-sector-tracking-gui-independent-20260909` で一致。専用GUIサーバーは終了0。
- 旧閉PEC TE/TM追跡8文書の公開replayが完全一致。最終 `seed_regression.json` はTM seed9モード19量の周波数差0/RF最大8.882e-16、旧TE通常7件・鏡映3件のRF差0。標準・最終独立・Study・GUI再検証・旧追跡と現在470sourceが一致。開始前snapshotを作ったとは主張しない。

失敗履歴を保持：旧鏡映unitの変換時に必須controlsを省略して失敗し、指定を補って58件を再実行した。最初のChrome検証器は旧6モード用の行数5を残し、今回4モードの合流3行と不一致。検証器の期待値を直し、既存取込を残して再検証した。製品側の数値条件は変更していない。以下の「実行中」「候補」は当時の記録であり、現在状態は本節を優先する。

## 受入条件

直線P1/P2・一定半径profileのTE円筒に限定する。通常閉PECに加え、一つだけ電気/磁気対称面を持つ元半領域と、その正規な鏡映結果を対象にする。比較する二つの元端条件・対称面の側を一致させ、通常/鏡映の混在と二つの対称面は受け入れない。異なる物理の境界を、同じ円筒の外形だけで対応付けない。

追跡する場は既存と同じ実ピークEφ。normalized_cylinderの点写像とrhoの体積重みを使い、磁場の要素境界における片側値を使わない。鏡映APIの元係数だけを参照して実際の入力場の変更を無視する実装にしない。符号/列ごとの振幅に対する正規化内積の不変性を維持する。鏡映結果の番号は部分スペクトル内の順序として記録する。

解析的な順位交差、近接/縮退、帯域退出、尺度/標本次数、符号/振幅を独立検証する。個別ID未確認や異なる対称条件で、調整へ周波数を渡さない。保存比較/公開replay・元native全snapshot・改変拒否、CLI/Study/GUI、旧閉PEC TE/TM追跡と標準回帰を維持してから限定受入する。一般形状/曲線追跡は別工程。

## 予備候補

一時パッケージ `/tmp/superfish-te-sector-tracking-candidate-20260909` のte_mode_tracking.pyだけへ端条件検査を試作した。主ツリーの閉PEC条件は変更していない。候補patch/driver/reportは `out/te-sector-tracking-candidate-20260909`。

既存TEのBessel基底で、磁気対称の全領域軸方向番号1/3と、電気対称の2/4に属する半径方向系列の交差を選んだ。左右×磁気/電気×交差前後のP2実FEMは8件、4モードの周波数は解析順位に対して1e-4以内。標本次数12/24/48、半領域と鏡映結果の全24比較で同じ解析ID対応がPASS。列ごとの符号と振幅を変えても対応を保持した。鏡映は元FEMから係数移送し、追加の固有値計算を数えていない。

初回driverは共有検証helperのimportが主ツリーを先頭に挿入し、候補パッケージを使っているというassertでFEM前に停止した。initial-driver.pyと `/tmp/te-sector-tracking-candidate-20260909.log` を保持。候補の場所を明示し、fingerprintを独立に定義した修正版70770は終了0（ログ `/tmp/te-sector-tracking-candidate-fixed-20260909.log`）。主ツリー467sourceは前後不変。

これはP2/1尺度の交差試作である。P1・相似則・混在/二対称拒否・近接縮退・帯域退出・保存replay/改変・CLI/GUIは未受入。候補の閉PEC出力にもmetadata変更が入るため、製品では従来閉PECの文書を保持する分岐が必要。新規外部資料・依存・legacy参照なし。

## 両次数・相似則と保存の候補検証

`out/te-sector-tracking-scales-candidate-20260909` の71233は終了0。P1/P2×尺度1/2×左右×両対称×交差前後の32実FEMを実行した。半領域/鏡映、標本次数12/24/48の全96比較で解析IDと一致し、列ごとの符号/振幅不変、尺度2で周波数1/2を1e-10で確認。P1はnr96/nz144、P2はnr24/nz36。解析周波数の相対誤差最大はP1 0.000407821、P2 1.007971e-5。候補での周波数ゲートはP1 1e-3、P2 1e-4を別に定義し、追跡一致を離散化誤差の保証とはしていない。主重なり最小はP1 0.999985213、P2 0.999999993。

`out/te-sector-tracking-integrity-candidate-20260909` の58725は終了0。両対称の解析縮退点・短い帯域を4実FEMで計算し、半領域/鏡映の4保存API比較で再生文書が一致。縮退では部分空間のID集合だけを保持し個別周波数取得を拒否、帯域退出はUNVERIFIEDを保持する。通常/鏡映混在と異なる対称条件、保存追跡文書の場名改変も拒否。鏡映の保存snapshotにsource_fields.npzが含まれることを確認。実ファイル変更中の追跡・CLI・GUIはこの候補では未検証。

主ツリー467sourceは引き続き不変。候補は製品へ未適用であり、旧閉PEC文書の保持、厳密な拒否検査、保存中変更・CLI/Study/GUI、標準回帰を受入条件として残す。

## 主ツリーへ接続中（基準959d127）

te_mode_tracking.pyで元端条件の一致・一対称面・TE source physicsを検査し、通常/鏡映混在や二対称を拒否する。実際に渡されたEφ場を比較し、reflection_source_coefficientsで入力場の変更を無視しない。閉PECの通常TEでは従来のphysical_mapping文書をそのまま維持する。一対称面の場合だけboundary_conditions/reflected_partial_spectrum/mode_index_scopeと限定scopeを追加する。曲面/一般形状は受け入れない。GUIの追跡説明・番号順入力と結果状態に半領域/鏡映部分スペクトルを明記した。

新6unit66992は終了0（5.151秒）。解析交差のIDと実入力場の列ごとの符号/振幅、縮退個別周波数拒否/帯域退出UNVERIFIED、保存replay/元source_fields snapshot、比較中元ファイル変更拒否、混在/異種端/二対称/偽のsource、閉PEC文書保持/曲面拒否を確認。既存鏡映5unitの初回45264は、拒否から成功へ変更した呼出しに必須の比較閾値を渡していなかったため1error。許容差を新設/緩和せず、必要な比較条件を呼出しへ明示した。初回log保持。TE全体87127は58件58.845秒、終了0。out/te-sector-tracking-development-20260909。

独立12324をscripts/validate_te_sector_tracking.pyで実行中（out/te-sector-tracking-independent-20260909、/tmp/te-sector-tracking-independent-20260909.log）。P1/P2・両尺度・左右/両対称の32実FEM/8組CLI+replayを予定する。GUI用の3実FEMはout/te-sector-tracking-gui-sources-20260909に作成済み。GUI24687 localhost42049、workspace out/te-sector-tracking-gui-workspace-20260909。Chromeはout/browser-te-sector-tracking-20260909へ実行中。標準は未開始、主ツリーsrc/tests/scripts/examplesは固定。
