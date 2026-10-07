# N03：元失敗系列を保った追加FEM水準と個別IDの来歴

2026-10-07。N03はIN_PROGRESS。元長楕円体の0/1/2はR/Qの二変化条件に
未達である。同じsource mesh・固定P2幾何に3/4を追加し、元失敗を消さず
2/3/4の連続二変化を別要求として評価する。原catalog・元45点・閾値は保持する。
原カードは「各滑らかな系列の連続二区間」と失敗/費用の保全を要求する。
catalogの `fixed_geometry_fem_requirement` は元meshを保ったuniform追加細分を指定する。
追加結果で初回0/1/2をPASSへ書き換えない。

## 追加nativeと実装の位置

`out/n03-native-surface-series-20261007/prolate-appended-fem-levels/report.json` に
幾何三水準×FEM3/4の六点を保存した。六点ともNATIVE_COMPLETE、460.209秒・終了0。
元source meshと各P2境界の一致、元1199源の不変を確認した。
この時点では実ID・RF・ピーク・求積・独立物理の受入は別に残る。

主ツリーの公開要求は版1/2/3/4。版4は
`/tmp/superfish-ng-n03-appended-matrix-20261007` の別作業ツリーで検証し、
独立比較の全ジョブ終端後に、受入源と全1200 Pythonファイルのbyte一致を確認して統合した。
新7＋直接3の10個別unitは分割PASS。元バージョンと科学核/RF定義・許容差は維持する。
版4を拒否するbaseline、kinematic順位交換・真の縮退/欠測、完全Case/source不一致の
sample前拒否、保存完全再生・排他/CLI、旧版3/既定逆写像を確認した。
製品FEM/seed/fullの新規検査は行わない。FEM/RF核とseed solveの経路は変更しない。
実保存九点＋ID来歴二点の評価は、同じtemp源1200を固定して1034.638秒・終了0でPASS。
新FEM0、全三ID・全場・求積・幾何不変量・五量の二区間が成立した。
幾何2の最終二R/Q変化は0.1285%/0.01598%、元0.5%条件内。
元0/1/2のFAILと六追加nativeの費用を保持する。
最終FEM4の独立照合は1017.615秒・終了0・PASS、元1199源/参照全byte不変。
[五系列の元条件監査と範囲](N03_PHYSICAL_SERIES.md)を参照。

## 要求と判定

版4は元版3の完全計画・元source/九点・宣言資源を保持し、次の二項目を必須にする。

```json
"uniform_fem_levels": [2, 3, 4],
"identity_prefix_runs": ["original-geometry0-level0", "original-geometry0-level1"]
```

三水準は0〜4内の隣接整数だけを受け付ける。prefixは元幾何0の水準0から
最初の評価水準の直前まで全点を要求する。各点は完全Case・元source mesh・
completion全byte・元固有対/規格化/RFを検証する。nullは欠測を明示しUNVERIFIED。
重複・Case/source不一致・未知キーを拒否する。元planの0/1/2は保存し、
追加要求のCaseはuniform水準だけを変更する。

元水準0の三IDから、prefixの**実Hφ**を各隣接水準で追跡して最初の評価点へ渡す。
周波数順位のIDをそのまま付け直さない。近縮退・guard未解決・欠測では個別IDをnullにする。
prefixはIDの来歴であり、初回の場/RF精度を新しい収束区間に数えない。
prefixの元場精度FAILも別報告で残す。実際の三水準の場/五量/求積/ピーク条件は従来通り。

幾何2の3→4は9248000点で、元版3上限8388608を超える。
版4だけは明示上限16777216を扱い、全求積点・次数10・元係数を保持する。
既定262144、版3の8388608、強いoverlap .98/margin .05、場/RF/ピーク閾値は不変。
比較関数も拡張上限を明示するまで8388608を維持する。これは計算資源の指定であり、
物理閾値の緩和や標本削除ではない。

## 独立比較の領域確認

元sphereの独立比較PASSに加え、丸め形状は195.393秒で場/RF/五量二変化PASS。
鋭角は244.794秒で非ピーク条件PASS、SINGULAR_GEOMETRYを保持した。
元ellipse/prolateの比較は、粗い参照h=0.005 mの極付近で解析点のmesh lookupに失敗した。
Gauss24のellipseは4点、prolateはGauss16/24で12/26点。点・重み・例外を保全した。
locator toleranceを1e-6〜1e-12に下げても同じ点が失敗することを確認し、変更は採用しない。

参照の実領域は公開 [NGSolveのelement transformation](https://docu.ngsolve.org/latest/i-tutorials/unit-1.8-meshtopology/meshtopology.html)
のpoint/Jacobianから取得する。単一楕円では中心から元境界への全polar fanを用い、
実NG/P2と参照/曲線meshの全領域を対応させる。閉壁の全区間・正のpolar Jacobianと
独立積分体積を検査する。参照meshのCurve、境界再投影、場係数/周波数の変更は行わない。
固定円筒E/Hの単位的L2比較に体積密度比の平方根を使い、Maxwell場の変形則とは区別する。
全点を保持し、物理axis Ezは同じ座標で比較する。

`conic-polar-fan-preflight.json` は二形状×参照三水準の六件PASS。
実領域の体積差は最大1.866e-14、全標本・極付近の実field lookupは欠測0、新固有値求解0。
これは幾何/lookupの確認であり、場・RF精度の受入ではない。
有限Gauss16/24の全比較を、失敗した二形状だけ再評価した。
元ellipseはPASS、元prolateは場/参照二区間/RF一致PASSでも元native行列FAILを保つ。
追加prolateのFEM4照合は別報告でPASS。元失敗の報告を上書きしない。

細かいnativeの点検索には [SciPy cKDTree](https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.cKDTree.html)
で全AABBを囲む半径による候補検索を使い、その後元AABB条件・元inverseを適用する。
eps=0、候補番号順と既存30 iteration/1024 boxを保ち、16点で全候補の総当たり一致と
既存samplerとの場一致も検査する。場や許容差の変更ではない。
実装はraw検証器のみで、製品のsampler/依存は変更しない。

追加全行列と独立二形状は終端し、元カード条件の五系列監査もPASS。
統合前の旧三源を `before-appended-main-integration/` に保存した。
統合前flightの相対manifestキーにabsolute relative_toを適用した検査側ValueErrorを保全し、
源を書き換える前にキー形式を修正した。数値再実行・許容差変更はない。
統合源は検証済みtemp commit `81bce60` と同一、新unit/FEM再実行0。
節目の全validate受入は後続。N03/親G03/原123カード/互換32要件/全goalは未完。
