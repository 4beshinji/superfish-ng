# 二次領域を保持する初期メッシュ置換と新しい細分履歴

2026-09-14追補：[内部メッシュの自動再生成](CURVED_REMESH_GENERATION.md)が、元二次境界を保持する完全な置換計画を作れるようになった。
元内部は再利用せず、新履歴も明示/固定する。この文書の置換計画版1とProject APIの受理条件は不変。
以下は各段階の履歴。

2026-09-14追補：[条件別メッシュStudy版4](CURVED_REMESH_STUDY.md)へこの計画を接続した。
全計画を元形状上で検査し、実値の区間で選択して独立変形する。比較写像は元Projectから導き、二分/保存再開・GUIでも保持する。
以下は単独Project API/CLIを追加した段階の記録。

2026-09-14 JST。N04の初期メッシュ変更を伴うStudyへ進むため、
置換する元メッシュと新しい履歴を同時に宣言するAPI/CLIを追加した。
Studyのメッシュ切替規則への接続は次段階であり、この項目をStudy全体の完成とはしない。

## 受入条件

- 元Projectを保持し、別の初期接続と明示した新履歴からportable Projectを作る。
- 旧marked番号を流用しない。新しい全履歴を宣言し、そのメッシュ上の分割選択を固定する。
- 元/先の二次境界全体が一致し、独立な面積・体積と既知場の質量積分が不変になる。
- 同じ解析曲線でも、境界点の再配置で表現する二次領域が変われば拒否する。
- 全新段階の正Jacobian・辺・品質・予算を検査し、不正入力や既存ファイルを上書きしない。
- 置換後の非アフィン変形、実FEM・保存場の追跡と再検証、Maxwell尺度則、円筒解析f/RFを確認する。

## APIと宣言

```python
from superfish_ng.curved_project_remesh import remesh_curved_project

replacement = remesh_curved_project(source_project, plan)
```

入力は未組立・未反射のnative曲線P2、閉PEC・軸のTM Project。
元の幾何、RF、正規化、求解、メッシュ予算、表示設定を保持し、初期メッシュと細分宣言だけを置き換える。
TEや対称半領域を黙って受理しない。

planは次の厳密なJSONオブジェクトである。

```json
{
  "schema_version": 1,
  "source_mesh": {"...": "完全な既存mesh版1オブジェクト"},
  "curved_refinement_steps": [
    {"kind": "marked", "marked_cells": [27], "minimum_corner_angle_deg": 1.0},
    {"kind": "uniform"}
  ],
  "minimum_corner_angle_deg": 1.0
}
```

上のsource_mesh部分は説明用であり、実行例は
[元Project](../examples/curved_project_remesh/source-project.json)と
[完全な置換plan](../examples/curved_project_remesh/remesh-plan.json)を参照する。
合成の二半楕円であり、測定構造ではない。

`schema_version`、`source_mesh`、`minimum_corner_angle_deg`を必須とし、
`curved_refinement_steps`と`curved_refinement_levels`のどちらか一方も必須にする。
細分なしは`curved_refinement_levels: 0`と明示する。
省略による旧履歴の継承や、空のsteps、両方の指定、未知フィールドを拒否する。
元メッシュは既存のm/rz/0始まりの完全なmesh版1入力である。

新stepsの各marked番号は、置換後のその段階直前のメッシュを指す。
同じ整数が旧メッシュと同じ物理位置を指すとは限らない。
未固定の新marked選択は既存freeze機能で固定し、返すProjectに全split_patternを保存する。
既に固定した選択を指定した場合も検査する。旧接続に拘束されたsplit_patternを新接続へ渡せば拒否する。
これは新しい選択の明示宣言であり、旧選択の自動移送ではない。

## 幾何と番号の確認

元のnative空間を全履歴まで構築し、先の初期空間・一様水準・新履歴の各prefixを検査する。
既存の二次境界比較により、同じプリミティブ分率の共通区間でBezier係数を比較する。
係数差の凸包による全辺位置の判定を、元の幾何尺度に応じた丸め許容差で行う。
端点だけの一致、同じ解析曲線名、同じ弦誤差予算では代用しない。

独立なGreen積分の面積・回転体積と、`u=1`すなわち`Hφ=r`に対する
質量`∫r³ dr dz = |∮r⁴ dz|/4`を検査した。境界の周回方向の符号は物理体積の符号ではない。
初期接続が変わるため、固有値の完全一致やRitz単調性は一般には要求しない。
小さい代数残差や同じ境界を、物理離散化誤差の保証に読み替えない。

