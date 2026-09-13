# G03: 異なる円・直線の有限オフセット交点

2026-09-14 JST、専用範囲を受入。BACKLOGの弧端・退化分類の限定子課題。

対象は、有理数の中心・符号付き支持半径を持つ円オフセットと、
有理数の原点・方向を持つ直線オフセット。既存の二進回転の規約を保つ。
異なる支持円の二交点、直線と円の二交点、非平行な直線の一交点を
全候補として列挙し、指定した閉有限区間への所属を検証する。
同じ円、潰れ、接触は従来の認証結果を再利用する。

円の中心差を D、D²を s、半径を R1/R2 とすると、二円の差から
基点 P=C1+αD、α=(R1²−R2²+s)/(2s) が得られる。
交点は P±J(D)√q、q=R1²/s−α²。J は90度回転。
直線と円は、円中心の直線への直交射影 P を使い、
P±D√q、q=(R²−|P−C|²)/|D|² となる。
これらは円の距離式と直線式から独立に導く。平方根は有理数区間で囲む。
有理平方根は厳密に保持し、弧端や線分端への許容差スナップは行わない。

受け入れ条件:

- 解析的な0/1/2交点と各元支持式、弧端、部分区間、線分延長の一致。
- 入替え、向き/距離反転、平行移動、二進尺度変更で中心数が不変。
- 接触の1 ULP内外を別判定し、予算不足は未確認のまま保持。
- 新規診断版5と保存版1〜4を別規則で再検証。元構築・Caseを保持。
- API/CLI、GUIへの応答と元バイト取得を検証する。

TESTING.mdに従い、専用テスト、既存offset診断と構築診断、円弧分類、
直接の構築利用先を選ぶ。FEMメッシュ・構築・RF計算方法は変更しないため、
この限定変更では全suite/seed FEMの再実行は必要ない。
独立検証は元支持式と別の高精度幾何判定を参照する。

無理数の回転ノルムを持つ異なる支持円、非円楕円/双曲線の一般交点、
新しいフィレット候補構築、物理ピーク収束は後続の残件。
G03全体・C00.V・V02・全計画の完了とは扱わない。

## 実装と検証

`finite_circular_crossings.py` が元支持式を満たす全交点の代数表現と
有理数区間を保持する。局所座標への変換を区間化の前に行い、尺度に
依存しない局所幅を使う。有理平方根20/41と厳密な弧端の一致も保持する。
`offset_degeneracies` の新規診断は版5、`construction_diagnostics` の保存版1〜4は
各版の元規則を使う。FEM・フィレット構築・Case・画面実装は変更していない。

変更前の既知2/2/1交点は全てUNVERIFIEDだった。
`out/finite-circular-crossings-20260914/initial-invariant.json` に記録した。
版4 fixtureは親`dbd5327`の自前構築診断2件を変更前に生成したもの。
旧SUPERFISHデータではない。来歴とSHAは同ディレクトリの`acceptance.json`。

最終の関連49テストは24.084秒で合格。新7件と、offset/構築診断、
同一円・一般回転・同一円錐曲線、弧間フィレット全6件、
直線弧フィレットのCase/面積/体積/保存/GUIの直接利用先を含む。
弧間フィレットの既存尺度FEM試験も実行したが、seedや全suiteの再実行ではない。
初回42件の7失敗は、新しい完全判定/診断版に対する旧期待値であり、
旧版再現の検査を維持して明示更新した。`first-focused.log`も保持する。

独立driverは、ピタゴラス三角形の既知交点(0,±4)を通る支持曲線を作る。
製品の交点q式から期待位置を生成せず、120桁の別Newton角度/AGM πで
有限区間所属を照合する。4,896条件が13.633秒で合格。
内訳は0点2,088、1点1,752、2点1,056。入力交換、逆向き、負の支持半径、
部分区間、四分の一回転、2^-200/1/2^200尺度を含む。
記録は`out/finite-circular-crossings-independent-20260914/report.json`。

実Chromeは旧版4/新版5各3件（未構築2件と既存の有効Case1件）の初回と
実サーバー再起動で、計48チェック・24ダウンロードが合格。
全JSON、元構築、適用可否、改変拒否、編集時無効化、保存ファイル再読込を検査し、
再起動前後の保存バイトが一致した。新版2画面を目視した。
記録は`out/finite-circular-crossings-browser-{initial,restarted}-20260914/`。
両サーバーは終了0で停止済み。初回sandboxのsocket拒否は生ログに保持し、
許可されたローカル実行で検証を完了した。

再現コマンド（出力先は未使用のものに変更する）:

```bash
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v test_finite_circular_crossings test_offset_degeneracies test_construction_diagnostics test_coincident_circle_arcs test_general_coincident_circle_arcs test_same_conic_offset_intersections test_conic_fillet test_line_conic_fillet.LineConicFilletTests.test_version6_case_area_volume_replay_and_gui
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python scripts/validate_finite_circular_crossings.py --out out/finite-circular-crossings-independent-new
```

公開数学は円の距離式・直交射影から独立に導いた。既存の自前有理数区間と
独立検証用Newton/AGMだけを再利用し、新規外部資料・依存・旧版実行はない。
物理許容差とbenchmarksは不変。今回の部分合格を全計画の受入へ拡張しない。
