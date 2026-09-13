# G03: 直線と非円円錐曲線オフセットの全交点

2026-09-14 JST、専用範囲を受入。接触証拠に続き、一般交差とカスプを含む全根を列挙する子課題。
受入条件は二進回転/符号付き距離を保持した全実根数、二乗で生じる偽解の除外、
有限弧/線分所属、チャート境界と同じ中心の重複統合、予算不足の未確認、旧保存互換性。
既知の軸交点・双曲線交点・自己交点が旧分類では全域未確認になることを着手時に記録した。
元FEMや既存構築を変更せず、診断版を分けて保存する。一般フィレット構築は後続に残る。

楕円はH=1+q²、局所単位座標(h(1−q²),2q)/H、h=±1、q∈[−1,1]の二チャート。
左半面h=−1の両端は右半面と同じ元点なので除く。
双曲線はH=1−q²、(branch(1+q²),2q)/H、q∈(−1,1)。端は無限遠で除く。
Uを回転後の元位置分子、Vを元角度/双曲線パラメータの接線分子、S=V·Vとすると、
中心軌跡はC+U/H+d JV/√S。dは元向きを調整した距離で、HとSは対象内部で正。

直線のD、N=JD、元始点P、距離dl、k=D·Dについて、
A=N·(C−P)H+N·U、B=d N·JV Hと置く。
支持交点式は(A−dl√k H)√S+B=0。
E=(A²+dl²kH²)S−B²、F=−2A dl H SからE²−kF²=0を有理数多項式で全根分離する。
√kが有理数なら先に保持し、一度の二乗で次数8以下にする。一般には次数16以下。
各根でE+F√k=0と、A−dl√kHとBの反対符号（両零を含む）を確認して偽解を除く。
零判定は平方因子除去多項式とのgcdとSturm根数、非零符号は有理根箱の評価で証明する。
平方根を含む符号は二乗差と元符号から判定する。数値近接を等号にしない。

## 有限所属・重複と未確認

直線分率の端点比較も「多項式＋多項式×正平方根」の符号に戻し、厳密一致を判定する。
元弧の局所座標は有理根箱から囲み、既存の有限弧所属へ渡す。曲率の速度係数が零ならCUSP、
係数が非零で元接線の法線射影が零ならREGULAR_TANGENCY、それ以外はTRANSVERSEと記録する。
これにより元接線が直線と平行でないカスプも残す。

同じ元曲線の二点が同じ中心を与える場合は、既存の[反射自己接点の導出](SAME_CONIC_OFFSET_SELF_INTERSECTIONS_PLAN.md)を使う。
楕円の二つの軸反射は(h,q)→(h,−q)、(h,q)→(−h,q)、双曲線の同枝はq→−q。
反射軸に垂直な中心座標が厳密に零で、二つの根の反射関係をgcd/Sturmで証明したときだけ統合する。
元弧と直線の有限範囲に属する全元点を列挙した後、中心数を返す。接触中心一つと元点二つを区別する。

公開診断の内部予算はチャート毎10,000分割箱、根毎512細分で、証拠へ保存する。
根箱、有限所属、中心同一性のいずれかが未確認なら全中心数を返さない。
版7までに証明済みの接触がある場合はTANGENCY_WITNESSESを保持し、未完了探索を
`evidence.general_crossing_search`へ添付する。極端に狭い要求幅でこの経路も確認した。
これらは専用内部APIの予算であり、公開JSONへ未定義の予算キーを足すと厳密パーサーが拒否する。

## 実装と保存

`algebraic_root_signs.py`に有理多項式の根での符号・零・反射同一性、
`line_noncircular_crossings.py`にチャート列挙・元の交点式・所属・中心統合を実装した。
既存の`polynomial_roots.py`は変更していない。新規normal/construction診断は版8、旧版1〜7は元規則で再検証する。
既存の全域確定診断はその証拠を使い、未確定な直線と非円円錐曲線へ新列挙を追加する。
元構築・Case・候補番号・適用条件は保持する。根の診断完了は新しいフィレット構築完了を意味しない。

