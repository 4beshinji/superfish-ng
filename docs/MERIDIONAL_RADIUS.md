# PEC壁の最小子午面曲率半径

2026-09-08。v3 curved_contourのgeometryに任意の `minimum_meridional_radius_m` を指定できる。
有限の正数、SI単位mを要求し、0・負数・bool・null・非有限値は拒否する。
未指定なら制約を課さず、従来の正規化JSONへ追加キーも出さない。

この制約は元解析プリミティブの**子午面曲率**を対象とする。周方向の主曲率半径、
最小隙間、FEM近似境界の曲率、表面電磁場の精度を保証するものではない。
axisと電気/磁気対称境界は曲率検査の対象外。PEC-PEC接続は既存位置許容差と
1e-8 radのG1数値検査を要求し、直線であってもPEC角を通過させない。
接続の数学的な厳密G1保証とは区別する。対称面での鏡映後も全PEC接続を再検査する。

## 区間による検査

`meridional_radius.certify_minimum_meridional_radius` は有限fraction区間全体の
絶対曲率を既存normal_offset_boundsの距離0で囲む。二進回転係数のc²+s²を保持する。
直線は曲率0。要求Rに対し各区間の曲率上界が1/R以下なら、その区間を受理する。
上界だけでは判定できない場合は区間端/中点での曲率下界を調べ、1/Rを超えれば
違反点の有理数証拠付きFAILとする。残る領域を二分し、予算不足や囲い込み未達は
UNVERIFIEDとして残す。PASSは有限区間の全被覆を要求する。
境界値へ許容差を足して合格にはしない。半径1の円に1 ULP大きい要求を与えると拒否する。

APIではmax_boxes=4096、fraction_width=2^-24、endpoint_width=2^-100、max_series_terms=96が既定。
Case検査にはこの固定予算を使い、FAILとUNVERIFIEDはいずれもプリミティブ番号付きで拒否する。
Caseの予算は現在JSONで調整できない。未知の区間は、独立APIへ明示予算を渡して調べられる。
`CurvedContour.radius_constraint_report()` は現在の制約に対する証拠を再計算する。
元のminimum_radius_m数値プロパティの推定値を認証根拠には使わない。

## 保存・構築・GUI

制約はCurvedContour、Case JSON、構築保存、計算結果、鏡映へ引き継ぐ。
構築要求のテンプレートに指定すると、候補選択後の完成Caseで全PEC壁を検査する。
未完成の候補表示は半径制約を含むCaseの受入ではない。
GUIは曲線形状JSONの読み込み・保持・構築適用に対応し、専用の半径入力欄はまだない。

```bash
superfish-ng construct-tangent examples/construction/radius_constrained_fillet_request.json --candidate-index 0 --out out/radius-construction-new.json
superfish-ng export-constructed-case out/radius-construction-new.json --out out/radius-case-new.json
superfish-ng solve out/radius-case-new.json --out out/radius-solve-new
```

例は半径20 mmの直線・弧フィレットを含む合成形状に19 mm以上を要求する。
21 mmへの変更はフィレットの曲率違反として拒否する。半径を自動変更しない。
制約の追加自体はメッシュやFEMを変更せず、同一幾何の周波数・RF量は同一である。

追加6テストは円/直線・1 ULP差、楕円/双曲線の既知極値・有限弧・尺度/向き、
予算不足保持、PEC角拒否/厳密入力/旧JSON維持、構築/GUI/実FEM同一性と保存再読込、
両対称タグでの鏡映後再検査。標準回帰・実ブラウザー証拠は[引継ぎ](CODEX_HANDOFF.md)。
一般の弧端/重解、旧曲線入力、物理ピーク収束を完了する機能ではない。
既存曲率区間核から独立実装し、新規外部資料・依存は追加していない。
