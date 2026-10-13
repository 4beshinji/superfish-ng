# 境界再メッシュの独立幾何・実FEM・保存受入

2026-10-13 JST、ADD-N04-boundary-remesh-06 **DONE**。先行GUI commitは `298aafe`。
[原仕様](CURVED_BOUNDARY_REMESH_SPEC.md)の全ゲートを維持し、専用validator
`scripts/validate_curved_boundary_remesh.py` を追加した。製品源・既存検査・許容差は変更していない。
全136カードは88 DONE/2 IN_PROGRESS/46 PLANNED、原123は76/2/45。
境界再メッシュ01〜06は完了。次は[RF重み付き版5の一般対照仕様](N04_REMAINING_CARDS.md#add-n04-rf-goal-01)。
適応の親N04、原互換32要件、全goalは継続する。

## 固定した入力と計算

円筒はR=.1 m、L=.2 m、TM010、U=1 J。要求弦長.045/.0225 mと弦面積.0005/.000125 m²の二水準、
各尺度1/2で4 FEM。非アフィン例は既存の合成半楕円断面を尺度1/2で2 FEM。
Caseの長さ・角近傍と生成の長さ/面積条件を同時に尺度変換し、幾何・場ともP2、求積次数12で実行した。
全入力/ゲート・1時間/32 GiB予算を求解前に`plan.json`へ記録した。

最終メッシュは円筒粗128要素/32境界辺、細512/64、非アフィン84/28。両尺度の接続/固定patternは一致した。
解析式はFEM後の評価だけに使い、固有値/場の生成や補正には使わない。
GUI/workerの7 FEMは先行05の別証拠。本工程は**6新FEM、再利用FEM0**。

## 独立ゲート

| 原条件 | 観測と判定 |
|---|---|
| 全二次境界 | native primitiveの全breakpoint和集合を作り、Lagrange点から独立にBernstein三係数を求める。全254共通区間、最大係数距離1.665e-16 m、各元512eps×座標尺度以下 |
| 三幾何積分 | 別P2基底8×8 Duffyの面積、回転体積、∫r³drdzを、境界Green三式と照合。最大相対7.459e-15、元3e-12以内。矩形の閉式RL/πR²L/R⁴L÷4も確認 |
| 既知場と尺度 | Hφ=rの組立M、元領域保存、尺度4/8/32を原3e-12以内で確認。元曲線へ再投影せず、各新seed→子の制限を評価 |
| 親子K/M | 全新prefixの独立組立とPᵀK_childP、PᵀM_childPを比較。最大相対norm1.436e-15、元1e-10以内。旧独立meshとのGalerkin関係は仮定しない |
| サイズ/品質/予算 | 最終全辺・弦面積が要求×(1+1e-12)以内。弦角/二次接線角は独立微分で計算し元下限以上。全prefixの要素/境界辺数も保存文書と一致 |
| 拒否 | 元境界区間数未満・サイズ競合・反復枯渇・未知キー・raw重複・保存改変を拒否。追加の境界gap/overlap/tag/未対応の向き/中点移動は独立検査と公開境界APIの両方が拒否。旧sourceのfrozen履歴も新seedへ適用できず拒否 |

Green式は1/2∮(r dz−z dr)、π∮r²dz、1/4∮r⁴dz。
境界の向きによる符号を別に残し、一貫した向きと正の物理測度を照合する。
三式の最終項も8点Gaussで独立に評価する。

## 周波数・元場・RFを分けた円筒評価

以下は各尺度の最大相対誤差。周波数は3e-3、両R/Q・G・Tは1e-2、
物理体積重み付きE/Hの相対L2はそれぞれ2e-2が原ゲートで、すべてPASS。

| 水準 | f | 両R/Q | G | T | HのL2 | EベクトルのL2 |
|---|---|---|---|---|---|---|
| 粗128要素 | 3.316e-7 | 1.274e-4 | 3.178e-6 | 4.236e-6 | 3.824e-5 | 8.152e-4 |
| 細512要素 | 2.150e-8 | 9.340e-6 | 2.133e-7 | 1.490e-7 | 4.831e-6 | 2.074e-4 |

既存の独立Bessel参照`analytic.pillbox_tm_mode`とSciPy J0/J1を再利用した。
TM010のHφ=H0J1(χr/R)、Ez=E0J0(χr/R)、Er=0を、全要素64点の独立P2物理体積重みで比較する。
Hの全体内積から決める単一符号をE/Hで共用し、点ごとの符号変更や振幅フィットは行わない。

## 非アフィンの尺度と保存

fの1/2、両R/Q/G/Tの不変の最大相対差は3.855e-14。
U=1 Jの場の2^-3/2則はHの相対L2が1.944e-15、Eベクトルが4.951e-15。
追加の各成分照合も最大1.402e-14で、原1e-9以内だった。
各比較は全84要素×64点、元場の物理体積で重み付けした。
独立体積積分の各電気/磁気エネルギーは0.5 Jから最大9.437e-15 J差であった（追加観測）。

全6 nativeを公開readerで再構築し、10配列ずつ、元Project/初期mesh、全mode/RF、規約、
元surface値を保存出力と照合した。全54ファイルは検証前後byte一致。
全RFを元場から再計算して元1e-12以内、保存された両R/Q定義とピークphasor規約も維持する。
離散surface値の完全保持を連続物理peak精度と読み替えない。
非アフィンの連続物理精度/物理peak精度はUNVERIFIED、物理誤差上界はnull。

## 実行と先行証拠の結合

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-uv-cache uv run --no-sync python scripts/validate_curved_boundary_remesh.py --out out/<new-directory>
```

専用runは58.057秒、handle27607終了0/PASS。全1458源を前後固定し、6新FEMを完了した。
その後、全境界拒否の証拠を明示するため、検証器に`boundary_refusals`と呼出しを追加した。
この追加だけをhandle50470で検査し、6反例PASS、新FEM0。
数値run時の検証器を`validator-six-solve.py`に保存し、既存の全数値関数ASTと、
mainの追加呼出し以外のAST一致を確認した。成功した6 FEMは再実行しない。
追加反例は尺度2の実呼出し条件でもhandle58392でPASS。証拠集計の初稿は書込中の自己logを
hash対象に含めたため、初稿を保全して対象から除き、metadata監査だけを訂正した。

[03](CURVED_BOUNDARY_REMESH_CORE.md)の41個別unitと[04](CURVED_BOUNDARY_REMESH_SAVED.md)の20個別unitは、
元test源と生成関数ASTを現行源へ照合して再利用した。両群は重複があるため合算しない。
元Caseの全辺/境界/角近傍、粗化、TE対称/反射、全prefix予算と旧履歴拒否もこの範囲に含む。
[05](CURVED_BOUNDARY_REMESH_GUI.md)のHTTP2・実Chrome42操作、保存/中止再開/再起動、7 nativeの
全63保存fileもSHAで結合した。本工程の追加GUI/worker求解は0。

rawは`out/n04-boundary-remesh-acceptance-20261013/`。
`report.json`は元6求解の独立結果、`acceptance.json`は保存・先行証拠・各場成分の監査、
`boundary-refusals.json`は追加反例、`final-acceptance.json`は現行validatorへの結合である。
元入力/output/source hash・全logを保持し、全実行handleは終端。
新unit/seed/full/legacy実行0。科学核・旧テスト・ゲート変更0、新外部資料/依存/サービス0。
既存P2制限、別基底積分、公開Bessel/Green数学を再利用した独立検査であり、
一般物理誤差上界、普遍的再メッシュ優位や親N04全体の完了を主張しない。
