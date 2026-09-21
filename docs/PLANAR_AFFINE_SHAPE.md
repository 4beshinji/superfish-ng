# P01 — 平面調整用の多項式アフィン形状法則

2026-09-22。P01の第一段階として
[PlanarAffineShapeLaw](../src/superfish_ng/planar_affine_shape.py)を実装。
**調整要求/runner・追跡・所有保存への接続は未完了で、P01はIN_PROGRESS**。
既存のschema_version 1の平面調整を変更していない。

元の明示xy多角形Projectから x(p)=A(p)x0+t(p) を生成する。
pとAの係数は無次元、tの係数はm、係数順序は昇冪で各要素0〜8次。
閉区間boundsを法則に保存する。有限JSON数・全キー・単位を厳密に検査し、
既存矩形Caseの暗黙の多角形化はまだ行わない。
保存はkind `polynomial_affine_xy` と明示係数/単位/boundsを持つ独立宣言である。

行列式多項式を有理数演算で作り、既存Sturm根数器で閉区間の全零点を数える。
恒等ゼロ、端点零点、内部の偶数重根もFEM前に拒否する。
独立の反例det A=(p−3/8)²は両端で正のため端点検査では不十分だが、本実装は拒否する。
同じ多項式に2^-40を加えた対照はゼロ点がなく受理する。
負の行列式が全区間で保持される反転は許可し、多角形と三角形の向きを正へ戻す。

係数と元binary64座標はその厳密な有理数として計算し、最終座標だけをbinary64へ丸める。
試行は必ず元Projectから生成し、前試行からの累積変形を行わない。
元Project・全メッシュ番号・表示単位・偏極・次数・モード数・壁導電率とU′[J/m]を保持する。
未解決の丸め/潰れた要素/境界不整合はPlanarMeshの既存検査で拒否する。
行列式に根がないことは良条件性や一般の浮動小数点精度の保証ではない。

## 検査と限界

新規[3テスト](../tests/test_planar_affine_shape.py)を次の分割証拠で確認した。

- `test_closed_interval_rejects_interior_even_root_and_endpoints`：端点/内部重根/恒等ゼロ拒否、正の微小対照をPASS。
- `test_original_project_area_shear_reflection_and_serialization`：非一様尺度/せん断/反転/移動、独立有理座標、面積行列式、順不同の元Project生成、U′/表示単位保持、JSON往復/単位・bool・範囲外・矩形拒否、丸めによる潰れ拒否をPASS。
- `test_real_fem_rotation_and_uniform_scale_fixed_energy_per_length`：実P2 FEMの90度回転/2倍尺度のf→f/2を相対2e-12、同一U′、既存uniform_scale Studyと別生成Projectの一致をPASS。

初回 `python -m unittest -v test_planar_affine_shape` は3件0.242秒、2PASS/1ERROR。
ERRORはテストがPlanarCaseの必須width/heightを省略したTypeErrorであり、製品の形状法則は変更せずテストを修正した。
同じメソッドへ丸め潰れ拒否も追加し、その1件のみを再実行して0.085秒PASS。
全3件は分割証拠で合格。初回失敗を隠して単一の全件PASSとは報告しない。
実行は `OPENBLAS_NUM_THREADS=1 PYTHONPATH=.:src:tests UV_CACHE_DIR=/tmp/superfish-uv-cache uv run --no-sync --python .venv/bin/python python -m unittest -v ...`。

製品の既存経路からは未使用の新規モジュールで、shared-core/seedの変更はない。
FEMはテスト内の実計算。解析値への置換なし。新しい外部資料・依存なし。
既存の有理多項式/SturmとPlanarMesh検査を再利用し、旧コード/実行物を参照していない。

## P01の残り

調整要求の新版へ法則を接続し、元矩形との一致、全試行/最終細分、保存再生を確認する。
丸めた試行間を単純なfloat行列商で「厳密アフィン」と断定しない。
元分割に基づく対応または既存厳密比較契約を満たす明示写像を保存し、
場の回転/せん断/尺度則・固定U′の実E/H比較とID追跡を独立に検証する。
初期未解決モード、最終細分/別周波数gate、strict要求、既存寸法tune回帰も必要。
これらの接続・検証前にP01または親P02/D02を閉じない。
