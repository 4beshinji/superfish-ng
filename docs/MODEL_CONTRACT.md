# C01: 物理・材料・領域と入力版の共通契約

2026-09-07仕様。C00の確認済みTM部分集合から開始する。追加物理の数式と受入は
P01〜P04/S01〜S05の各仕様で確定する。本契約の追加で未実装ソルバーを受理しない。

## v3の明示モデル

既存caseのgeometry/mesh/solver/rf/boundariesを保持し、`schema_version:3`では
次の`model`を必須とする。v1/v2ではmodelを禁止し、従来の暗黙の真空TM契約を保つ。

```json
{
  "physics": "rf_eigenmode",
  "coordinates": "axisymmetric",
  "polarization": "tm",
  "azimuthal_index": 0,
  "materials": [{"id": "vacuum", "type": "vacuum"}],
  "regions": [{"id": "cavity", "material": "vacuum", "domain": "interior"}]
}
```

全キー必須、未知キー・重複JSONキーは拒否する。材料と領域はそれぞれ1件だけ。
idは空でない文字列で、region.materialは材料idへ一致しなければならない。
domain=interiorはcaseの輪郭が囲む計算領域全体。複数領域、内導体、穴、
領域ごとの別輪郭はG01/G02/P03/P04の受入後に追加する。
vacuumはε0/μ0を持つ材料種別。相対誘電率等の上書きを受け入れない。
壁の導電率は体積材料の導電率ではなく、従来rfの摂動壁損失パラメータ。

`azimuthal_index`はboolや実数を許さない整数0。
未対応physics/coordinates/polarization/materialは対応可能な値を示して拒否し、
TM組立にフォールバックしない。PythonのModelも不変値として同じ検査を行う。

## 場・単位・境界・将来物理

| 系 | 場と積分契約 | 本改修での受理 |
|---|---|---|
| 軸対称m=0 TM RF | Hphi=r u、Er/EzはPHYSICS.mdの復元式。SI、ピークphasor、2πr体積重み、U[J]、P[W]、RQ二定義 | vacuum、単一interiorのみ |
| 軸対称TE RF | Ephiを独立未知数とし軸/PEC条件を別設計。軸加速量はN/A | 拒否、P01 |
| 平面RF | 偏波別未知数、体積重みは回転体にしない。U[J/m]、P[W/m]を別のキーで出力 | 拒否、P02 |
| 同軸・多重連結RF | 零固有値と共振の区別、軸がない領域の軸積分はN/A | 拒否、P03 |
| RF材料 | 領域別epsilon/mu、界面条件、領域エネルギーと損失モデルを明示 | 拒否、P04 |
| 静電場 | 電位[V]、E[V/m]、電荷と容量。平面の容量[F/m]と回転体の容量[F]を別出力 | 拒否、S01 |
| 静磁場 | 磁気ポテンシャル、B[T]/H[A/m]、源電流の単位、gauge・外部境界を別仕様化 | 拒否、S02〜S05 |

表の未受理の出力量は将来仕様の制約で、現出力schemaの追加キーではない。
m>0、放射/開放、複素/分散材料、熱は受理しない。
現boundariesはz_min/z_maxのPEC/電気対称/磁気対称を継続し、壁PECと軸正則条件を維持。
物理ごとの境界を共通の整数へ潰さず、今後の材料・形状拡張で明示的にschemaを拡張する。
新しいmodel種別の能力表・入力検査・ソルバー・保存/再読込は同じ受入で更新する。

## 移行と保存

`Case`は任意の明示Modelを持つ。modelがなければ従来通り必要最小のv1/v2を出力する。
modelがあれば常にv3を出力し、材料/領域idを保存する。通常の読込で勝手に移行しない。
`upgrade_case`とCLI `migrate-case INPUT --out NEW.json`は入力を厳密に検査して
明示Model付きv3へ移行する。v3への再移行は同じcanonicalデータを返す。
旧入力のcanonical hashは変わらず、明示移行した入力のhashはschema/model分だけ変わる。
旧入力ファイルや計算出力を上書きしない。v3をv1/v2へ暗黙に戻す操作は用意しない。

保存resultの外側schemaは1を継続する。内側caseは独立した版付きデータで、
場NPZ・CSV・VTKの構造と数値の意味は変更しない。caseの版を旧読取機が拒否するため、
追加物理を旧TM場と誤解することはない。実際に場表現を変えるN02/追加物理では結果版も別途設計する。
Project/Study/鏡映はmodelを保持する。GUIでは読み込んだmodelを保持し、表示済みのTM編集項目へ対応する。
GUIで追加物理を編集する機能は各O02の受入対象。

## 受入基準

1. 固定v1/v2 canonical hash、読込/出力往復を維持し、v3移行を再実行しても同じになる。
2. 全例題で移行前後のgeometry/境界/メッシュ/ソルバー設定が一致する。
3. 同一メッシュのv1/v2とv3で固有値・u・RF量が一致する。円筒Bessel解への既存独立検査も維持。
   schema変更だけによる周波数・場・エネルギー・RQ・Gの差を認めない。
4. 未対応物理、材料係数、誤った材料参照、複数領域、欠落/重複/未知キーを拒否する。
   不正入力をCLIへ渡したとき計算結果ディレクトリを生成しない。
5. v3でCLI計算・保存再読込、Project組立/Study/鏡映、外部meshを通し、modelを失わない。
6. `capabilities`は現在受理する組合せと場・積分単位を出力する。計画上の物理をavailableにしない。

仕様追加は独立設計。新しい外部文献・コード・依存は使用しない。
実行結果は本書末尾へ追記する。C00全体の調査完了とは独立したC01の受入である。