最小頂点接線角は有限かつ0より大きく60未満。全新段階へ適用する。
新steps自身の品質条件、正Jacobian、全二次辺、boundary/axis、元の要素予算も維持する。
巨大な一様段数は段階を逐次検査し、巨大な配列を先に生成せず要素予算で拒否する。

元/先が同じ二次領域であれば、既存`curved_same_domain`で独立な保存場を比較できる。
後の[調和変位](CURVED_HARMONIC_DEFORMATION.md)にも新固定履歴を渡せる。
非アフィンな形状比較では、元の比較用Projectから変形した対応空間と、
置換メッシュから計算した独立FEMを[曲線比較メッシュ](CURVED_PIECEWISE_REMESH_TRACKING.md)で照合する。
この対応の合格は、一般連続枝や自動の物理対応を意味しない。

## CLI

```sh
OPENBLAS_NUM_THREADS=1 .venv/bin/python -m superfish_ng remesh-curved-project \
  examples/curved_project_remesh/source-project.json \
  --plan examples/curved_project_remesh/remesh-plan.json \
  --out out/new-remeshed-project.json
```

全検査の後で出力を排他的に作成する。元Project・plan・既存出力を保持する。
終了0/REMESHEDはProject作成の完了であり、固有値求解やRF精度の合格ではない。
自動の再メッシュ生成器・新GUI・Studyメッシュ切替は追加していない。

## 検証記録

着手HEAD`f6ee460`、初期作業ツリーclean。
証拠は`out/curved-project-remesh-20260914/`、最終索引は`acceptance.json`。
初回の幾何/質量2テストは新API不在でred。
最初の実装後の2件は1合格/1エラー、後者は検証器がkeyword-onlyの積分次数を位置引数で渡した誤りだった。
テストの呼出しを修正し、新6件は7.994秒PASS。
後続の非アフィン変形受渡し1件も2.975秒PASS。
専用FEM確認後、独立な内部点移動と節点/要素番号の付け直しを含む1件も追加確認した。
最終新8件は6+1+1の分割証拠である。

既存の`test_curved_harmonic_deformation`、`test_frozen_curved_refinement`、
`test_project_mesh`、`test_curved_same_domain_tracking`、`test_curved_piecewise_remesh_tracking`の
34件は75.672秒PASS。直接の旧メッシュ置換とStudyを含む`test_external_mesh_study`も4件0.478秒PASS。
旧APIがmarked履歴付きの無宣言置換を拒否することは維持した。

専用`validate_curved_project_remesh.py`は53.996秒PASS、8新FEM。
元26→履歴146要素、置換28→新履歴188要素を、それぞれ尺度1/2と非アフィン変形後に計算した。
元/置換の同一領域追跡は重なり0.9999999408013291、元/変形後の独立置換FEMは0.9977230877971308でPASS。
後者の比較用メッシュは元Projectから変形したものを使用し、FEMの初期接続との一致を仮定しない。
両保存追跡の完全replayとnative読込も一致した。
独立Green面積/体積、Maxwell f/RFの相対差最大4.441e-15、Hφ/Er/Ez場形の尺度差2.919e-14を確認した。

別の円筒では、同じ四線分の曲線宣言から最大辺長.015m/.012mで初期メッシュを独立生成し、
置換後に指定した一様段数を適用した。初期96/384→最終384/1536要素の2 FEM。
TM010の解析f相対差は元2.103e-8/置換1.320e-9、両R/Qは8.555e-6/6.233e-7、
Gは2.330e-8/1.566e-9、TTFは3.303e-9/2.006e-10だった。
周波数とRFの条件を別に検査し、解析値をFEM求解へ使っていない。
この円筒の一致やMaxwell則を、任意形状の誤差上界や適応効率へ拡張しない。

専用実行中1,028ソース系ファイルは不変。以後の差分は独立番号付替え1テストの追加だけで、製品は不変。
今回の変更は新しいProject作成API/CLIと直接消費先に限定する。
FEM・既存変形・比較数学・物理許容差を変更しない。
全件validate/seed/browser/Hosted CI/新Wine比較/実測検証は再実行していない。
新規外部資料・依存・旧資産参照なし。既存の独立幾何・境界比較・保存/追跡と合成形状を用いた。

## 残る範囲

Studyの値ごとの初期メッシュ切替と新履歴、二分点での選択、保存再開、GUIへ接続する必要がある。
境界が一致しない二次近似間の新しい対応、一般メッシュの自動生成/番号対応、
TE/反射/半領域の置換契約、N04一般精度/効率と全計画の未完了も保持する。
親33=8受入/17進行/7他未受入/1範囲外、goal ACTIVEを維持する。
