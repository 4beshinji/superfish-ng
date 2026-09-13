# 法線オフセットの弧端・退化診断

2026-09-14 JST：[直線と非円楕円・双曲線オフセットの接触](LINE_NONCIRCULAR_OFFSET_CONTACTS.md)を追加。
新規診断は版7、旧保存構築診断版1〜6は元規則で再検証する。全域射影から有限0/1点を証明し、
非正則時は確認済み接触中心数だけを保存する。カスプ接触と同一中心の重複も明示する。

2026-09-14 JST：[一般二進回転/直線長の円オフセット](ALGEBRAIC_CIRCULAR_OFFSETS.md)を追加。
新規診断は版6、旧保存構築診断版1〜5は元規則で再検証する。支持半径や直線長の平方根を
丸めず、円・直線の接触/横断/離隔と有限所属を判定する。予算不足の未確認は維持する。

2026-09-14 JST：[異なる円・直線の有限交点](FINITE_CIRCULAR_CROSSINGS.md)を追加。
新規診断は版5、保存構築診断版1〜4は各当時の規則で再検証する。
有理支持の二円/直線円の全二交点・非平行線の一交点を元有限区間へ照合する。

2026-09-13 UTC：[有限オフセット診断の受入更新](G03_FINITE_OFFSETS_CHECKPOINT.md)。新規normal_offset_diagnosis/construction_offset_diagnosisは版4、要求は版1。保存構築診断版1/2/3は各当時の規則で再検証し、自動更新しない。同一支持円の真の周期と任意回転、同じ非円楕円/同枝双曲線の等距離自己接点を追加した。証拠のみの認証と全有限領域の完全性を区別する。

2026-09-08。`offset_degeneracies.classify_offset_degeneracies` は中心軌跡の特殊ケースを
厳密な有理数演算と有限弧の区間所属検査で分類する。単位はSI、座標順は(z,r)。
診断は構築候補の自動選択や完成Caseではなく、G03の退化分類の部分実装である。
一般の交点探索は従来の `intersect_normal_offsets` を使う。

## 結果の読み方

`status=CERTIFIED` は記録した事実の証明を表す。全有限領域の分類まで完了したかは
別の `finite_domain_complete` で読む。共有パラメータの証拠だけでは、別パラメータ同士の
交差や有限弧全体の解数を決められない。`UNVERIFIED` は無交点を意味しない。

| classification | 確認した事実 | 全有限領域 |
|---|---|---|
| DISJOINT | 対象領域で共有する中心点なし | true、finite_center_count=0 |
| SINGLE_TANGENCY | 円同士、直線円、または全域射影が証明された直線と非円楕円/双曲線の唯一の支持接点が、両有限範囲に所属 | true、finite_center_count=1 |
| TANGENCY_WITNESSES | 非円楕円/双曲線と直線の有限接触中心を確認。通常/カスプ接触と同一中心の統合を証拠へ記録 | false、finite_center_count=null。確認数はevidence.tangency_witness_center_count |
| INFINITE_PARAMETER_PAIRS | 同じ中心を与えるパラメータ対が無限個ある | 証拠のみならfalse。同一支持円・対象の同一円錐曲線・潰れた円・平行直線の全分類はtrue |
| SHARED_PARAMETER_ENDPOINT | 同じ元パラメータの端点、または一直線上の有限範囲の共有端点 | 証拠のみならfalse。同一支持円・対象の同一円錐曲線・平行直線の全分類はtrue |
| FINITE_CENTERS | 対象の同一円錐曲線の反射接点/共有端点、または異なる円・直線の全交点から重複なく数えた有限中心 | true、finite_center_countは全数 |
| COINCIDENT_SUPPORTING_CIRCLES | 支持円の中心と半径が同じ | false。元の有限弧同士が重なるとは限らない |
| UNVERIFIED | この診断で証明できない、または有限弧所属の精度予算不足 | false。無交点・解数・接続可否を確定しない |

`finite_center_count` は全有限領域の中心点数が確定した場合だけ整数で返す。
未確定または無限個の場合はnull。`infinite_parameter_pairs` は無限個のパラメータ対を
証明した場合true、有限性を証明した場合false、決めていない場合null。
円のオフセットが中心へ潰れると、中心点が1個でもパラメータ対は無限個になり得る。
この場合を「唯一のフィレット候補」と扱ってはならない。

## 証明に使う関係

元の円/楕円/双曲線の中心・軸・二進回転係数（双曲線は枝も）が一致し、
向きを補正した距離 sign(span)*d が一致すると、同じ元パラメータの中心軌跡も一致する。
両有限範囲を元パラメータへアフィン変換し、正の長さの共通区間があれば無限対、
共通区間が一点なら共有端点の証拠を返す。別パラメータでの自己交差を除外する証明ではない。
向きを反転した元弧にはdの符号反転が必要で、同じdのまま同一軌跡とは扱わない。

円は半軸aと二進回転係数c,sから、符号付きオフセット半径
`rho = a*sqrt(c*c+s*s) - sign(span)*d` を持つ。平方根が厳密な有理数となる場合を扱い、
一般の二進回転をc²+s²=1へ丸めない。支持半径は|rho|で、rho<0でも接点を元弧へ戻す際は
符号を維持する。rho=0は潰れとして別に扱う。

2円の中心差の二乗D²を、半径和/差の二乗と有理数で比較する。
外接/内接の等号、外側/内側の離隔を判定し、接点は
`C1 + (R1²-R2²+D²)/(2D²) * (C2-C1)` で得る。
直線と円は中心の支持直線への直交射影を使い、距離二乗とR²を比較する。
線分の非零オフセットは|Q−P|が有理数のときに扱う。距離0なら任意の二進端点を扱える。
平行直線の同一直線性は外積で検査し、両有限パラメータ範囲を厳密なアフィン式で照合する。

