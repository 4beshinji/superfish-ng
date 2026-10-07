# N03：元系列の終端と曲線親子比較の明示資源

2026-10-07。N03はIN_PROGRESS。原N01五形状・全45点の計算と、
モード追跡の資源制限を分けて記録する。全滑らか形状の連続二変化、
独立参照の両側細分、周波数・場・RF・物理ピークの受入は後続である。
原123カードと互換32要件、親G03/N03、全goalの範囲は維持する。

## 受入条件と変更

元の次数10による両側全求積点、全guard個別ID、Hφ/Er/Ezの単一符号・
絶対振幅、元閾値を保持し、宣言した資源で隣接一様P2細分を比較する。
既定経路・旧要求版1/2の意味は維持し、非対応の履歴や幾何は拒否する。
FEM求解・場係数・周波数・RF定義・規格化・物理閾値は変更しない。

[uniform_curved_sampling.py](../src/superfish_ng/uniform_curved_sampling.py) は
完全な元Case/source mesh、一様細分水準差1、四子要素の順序と各六節点を検査する。
各二次子写像を親の参照4分割へ照合し、既存細分と同じ
`512 * epsilon * geometry_scale` の丸め一致を要求する。
全求積点を親子の参照座標へ写し、両方の**元係数**でHφを評価する。
係数の補間・再規格化・振幅 fitting、境界の再投影、求積点の削除は行わない。
重みは従来の両側物理 `r dr dz` の半和である。六節点一致は二次幾何の検査であり、
Maxwell場や物理誤差の上界ではない。局所履歴、非隣接水準、異なる元メッシュ、
TE、鏡映・アフィン比較にはこの経路を使用しない。

[geometry_surface_matrix.py](../src/superfish_ng/geometry_surface_matrix.py) の版3要求は
版1の完全計画・全九点に次の必須項目を追加する。

```json
"native_tracking_resources": {
  "sample_budget": 8388608,
  "sampling": "uniform_parent_p2"
}
```

予算は整数1〜8388608、方針は上記だけを受け付ける。閾値の上書きや未知キーは拒否する。
この資源は固定幾何のnative追跡だけに適用し、幾何間比較・求積・ピーク・RF条件は従来通り。
予算不足はUNVERIFIED、個別IDはnullを保持する。資源を要求と報告の双方に保存し、
再読込では元結果から完全再生する。既定上限262144と物理逆写像の経路は変えない。

## 終端した元系列

raw：`out/n03-native-surface-series-20261007/`。
`initial-series.json` は45/45 native完了、2995.296秒、終了0。
元1197 Python源とSHA固定catalogは開始・終端で不変。
四つの滑らか形状は追跡予算でUNVERIFIED、鋭角はSINGULAR_GEOMETRYかつ
numerical_status=UNVERIFIED。未確認を精度合格へ変更しない。
元Case・三モード・source mesh・各費用・全失敗/未確認報告を保持する。

公開MIT cavsim2dのA01固定commit
`48741ff46ca44463281a5ab5945328615881b502` の79源を既存SHAへ照合して復元した。
独立uv環境でNGSolve 6.2.2606、幾何だけの公開Profile adapterを使用する。
NGメッシュ・係数・行列・周波数は参照求解へ渡さない。全AXI/PECと独立面積/体積を検査。
五形状×h三水準の15求解は8.188秒、追加h=0.0025/0.00125 mの10求解は
552.118秒で終端。全5個の実計算モードを保持する。TE混在順位をTMラベルにしない。
参照源は不変、製品依存の追加なし、legacy源/実行/バイナリ取得なし。

元球参照の全解析体積Gauss16/24比較は、h=0.02/0.01 mでG等がFAIL、
h=0.005 mで解析五量・元E/HがPASS。粗いFAILを保持し、後続の両側精度受入と区別する。
環境のdistutils欠落は隔離環境へのuv管理setuptools追加で修復。
検査側peak APIキー誤りとNumPy boolのJSON拒否は元logを保持し、
保存場の検査だけを修正した。参照固有値の重複求解はしない。

## 拡張の限定検証

`tracking-extension-acceptance.json` に全source SHA・13個別unit ID・元logを結合した。
新5親子検査＋版3要求/保存CLI2＋直接同一領域/TE4＋アフィン/TE対称2を分割受入。
独立多項式 `Hφ=r(2+3r−4z)` と両側体積、実振幅2%差、順位交換、
異なるsource/子多項式拒否、既定逆写像との一致、元閾値・予算停止、完全再生を確認する。
初回module未実装、検査側out symlink拒否、空要求の資源echo不足を保全し、必要な失敗分だけ修復。
製品/検査/スクリプト1199源のうち既存1197源中1193はbyte不変。
旧moduleの変更関数以外はAST同一、FEM/RF科学核・元ゲートは不変。
検証したtemp源と主ツリーへ統合した源はbyte一致し、統合だけの重複unitは行わない。
新seed/fullは実施しない。この変更は固有値/RF核やseed solveに影響しない。

