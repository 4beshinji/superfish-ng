# 明示曲線Hφのnative・CLI

[計画](CURVED_HPHI_NATIVE_PLAN.md)の固定候補653sourceを主ツリーへ統合し、以下の範囲で限定受入。
専用schema 1でcase.json/mesh.npz/fields.npz/results.jsonを保存し、manifest.jsonを最後に公開する。
元の二次幾何・全頂点/中点・境界成分/区間・P1/P2 DOFと元係数/周波数を保持する。
規約にはq/uの単位、静的核の除外、peak phasor、全3D U/P、全曲線壁損失、明示軸の複素Vaccと両R/Qを含む。

`save_curved_hphi_run` は元Caseと解の対応を確認し、幾何/K/M・最低正スペクトル・全RFを再構築してから新しい出力先を作る。
`read_curved_hphi_run` は5ファイルの完了とhashに加え、全配列・境界/DOF・最低正帯域・全RFと規約を再計算して照合する。
未知配列/形式、不完了、リンク、再hashした改変、読込中の変更を拒否する。既存出力を上書きしない。
元解や入力が公開検証中に変わった場合も、出力先を作る前に拒否する。

```sh
python -m superfish_ng solve-curved-hphi CASE.json --out NEW_RUN
python -m superfish_ng replay-curved-hphi NEW_RUN
python -m superfish_ng probe-curved-hphi NEW_RUN --points POINTS.json --mode 1 --out NEW_PROBE.json
```

solveとreplayは検証した全結果JSONを出力する。
POINTS.jsonはSIの `[r_m,z_m]` の行リスト。全E/H/Bのreal/quadrature成分、規約と元nativeのhashを新しいプローブJSONへ保存する。
モード番号は1から始まる正スペクトルの順位で、追跡IDではない。穴/領域外を拒否し、プローブ先をnative内部には作らない。

## 検証

追加4unitは7.502秒、関連30unitは20.729秒でPASS。
軸あり/なし・P1/P2の完全往復、元係数とプローブの保持、再hashした幾何/係数/RF/phasor改変、未知/欠落/リンク、検証中の変更、保存中断時の未完成判定を確認した。

先行する独立48 FEM/144 RFのうち、軸あり/なし・0/1/2穴・P1/P2・2尺度の24ケースを使って48回保存した。
74実CLI（72成功・2想定拒否）が77.974秒でPASS。API/CLIのnative5ファイルがbyte単位で一致し、プローブ全JSONもE/H/B・規約・元hashを含め一致した。
元240nativeと97参照ファイルは不変。全RF JSONは先行する独立物理微分/積分の結果と一致した。
証拠はout/curved-hphi-native-independent-20260912。

半径も非線形の写像 `R=r+αr², Z=z+βr²` を追加し、24ケース/48RFと12CLI・40native不変が14.345秒でPASS。
最大相対差は解析形式2.177e-14、f7.128e-14、RF7.223e-15、元場L2差1.161e-15。
全3候補の不変な基盤sourceとの対応をout/curved-hphi-radial-map-independent-20260912へ保存した。
実行helperはout/curved-hphi-native-development-20260912/operation-helpersにhash付きで保持する。

標準回帰・本体統合・主ツリー検証も終了した。
Project・Job・GUI・Study・追跡への統合は別工程。二次多項式の有限FEM照合を連続問題や表面ピークの精度保証にしない。
既存の自作保存共通処理とCLIを再利用し、新規外部資料・依存・旧版参照なし。

標準1099件（1096合格・3skip）は2262.072秒、ResourceWarningなしでPASS。
skipは任意NGSolve参照2件とsandboxの既存HTTP待受1件。新規GUI変更はない。
主4unitは7.719秒、主24ケース/48保存/74CLIは65.573秒でPASS。
候補653sourceと主659source（不変egg-info 6件）の一致を確認した。
旧seed9モード19量はf差0、最大相対差8.882e-16。ベンチマークと数値しきい値は不変。
統合証拠はout/validation-curved-hphi-native-candidate-20260912/seed_regression.json。
