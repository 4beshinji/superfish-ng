# G03: 一般二進回転・直線長を保持する円オフセット診断

2026-09-14 JST 後続更新：[構築版9](CIRCULAR_FILLET.md)で円同士の全元点対を候補/Caseへ接続した。
本分類器と診断版の規則は変更していない。以下は診断実装時の受入記録である。

2026-09-14 JST、専用範囲を受入。有限円交点の次の限定子課題。

対象は全ての既存円弧/直線プリミティブの有限法線オフセット。
円の二進回転(c,s)を正規化せず、L=√(c²+s²)、向き補正距離d、
符号付き半径ρ=aL−dを保持する。直線も元二進端点差Dから
原点P+d JD/√(D·D)を保持する。

二つの支持式に必要な元平方根は最大2個、交点の平方根を含め最大3段階。
各段階のx+y√rについてr>0を先に証明する。同符号のx/yはその符号、
異符号ならsign(x+y√r)=sign(x) sign(x²−r y²)となる。
右辺は下位段階だけで評価でき、0の等号も有理数まで再帰できる。
√8=2√2や√(3+2√2)=1+√2のような従属関係もこの等号で保持する。
一般の記号式除算は不要で、除算は有理数、局所座標は符号を証明した
分母の有理数区間を使う。局所座標の0/±1だけは先に代数等号を検査する。

受け入れ条件:

- 異なる円の外接/内接/横断/離隔、同心円、潰れた円、直線円、
  非平行/平行直線を元の支持式に従って分類する。
- 一般回転の厳密な接触と1 ULPの離隔を丸めず分ける。
- 有限弧端・線分端・明示範囲、交換/反転/尺度を検証する。
- 不明な端点所属/精度予算はUNVERIFIEDとして保持し、構築可否を変更しない。
- 新規診断版6と旧保存版1〜5を別規則で再検証し、CLI/GUIの保存往復を検証する。

検証は有理数・代数の独立恒等式、120桁Decimalの別幾何参照、関連テスト、
実Chromeの診断入力/取得/再起動とする。新依存なし。FEM・フィレット生成は変更しない。
非円楕円/双曲線の一般弧端/重解、新フィレット候補、物理ピーク収束、
C00.V/V02と全計画の完走は別の残件として維持する。

## 実装と数値検証

`quadratic_radicals.py` に3段階までの正実平方根、加減乗算、有理数倍、
再帰的符号、尺度を保持する有理数区間を実装した。表現が既約であることを
仮定しない。幾何以外の汎用代数システムや記号式除算は導入していない。
`algebraic_circular_offsets.py` はこの演算で支持交点と元有限区間を分類する。
新規診断版6は先行版の完全な結果をそのまま使い、未確認の円/直線だけを拡張する。
旧版1〜5の保存再検証、元構築、Case適用可否、FEMと画面実装は保持する。

代数式の分母や有限弧所属が区間で分離できない場合、内部平方根幅を
追加64ビットずつ最大2回細分する。端点の三角級数予算は増やさない。
それでも判定できない所属はUNVERIFIED。有限中心数を推測しない。

開始時の一般回転の外接/内接/円二交点/直線円二交点は全てUNVERIFIED。
独立に分かる中心数1/1/2/2と、追加後の一致を
`out/algebraic-circular-offsets-20260914/initial-invariants.json`に保持した。
旧版5 fixtureは親`94b879c`の公開診断経路を変更する前に自前構築2件から生成した。

関連58テストは25.348秒で合格。新しい根号演算3件と円/直線診断6件に、
先行の有限円・同一円・一般同一円・同一円錐曲線・構築診断・弧間フィレット、
直線弧フィレットのCase/面積/体積/保存/GUIの直接利用先を含む。
厳密な外接/内接と1 ULP内外、無理直線長の接触と両端点、潰れ、
同心円、平行直線の一致/分離、2^-200〜2^200尺度と低予算を検査した。
初回51件の9失敗は、拡張後も旧未確認/版番号を要求していた期待値。
旧版再検証を残して更新し、`first-focused.log`も保持した。

独立driverは製品の根号代数を呼ばず、160桁DecimalのEuclidean距離、
直交射影、Newton角度とAGM πで円・直線の位置と有限所属を照合する。
1,944条件が9.362秒で合格し、0点1,320、1点384、2点240。
各参照交点の元支持式も検査した。交換・反転、負の符号付き半径、部分区間、
2^-160/1/2^160尺度を含む。正確な接触は上記の独立な代数恒等式テストで扱い、
汎用Decimal参照でほぼ零の判別式を接触へ丸めない。
記録は`out/algebraic-circular-offsets-independent-20260914/report.json`。

再現（出力先は未使用のパスに変える）:

```bash
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v test_quadratic_radicals test_algebraic_circular_offsets test_finite_circular_crossings test_offset_degeneracies test_construction_diagnostics test_coincident_circle_arcs test_general_coincident_circle_arcs test_same_conic_offset_intersections test_conic_fillet test_line_conic_fillet.LineConicFilletTests.test_version6_case_area_volume_replay_and_gui
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python scripts/validate_algebraic_circular_offsets.py --out out/algebraic-circular-offsets-independent-new
```

平方根の符号式は上記の二乗差から独立に導出した。既存の自前有限弧所属と
独立参照のNewton/AGMのみを再利用し、新規外部資料・依存・旧版資産/実行はない。
対象テストには既存の弧間フィレットFEM尺度試験を含むが、全suite/seed/Hosted CIの
再実行ではない。物理規約・許容差とbenchmarksは不変。

実Chromeは旧版5/新版6の8入力（円/直線円の二交点、無理直線長での接触、
既存の有効Case）の初回と実サーバー再起動で計62チェック・32取得が合格。
全JSON、元構築・適用可否、保存ファイル再読込、改変拒否と編集時無効化を検査した。
再起動前後の全保存バイトと実行中の製品sourceが一致。新版の3画像を目視した。
記録は`out/algebraic-circular-offsets-browser-{initial,restarted}-20260914/`、
集約は`out/algebraic-circular-offsets-20260914/acceptance.json`。
両GUIサーバーは終了0で停止済み。