保存された球のgeometry2・FEM1→2は312000点で、元経路は予算停止。
明示資源経路は全点・全三ID・元場条件PASS、3.479秒、最大RSS148808 KiB、
新FEM0。これは一比較の対応成立であり、N03全行列や独立物理精度の受入ではない。
別の読取prototypeは元逆写像128点とのE/H差最大5.032e-15を確認した。
両手法の計測標本数は異なるため、一般的な速度倍率を主張しない。

次は版3で保存45点を再利用して全五行列を評価し、参照最細三水準の実H対応と
連続二変化、NGとの同規約場/RF/ピーク比較を行う。物理誤差上界はnullを維持する。

## 版3全行列と独立球の後続証拠

コミット63a9eafの1199源を固定して保存45 nativeを再利用した。
`explicit-resource-matrices/report.json` は1025.114秒、終了0、新FEM0、源不変。
元五Caseと0/1/2の全水準、次数10、全個別ID、五量閾値は変えていない。

| 元Case | 全行列 | numerical_status |
|---|---|---|
| 球 | PASS | PASS |
| 楕円 | PASS | PASS |
| 長楕円体 | FAIL | FAIL |
| 接線連続丸め二ローブ | PASS | PASS |
| 鋭い二ローブ | SINGULAR_GEOMETRY | PASS |

長楕円体の最初のR/Q変化は幾何三水準で4.959/10.931/7.301%、
次は0.536/1.552/0.987%で、元0.5%条件を超える。fが安定していても受入しない。
同じ元source meshと各P2幾何に一様FEM3/4の六点を明示的に追加する。
元45点・全初回FAILは保存し、追加後の実ID/場/求積/RF/ピーク判定は別に行う。
固有値の順位を個別モードのIDと見なさない。

独立比較rawは `compare-saved-independent-series.py` と各排他batch。
初回の「解析領域の全点を粗いP2領域へ直接評価」は領域外点で失敗した。
次の全P2 radial fanは幾何partitionで分割しないGauss積分の体積条件で停止し、
その後の参照root指定も検査側FileNotFoundErrorで停止した。各版・log・失敗jsonを保持する。
これらを製品固有値/場の不具合やN03精度合格と呼ばない。

修正した比較は、元曲線parameterと半径分率で**両方の全領域**を対応させる。
元各幾何のP2壁partitionの和集合でGauss16/24を分割し、全曲線被覆と
z単調性・正の体積密度を検査する。NGは元P2壁へのradial fan、参照は解析壁のfan。
固定円筒E/H成分に体積密度比の平方根を掛ける単位的L2規約を明示する。
これは[既存の非一様比較規約](HPHI_MAPPED_TRACKING.md)と同じ数学であり、
Maxwell場のpush-forward、係数や振幅のfittingではない。軸Ezは同じ物理座標で比較する。
native locatorの同じ30 iteration/1024 boxで各点の住所を一度求め、
元fields_in_cellを全モードへ評価する。各入力の16点で既存samplerとの一致も検査する。
全点・体積密度・場・各求積結果・元源/native/reference byteを保持し、欠測を除外しない。
この有限Gauss診断を連続場の誤差上界とは扱わない。

`batch-v4-N01-sphere-control/report.json` は44.191秒、終了0、新固有値求解0、
全元源/参照/入力byte不変。全5参照モードから実TE電気エネルギー比1e-8未満の
TM候補を選び、Hφと全候補の競合marginから三個別IDを追跡する。
参照h=0.005/0.0025/0.00125 mの連続二場/五量変化と、最終NG–参照の場/軸/五量はPASS。
Gauss16/24の全体積点8192/18432で、元P2体積との差は最大6.662e-16。
最終全体積E相対L2差は0.000418/0.000448、Hφは0.000182/0.000182、軸Ezは0.000130/0.000132。
ピークは参照solver推定値との経験的照合であり、連続Maxwellの厳密なピーク保証ではない。
追加球二水準の解析照合も別の `reference-sphere-analytical-finer.json` にPASSを保持する。

楕円/長楕円体/丸め形状と鋭角の独立比較、長楕円体の追加水準は続行中。
N03をDONEへ変更しない。追加実行中も1199源を固定する。