支持接点が唯一と証明できた後に、元の有限範囲への所属を検査する。
線分は有理数パラメータ、円弧は符号付き半径と二進回転の逆行列で元の単位円座標へ戻し、
既存の `_arc_membership` による短い扇形の区間検査を使う。
領域端のSTART/ENDと内部INTERIORを区別し、どちらかがEXTERIORなら無交点。
所属が未確認なら支持接触の証拠を残したUNVERIFIEDであり、弧端を近傍へ吸着しない。
等号の判定に許容差を使わず、接触配置から1 ULP離れた例も接触へ丸めない。

## CLIと保存

```bash
superfish-ng diagnose-offsets examples/construction/offset_tangency_diagnosis_request.json --out out/offset-diagnosis-new.json
```

要求は診断用schema_version=1で、`curves` に2プリミティブ、`controls` に
first_distance_m / second_distance_mを必須指定する。任意controlsはfirst_interval / second_interval、
endpoint_width、max_series_termsのみ。既定は各[0,1]、2^-100、96項。
線分は有限の増加区間、円錐曲線弧は[0,1]内の増加区間に制限する。
これは構築要求版1や物理Case版1とは異なる入力契約で、`allow_extension` 等は拒否する。

出力にはdocument_type=normal_offset_diagnosis、要求の原データ/正規化SHA-256、
software_version、診断結果と有理数証拠を保存する。保存要求から同じ診断を再実行できる。
既存ファイルは上書きしない。終了コードは未確認で1、事実を証明した診断で0。
終了コード0でもfinite_domain_complete=falseの場合がある。完全性は別フィールドで確認する。
出力を `export-constructed-case` やFEMのCaseとして利用してはならない。

## 検証と残件

追加9テストは円の外接/内接と1 ULP差、有限弧の端点/外部/予算不足、潰れと無限対、
楕円/双曲線の共有区間・逆向き・共有端点、直線と円、平行直線の重複/端点/離隔、
尺度/交換/二進回転の未確認保持、支持円一致と有限弧の区別、CLIの保存再実行・厳密入力・
未確認出力・上書き拒否。反転した円オフセット等の追加実行記録も保存した。
標準回帰と実行記録は[引継ぎ](CODEX_HANDOFF.md)を参照。

構築版1〜6の再構築結果を変えないよう、診断を既存の交点列挙・候補選択へ暗黙適用しない。
GUI診断表示と構築保存への接続は次節で実装。退化候補の構築、一般の楕円/双曲線オフセットの重解・自己交差、
全弧端での隔離証明は残件。G03全体、旧入力互換、物理ピーク収束は未完了である。
新しい外部資料・依存は使わず、既存の区間演算と初等円幾何・線形代数から独立実装した。

## 保存済み構築・GUIへの接続 — 2026-09-08

`construction_diagnostics` は版5/6の構築を再実行・照合した後、保存された交点探索証明の
domain_boxと符号付き距離を厳密な有理数として診断へ渡す。延長が許可された線分も、
実際の探索区間を使う。診断のために元の[0,1]へ縮めたり、区間端をfloatへ丸めたりしない。

```bash
superfish-ng construct-tangent examples/construction/degenerate_fillet_request.json --out out/degenerate-construction-new.json
superfish-ng diagnose-construction out/degenerate-construction-new.json --out out/construction-diagnosis-new.json
superfish-ng diagnose-construction out/construction-diagnosis-new.json --out out/construction-diagnosis-replayed-new.json
```

この例の最初の構築はUNVERIFIEDを保存して終了コード1になる。診断は有限範囲で唯一の
接触を証明しても、元の構築状態を変更しない。第2/3コマンドは診断の証明で終了コード0、
出力のconstruction.statusはUNVERIFIEDのままである。FEMへ渡せるCaseは生成していない。

新規診断文書はschema_version=7 / document_type=construction_offset_diagnosisで、
元のconstruction全体、parameter_domain_box、diagnosisを保存する。構築文書自体の版や
内容は変えない。再読込は元の構築要求から再構築し、診断も再計算して文書全体を照合する。
診断、探索区間、構築内容、文書版の改変は拒否する。これは署名ではなく現在の実装での再現照合である。
Pythonではdiagnose_construction / replay_construction_diagnosisを使える。
CLIは保存構築または保存診断を受け取り、新規ファイルだけへ出力する。
診断UNVERIFIEDは終了コード1だが、元の構築がCASE_VALIDATEDである場合もある。
有理支持の円・直線の横断交点は版5、一般の二進回転/直線長は版6の対象。
直線と非円楕円/双曲線の全域射影境界・接触証拠は版7の対象。旧版1〜6は当時の規則を保持する。
その他の未確認診断も、構築の合格を取り消す根拠にはしない。

GUIは版5/6構築の候補表示・選択後検査・再読込時に同じ診断を別欄へ表示する。
「中心軌跡の診断を保存」からサーバーの直列化文字列を保存でき、構築ファイルと同じ入力欄で
再検証して開ける。要求/候補の編集や改変拒否では診断保存も無効化する。
元の構築ファイル保存と適用条件は維持し、診断がCERTIFIEDという理由で適用を許可しない。
構築版1〜4にはこのオフセット診断を付けず、従来の保存/再構築を維持する。

追加5テストは端点接触診断と未完成Caseの分離、延長区間の一致、通常の構築合格と
特殊ケース未分類の両立、旧構築版の維持、改変拒否、CLI保存再実行/上書き拒否。
Chrome11操作で診断表示・ダウンロード・再読込・改変拒否と未確認構築の適用不可まで確認。
診断対象は2026-09-13の受入範囲まで拡張した。異なる支持曲線の一般重解や退化からの新しい構築候補生成は未実装である。
