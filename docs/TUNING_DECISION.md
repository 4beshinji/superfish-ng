# 調整判断と物理入口の境界（RF-05）

2026-10-14 **RF-05 DONE**。直接55個別unitと元六成果物の再生がPASSし、検証済み七ファイルを主ツリーへ反映した。

`tuning_decision.decide_next_trial(request, trials)`は確認済み試行と入口で正規化した
bracket制御値から、元の停止/次試行dictを返す。依存は標準`math`のみで、要求parser、
file I/O、Case/Project、solver、場/IDの検証を持たない。未確認報告を確認済み試行へ
変換する機能はない。物理入口が実native/場/追跡を確認してから判断へ渡す。

旧`tuning._decision`はsignatureと`base_request`正規化を保った転送関数として残す。
planar tuning/その所有prefix、直線・曲線・材料Hφは正規化を呼出側へ置いて下位判断を
直接利用する。三系HφのMESH_LIMITは共通bracket判断へ入る前に停止し、uniform scaleの
search比較親を0とする元処理も物理adapterに残した。

INITIALは試行なしで下限を次試行とするPAUSEDの元辞書に対応し、新しいstatus名を
作っていない。UNVERIFIEDは周波数欠落のまま停止する。上端の親0、bracketの符号/更新順、
反復/parameter限界、表現可能な中点、最良試行のrefinement親と停止理由を維持する。
最終refinementは目標誤差と二mesh周波数差の両方を検査し、後者を離散化誤差上界と
呼ばない。モード番号をIDへ置き換えず、追跡と回復は各物理の元実装に残す。

rawは`out/rf05-tuning-decision-20261014/`。自作sourceの隔離コピー
`/tmp/superfish-rf05-tuning-decision-20261014`で検証した。

- 元decisionから正規化だけを除いたbodyはAST完全一致。他のtuning関数も不変。
  五消費moduleは判断呼出と入口正規化以外の全関数bodyが一致。
- 114組の旧/純粋/旧API判断と174組の専用adapter比較で、初期/未確認/未bracket/両限界、
  四通りの最終二ゲート、親index、回復wrapper、MESH_LIMIT、符号付きゼロ/隣接float、
  入力不変を確認。純粋関数の機械比較は物理場の受入とは区別する。
- 直接tuningと各専用回復の10moduleを選択し、矩形解析cutoff/順位交換、同軸TEMと元場尺度、
  材料独立二層参照、曲線の元明示幾何/相似則、両周波数ゲートと未確認停止を保持する。
  55個別unit/1655.399秒、終了0/PASS、SKIP0。
- RF-04で得た元/抽出六worker成果物を、元native/Project byteのまま完全再生した。
  全RF/ID/試行/判断値の一致、source/artifactの前後不変を確認、新しいFEM求解はゼロ。

FEM/RF核、解析参照、物理許容差、native/要求/判断のschema、旧公開APIは変更しない。
変更は判断の責務移動と直接消費者に限定され、seed solver/RF経路には及ばないため、
RF-05単独の追加seed/fullは行わない。最終11カードの節目では全体fullを実施する。
新しい依存・外部数値参照・速度/一般精度保証も追加していない。

主ツリー反映時に候補の全byteと他1487 sourceの不変を確認した。受入の束縛は
`acceptance.json`、元数学body/直接unit/元成果物再生のsourceとraw SHAを保存する。
