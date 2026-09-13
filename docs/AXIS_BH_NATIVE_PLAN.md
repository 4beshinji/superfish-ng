# S04: 軸接続P1非線形磁場の保存・CLI

2026-09-13 JST。後続限定課題。未実装・未受入。

専用AxisBHCaseのB-H表/来歴・全Jphi/固定a/Ht/軸正則境界・求積/Newton設定/初期係数を保存する。元a=Aphi/r[T]、全軸DOF、幾何勾配/所有/界面/穴、g/電流/自然荷重[A m²]と接線[m⁴/H]、反復履歴と全J U/U*・A周回/A m²反力/Wb磁束を同じ非線形FEMで照合する。元Bはaの微分から、Hと接線は元Bと表から再構成し、セル頂点の診断値を一定セル場へ読み替えない。qとq+4の診断も保持する。

成功nativeは5ファイル、失敗nativeはcase/failure/manifestの3ファイルに分離する。軸失敗報告は版2、coefficient_field=aphi_over_r_tとlast_valid_coefficientsで係数を明示する。失敗読込でも同じCaseを再試行する。solve/replayは成功0、収束失敗1、入力/保存検証エラー2。probeは元6場と片側材料/来歴/表区間を返し、失敗nativeのprobeは拒否する。

受入は独立検証済み問題のAPI/CLI保存ファイル・probe全JSON一致、失敗3種類の保持、再ハッシュした場/表/接線/反復/求積診断等の改変拒否、途中出力/リンク/検証中の変更/上書き拒否を含む。全軸DOFとaに定数gaugeがない規約を保持する。独立ソルバー比較や旧版互換保存とは呼ばない。標準と旧周波数/RF差を確認して専用APIを限定受入する。Project/GUI/Study、軸非接続・P2・履歴型材料/力/RFはこの工程に追加しない。
