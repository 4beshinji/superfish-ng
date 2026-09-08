# 表面ピークの固定幾何細分評価

N03の初期API/CLI/GUI。保存したモード追跡履歴を再検証し、同一モードの周波数・RF量・
表面ピーク比について、直近2回のメッシュ細分での変化を別々に判定する。
`TARGETS_MET` は記録した細分差が開発目標以内という意味であり、物理誤差の上界ではない。
解析曲線と二次近似境界との差は別途検証する。

## 入力と判定

- 最低3水準のnative曲線P2結果と、`curved_same_domain` による保存追跡履歴を使用する。
- 対象 `mode_id` は各段階で確認された個別IDであること。順位は履歴から取得する。
  集合内で未確定の個別枝や未確認の対応から周波数・ピーク値を選ばない。
- 元Caseと元メッシュを保持し、`curved_refinement_levels` のみを厳密に増やす。
  形状・励振規約・正規化・物性・元メッシュを変えた系列、再投影を含む系列は拒否する。
- 各保存結果の場・RF・連続離散ピークを通常の再読込検査で確認する。
  囲い込み済みのピークを持たない旧結果は、現在の契約で保存し直す必要がある。

| 量 | 各細分区間の相対変化上限 |
|---|---:|
| 周波数 | 1e-4 |
| accelerator R/Q | 0.005 |
| 幾何係数G | 0.005 |
| Epk/Eacc | 0.01 |
| Bpk/Eacc（mT/(MV/m)） | 0.01 |

直近2区間の**両方**で全量が基準を満たす必要がある。全水準と全区間の診断を保存する。
ピークは上側推定値だけで比較せず、上下界をEaccで割った区間から最大相対変化を求める。
保存した浮動小数点値を厳密有理数として比を計算し、結果を外向きに丸める。
周波数/RQ/Gは保存した離散計算値の比較であり、物理値の区間保証ではない。
Eaccが有意でない、比の範囲が表現不能、相対比較の下界が0以下の場合は `UNVERIFIED`。

元解析曲線のPEC接続を調べ、再入角があれば `SINGULAR_GEOMETRY` を返す。
これはピークを有限と認めない診断であり、特異場の漸近次数を求める機能ではない。
他の角や未分類の接続は `UNVERIFIED_GEOMETRY`。軸との接続では、PEC接線が軸に直交するかを
明示角度許容差で検査する。球・楕円体の滑らかな極と、円錐状の先端を区別する。
内部の軸分割点は物理的な角と数えない。滑らかさは許容差による診断で、厳密正則性の証明ではない。

## APIとCLI

```python
from superfish_ng.mode_tracking_history import read_mode_history
from superfish_ng.surface_convergence import save_surface_convergence, read_surface_convergence

history = read_mode_history("history.json")
report = save_surface_convergence(history, "fundamental", "surface-convergence.json")
verified = read_surface_convergence("surface-convergence.json")
```

```bash
superfish-ng assess-surface-convergence history.json --mode-id fundamental --out surface-convergence.json
superfish-ng replay-surface-convergence surface-convergence.json
```

出力は新規ファイルに限定する。再検証では履歴・全native source・評価値・基準・判断を再構築し、
改変や欠損を拒否する。CLI終了値は `TARGETS_MET` の場合0、未達・未確認・特異の場合1。
`NOT_CONVERGED` や特異診断でも記録を保存し、処理が終わったことと基準達成を分ける。

## GUIで評価する

「モード対応と追跡履歴」の「対応・履歴を開いて再検証」で3水準以上の履歴、
または追跡済みStudyの文書を開く。その下の「表面ピークの細分差を評価する」で
個別モードIDを指定し、「上の履歴から評価する」を押す。

各水準の周波数・R/Q・G、ピーク比の上下界、各細分区間の変化率・基準・判定対象を表示する。
基準達成、未収束、特異形状、形状未確認を分け、元結果と角診断も確認できる。
短い履歴では評価ボタンを無効にし、対象ID・固定幾何の条件はサーバーで再検証する。
上の追跡結果や通常Studyの収束判定を置き換えない。

「検証済みの表面評価を保存」はサーバーの元JSON文字列を保存する。
「保存した表面評価を開いて再検証」と「表示中の評価を再検証」は全native sourceと判断を
再構築する。入力変更や失敗時に前評価を上書きせず、表示は最後の検証済み評価として保持する。
再検証には元の保存結果が必要。画面上の丸めた値で判定をやり直さない。

## 独立検証と残件

`scripts/validate_surface_convergence.py` は球形の3水準について、最終FEMの周波数・R/Q・G・
Epk/Eacc・Bpk/Eaccを独立球形解と比較する。長さを2倍、蓄積エネルギーを4倍にした別系列で
fの反比例とRF/ピーク比の不変性も確認する。解析式は検証にのみ用い、FEMには渡さない。

この初期評価は固定した二次境界の一様細分に限る。解析曲線への幾何収束、一般形状の
ピーク受入、直線P1/P2の収束評価統合、局所適応細分、通常RF結果画面への評価統合は残件。
N03親課題全体の完了とはしない。既存StudyやRFの未認証表示を一括で合格に書き換えない。

最終独立検証は `out/n03-surface-convergence-final-20260908/validation.json` に保存。
球形の36/144/576要素、長さ1/2とエネルギー1/4の2系列で基準達成。
最終解析差はf 2.483e-5、RQ 6.489e-6、G 8.807e-7、Epk/Eacc 2.657e-4、Bpk/Eacc 3.847e-5以内。
基準や許容差は変更していない。これらは球形に対する独立検証値であり、一般形状へ外挿しない。

GUI接続は `out/browser-n03-surface-20260908/report.json` の実Chrome51項目で確認。
表面評価の追加11項目と既存追跡40項目が成功し、成功/特異形状の画面も画像確認した。
標準567件中565合格/2 skip、独立球形と周波数/RF回帰も最終ソースで再検証済み。