先行タスクの自前版7診断4件を、今回の公開分類器変更前にfixtureへ転記した。
`tests/fixtures/offset_diagnosis_v7_line_crossings.json`のSHA256は
`5bd070adf12f2f1bf9137f68a98df4026e0bbcf0d10d2aba06e1c80894e252ac`。
ブラウザー用の追加旧版文書は保持した版7分類器から作り、当時の規則で再検証した。
版7専用の接触テスト/validatorは明示的に版7分類器を呼び、証拠のみの旧契約を維持する。
版8の全交点数は新しい独立参照で検査する。

## 検証

関連83項目の合格を確認した。初回82テストは33.507秒で81合格、新規テスト入力の誤り1件。
要求JSONへ未対応のdocument_typeを付けていたためで、入力を修正してその1件を0.007秒で再検査し合格。
さらに公開経路の予算不足時の証拠保持1件が0.227秒で合格した。製品コードの修正や許容差の変更はない。
初回失敗ログを保持し、83件を一括再実行したとはしない。新列挙器の先行7テスト、根符号/既存Sturmの先行8テストも合格。

独立参照は140桁Decimalで元の三角/双曲線位置・単位法線を直接評価する。
元投影接線と曲率速度係数の零点で単調区間を作り、各区間を二分して交点を求める。
製品の有理チャート・消去多項式・Sturm根を参照の生成へ使わない。
102条件が89.455秒、縦長楕円/双曲線・並進・異なる距離・直線延長の追加13条件が24.018秒で合格。
計115条件で全中心数・元点数・交差/接触/カスプ・位置を照合した。両枝・反転・交換・部分弧と
2^-80/1/2^80尺度を含む。数値参照の零/同一性の識別幅は規格化座標で1e-90、製品の等号判定は厳密代数。
1 ULPの接触分岐・厳密弧/線分端・共有チャート・同一中心の別交点はunitでも確認した。

実Chrome初回/実サーバー再起動は各16入力・70チェック・32取得、計140チェック・64取得が合格。
旧版7/新版8の接触・カスプ・同一中心＋別交点・一般二進回転の16次式・既存有効Caseを検査した。
構築/診断32ファイルは再起動前後で全バイト一致。全構築・全診断・適用可否、改変拒否・編集無効化を照合し、
外部HTTPなし、検証中の全src不変を確認した。新版3画像を目視して全中心数と全域分類表示を確認。
カスプ詳細はCDPで検査した。両GUIサーバーはSIGINT後の終了コード0を確認して停止済み。

記録は次の出力を保持する。再実行時は新しい出力先を指定する。

- `out/line-noncircular-crossings-20260914/initial-invariants.json`、`root-signs-first.log`、`first-unit.log`
- 同ディレクトリの`focused-first.log`、`request-test-corrected.log`、`public-budget.log`、`acceptance.json`
- `out/line-noncircular-crossings-independent-20260914/report.json`
- `out/line-noncircular-crossings-independent-additional-20260914/report.json`
- `out/line-noncircular-crossings-browser-initial-20260914/report.json`
- `out/line-noncircular-crossings-browser-restarted-20260914/report.json`
- `out/line-noncircular-crossings-20260914/verify-browser.mjs`と`browser-cases.json`

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v \
  test_algebraic_root_signs test_polynomial_roots test_line_noncircular_crossings \
  test_line_noncircular_offset_contacts test_quadratic_radicals \
  test_algebraic_circular_offsets test_finite_circular_crossings \
  test_offset_degeneracies test_construction_diagnostics \
  test_coincident_circle_arcs test_general_coincident_circle_arcs \
  test_same_conic_offset_intersections test_conic_fillet \
  test_line_conic_fillet.LineConicFilletTests.test_version6_case_area_volume_replay_and_gui
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python \
  scripts/validate_line_noncircular_crossings.py --out out/line-noncircular-crossings-independent-new
```

現在の専用validatorは追加分を含む全115条件を既定で実行する。追加分だけなら`--family additional`。
FEM/メッシュ・元構築・物理規約・許容差・benchmarksを変更していないため、検証は幾何診断と直接消費先に限定した。
既存conic_filletのFEM尺度テストを含むが、全suite/seed/Hosted CIは再実行していない。
式と全根列挙を自前に導出し、新外部資料・依存・旧版資産/実行は使っていない。
曲線同士の一般交点、新フィレット候補構築、物理ピーク収束、C00.V/V02と全計画は未完。
