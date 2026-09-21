# 曲線Hφの探索候補と最終細分（H13-cの途中段階）

`build_curved_hphi_tune_trial`は元Projectと全P2形状則から候補を作る。探索候補は未細分の形状、最終候補は同じ二次領域を明示回数だけ細分した形状を持つ。`curved_hphi_trial_comparison`は両候補をさらに一段細分した比較空間を作り、曲線E/H追跡要求へ接続する。

この段階では候補・比較空間の接続を実装する。目標/粗細周波数差の判定、探索の状態遷移、過去anchorからのID回復を含む曲線調整runnerはまだ未実装。H13-cを完了扱いしない。

## 元領域を保持する仕組み

候補は必ず元Projectに[全P2形状則](CURVED_HPHI_SHAPE.md)を適用して生成する。最終細分でも、採用した候補の二次境界を解析曲線へ再投影しない。細分はH13-aの有理数P2制限を使い、各子の参照座標を親chartと有理数演算で合成する。

結果は候補Project、未細分の完全二次参照幾何、そこへ戻る全native chart、元scalar空間からの累積prolongation、形状/細分/最終被覆の診断を持つ。P1/P2次数、全穴/軸、加速経路、エネルギー/導電率等は保持する。prolongationは場の検査用で、新固有場や周波数の代わりには使わない。

各段の制限だけでなく、最終nativeから元の未細分領域への全制限も検証する。非dyadic寸法で累積した丸めは明示`binary64_roundoff`契約で再検査し、段ごとの成功から元領域一致を推測しない。元参照chartの被覆は厳密で、native係数の丸め上限は別に報告する。

形状生成前に、実行する細分数に応じた要素・全scalar DOF・pair数を計算する。最大8段、利用者の予算を超えれば`UNVERIFIED`予算例外で停止する。root一セルにk個の子がある場合、自己分割の`k(k−1)/2`とroot/子比較のk組を含めて上限を確認する。比較空間は追跡controlsの予算を使って別途構築・検証する。

比較要求は各候補の未細分参照幾何どうしの二次対応と、元native/さらに細かい比較nativeの全chartを含む。前のIDまたはID集合は呼び出し側が明示する。前後の固有場は元Projectに対するFEMで別々に求め、追跡器へ渡す。過去の係数転送や解析尺度則を固有解として使わない。

## 独立検査と記録

証拠は`out/h13-curved-trials-20260921/`。`before.log`は新APIのimportで失敗（1件、0.217秒、終了1）。既存FEM不具合のredではなく、新候補生成機能の欠落を確認した。

`after.log`は初期2件、25.913秒、終了0。q/u・非dyadic尺度0.7から値1.3の候補を作り二段細分。独立尺度則の体積1.3³、全元参照領域の有理数被覆、`P.T M_f P=M_original`相対1e-10、定数場保存、加速経路不変を確認した。予算不足/不正phase/不正段数は形状生成前に拒否する。

追加試験は実曲線穴付き探索候補から最終細分候補へ、独立FEMのE/HでIDを追跡する。関連は`test_curved_hphi_shape_tuning test_curved_hphi_refinement`。実行は`OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-uv-cache uv run --no-sync --python .venv/bin/python python -m unittest -v <modules/cases>`。

既存形状生成・P2細分・有理数共通領域・E/H追跡を接続した。新外部資料・依存・legacy参照なし。既存FEM/seed TM/物理許容差は変更しない。全suite・目標調整・所有保存・GUIの受入ではない。

`tracking.log`：実曲線穴付き探索→最終細分の追加1件、105.937秒、終了0。両側を独立にFEMで解き、元の二つのIDをE/Hで確認。さらに一段細分した現在比較空間も未細分候補へ完全chartで結び、元の係数配列が不変であることを確認した。

`related.log`：形状変数4件と細分6件の計10件、39.615秒、終了0。初期2件と追加1件を合わせ新3件を検証した。全検査handle終端、成功後の数値変更なし。次は曲線調整runnerの状態遷移・目標/粗細周波数差の別判定・明示ID回復を接続する。
