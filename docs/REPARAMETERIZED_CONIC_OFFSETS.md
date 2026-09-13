# G03: 主軸表現が異なる同一円錐曲線の法線オフセット

2026-09-14 JST、専用範囲を受入。開始HEADは9da1f92。
同じ非円楕円、または同じ物理的な枝の双曲線を別の主軸で表し、向きを補正した距離が等しい場合を扱う。
距離は零・非零のどちらも含む。支持の厳密な同一性、有限弧の重なり/共有端点/離隔、
反射自己交点の全元点対と中心の重複除去、元保存版の再現を受入条件とした。
API/CLIと構築付属診断のGUI表示・保存・実再起動を確認した。
異なる支持曲線の両非零オフセット、新フィレット構築、双曲線の異なる物理的な枝の一般交差は残件。

変更前の3例は、楕円の正長重なり、楕円の1自己交点、双曲線の1自己交点がいずれも全域未確認だった。
独立に分かる元点/区間と旧結果はout/reparameterized-conic-offsets-20260914/baseline.jsonへ記録した。
親G03と全計画の完了には含めず、親33=8受入/17進行/7他未受入/1範囲外を維持する。

## 支持曲線の厳密な変換

元点はC+A u(t)、A=R diag(a,b)、R=((c,−s),(s,c))。
c,sは既存の二進回転規約の値で、c²+s²を1へ丸めない。
両中心が等しいとき、M=A₁⁻¹A₂を有理数で求める。第1曲線のa,b,c,s、第2曲線のu,v,x,yに対して

```text
n = c²+s², dot = cx+sy, cross = cy−sx
M = ((dot*u/(n*a), −cross*v/(n*a)),
     (cross*u/(n*b), dot*v/(n*b)))
```

楕円の同一支持にはMが直交行列であることが必要。
両Aの列は直交し、非円では主軸長が異なるため、MはI、−I、左右90度回転の4通りに限られる。
具体的にはMの回転角φについて、列の直交条件が(a²−b²)sinφ cosφ=0を与える。
これらの行列との厳密な等号を検査し、第2元角度から第1への変換t₁=t₂+λπ、λ=0,1,±1/2を保存する。

双曲線ではMはdiag(1,−1)を保持する正行列式の変換。
双曲回転を使って表すと、元の列の直交条件は(a²+b²)sinhη coshη=0となり、M=Iまたは−Iに限られる。
さらにbranch₁=M₀₀ branch₂を確認する。M=−Iならt₁=−t₂となり、枝番号の変更と元パラメータ反転が同時に必要。
同じ陰関数でも異なる物理的な枝を、この一致判定で同じ弧と扱わない。

各弧の元パラメータ増加方向へ直した距離はsign(spanᵢ)dᵢ。
第2曲線は変換の微分ε=dt₁/dt₂も掛け、sign(span₁)d₁=ε sign(span₂)d₂を厳密に確認する。
不一致はこの専用処理の対象外であり、離隔の証明にはしない。

例えばこの環境の回転.3と.3+πでは二進係数が厳密に反対になり、非単位ノルムのまま一致を証明できる。
.7と.7+πでは一致しない。回転角の差が浮動小数点でπに近いことを支持の等号へ代用しない。
半軸・中心・回転の1 ULP差も吸着しない。

## 有限元点対と中心数

元の分率区間端はstart+span*fractionを有理数で保持する。
楕円は第2角度区間へ(λ+2k)πを加え、認証付きπ区間で可能な全整数kの範囲を列挙する。
双曲線は第2パラメータ区間をε倍するだけで、周期を導入しない。
正長の重なりはINFINITE_PARAMETER_PAIRS、厳密な孤立共有端はSHARED_PARAMETER_ENDPOINT、
残る場合は有限中心数またはDISJOINTを返す。比較が分離しなければ未確認を保持する。

πの係数が非零の移動を二進の角度へ丸めない。
例として第1楕円の終角が保存値math.pi/2、第2楕円の主軸交換後の始角が真のπ/2なら、わずかに離れている。
終角を次の二進数へ進めると正長の重なりになる。どちらも共有端点にはしない。

異なる元点同士の一致には、既存の[同一円錐曲線の反射自己接点](SAME_CONIC_OFFSET_SELF_INTERSECTIONS_PLAN.md)を使う。
第1座標系で候補を求め、Mの転置で第2の正規化座標へ戻して、両方の元有限弧へ所属を照合する。
contacts_in_original_frames、membership、parameter_pair_directions、included_parameter_pairsに
両座標系と可能な2通りの元点順序を残す。未確認の方向を無交点へ読み替えない。
共有端点と同じ中心なら一度だけ数える。複数の元点対と中心数は異なる量である。

既知の例として楕円半軸(2,1)、距離3/4ではsin²t=5/12、cos²t=7/12の反射元点対が一致する。
第1弧[.5,1]と、半回転した第2弧[2,2.5]は1中心を持つ。
双曲線半軸(2,1)、第1枝+1/距離−3/4と、半回転した第2枝−1/距離+3/4ではsinh²t=1/4。
両元パラメータ区間[.25,.75]から1中心を確認する。これらは合成幾何で、測定構造ではない。

## 入出力と保存版

新規診断は版11。旧公開分類器の本体を_classify_offset_degeneracies_v10として保持した。
保存構築診断1〜10はそれぞれの旧規則で再検証し、構築自体は版1〜9を維持する。
旧結果で全域分類済みなら保持する。新処理が未完で旧共有点の証拠がある場合は、その証拠も保持する。

独立診断要求は版1、出力normal_offset_diagnosisは版11。
厳密な既存制御だけを受理し、support_tolerance等の未対応な入力を拒否する。

```bash
superfish-ng diagnose-offsets examples/construction/reparameterized_conic_offsets_request.json \
  --out out/reparameterized-offset-diagnosis-new.json
```

[この例](../examples/construction/reparameterized_conic_offsets_request.json)は上記の楕円1中心。
完成Caseではない。GUIでは既存の構築文書に付く診断として表示・保存する。
独立診断要求を構築要求へ読み替える機能や、診断完了によって構築の適用を許可する機能は追加していない。
新しい有限元点をフィレット候補へ接続する処理は次段階である。

## 検証と来歴

関連103 unittestが57.033秒でPASS。初回の追加6件は5合格/テスト前提1失敗、0.554秒。
回転.3と.3+πの二進係数が一致しないという期待が誤っていたため、実際に不一致の.7へ修正し、
.3の厳密一致・非単位ノルムも検査した。製品コードはこの修正で不変。
旧テストの新規診断版の期待は10から11へ更新し、保存旧版の期待は維持した。

専用validatorは1,984条件、8.755431秒でPASS。反射元点対435組、無限元点対を持つ条件608件。
尺度2^-40/1/2^40、両主軸順、二進一般回転、正負/零距離、反転/交換、両枝番号と有限分率制限を含む。
参照は既存の独立な法線成分の140桁二分法とAGMのπ、独立三角関数・対数を使用する。
製品の支持変換・反射根の閉形式・区間所属判定を参照値へ使わず、元の点＋有向単位法線を両座標系で照合した。
参照側は固定17周期で有限範囲を覆い、全分類/数、両元座標の囲みと元点対の両方向を確認する。
小さな参照丸め残差を許す数値的な照合であり、参照数値そのものを認証付き証明やFEM誤差保証とはしない。

```bash
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v \
  test_reparameterized_conic_offsets test_conic_implicit_offset test_circle_conic_crossings \
  test_line_noncircular_crossings test_circle_conic_fillet test_circular_fillet \
  test_algebraic_circular_offsets test_finite_circular_crossings test_general_coincident_circle_arcs \
  test_same_conic_offset_intersections test_line_noncircular_offset_contacts \
  test_offset_degeneracies test_construction_diagnostics test_conic_fillet
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python scripts/validate_reparameterized_conic_offsets.py \
  --out out/reparameterized-conic-offsets-independent-new
```

自前の保存診断10は開始HEADで全文再現し、tests/fixtures/offset_diagnosis_v10.jsonへ元バイトをコピーした。
元はout/conic-implicit-offset-browser-restarted-20260914/downloads/construction-9-new-diagnosis-10-diagnosis.json。
88730 bytes、SHA256=f382eae576cae0849151e5794e936fe1761cc5ffd40dd19c8fbbc58e2546a750。
開始時に記録した未確認診断を同じ再現済み構築へ付ける追加API照合でも、版10は未確認のまま、版11は1中心となり、
版番号だけを変えた文書は拒否した。この追加文書は過去のブラウザー保存ファイルとは区別して記録した。
既存の自前数学・実装・独立検証を再利用し、新外部資料・依存・旧版資産/実行・subagentは使っていない。

実Chromeは7入力、初回46/実サーバー再起動44チェック、各17取得でPASS。
新しい楕円有限/重なり・双曲線有限・精度不足を構築5の付属診断で表示し、構築の未確認と適用不可を保持した。
旧保存診断10、新構築9の診断11、生要求の候補選択/Case適用/native保存、改変拒否・編集失効・beta拒否も確認。
全17保存ファイルが再起動前後でバイト一致し、再起動後の楕円有限/双曲線有限/精度不足3画面を目視した。
実CLIも上記1中心を版11・全域完了で出力して終了0。両GUIプロセスは正常終了して停止済み。
検証後の製品301ファイルは不変で、全suite/seed/Hosted CIは実行していない。許容差/benchmarksは不変。
既存構築5のFEM尺度unitは含むが、新たな構築や離散化精度の受入ではない。

集約はout/reparameterized-conic-offsets-20260914/acceptance.json。
同ディレクトリに初回/最終ログ、CLI結果、fixture来歴、ブラウザー入力とバイト比較を保存した。
独立結果はout/reparameterized-conic-offsets-independent-20260914、
ブラウザー結果はout/reparameterized-conic-offsets-browser-{initial,restarted}-20260914。
異なる支持や向き補正後の距離が異なる両非零オフセット、異なる物理枝の一般交差、新フィレット構築、
物理ピーク収束・G03全体・C00.V/V02と全計画は継続中である。
