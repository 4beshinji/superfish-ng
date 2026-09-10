# 同じ多角形の独立メッシュ間の電場追跡

同じ単純PEC多角形を別の適合三角形メッシュで解いた平面TE/TMの保存場を比較する。Cartesian遮断問題β=0、真空、直線P1/P2が対象。節点数・番号・要素数・対角線・内部節点位置が異なっていても、元領域が同じなら比較できる。両側の要素次数が異なるP1/P2の比較にも対応する。要求/結果版4、CLI・ローカルworker・GUI・所有履歴に接続し、以下の限定受入条件を確認した。

## 入力の意味

`PolygonRemeshMapping(max_candidate_tests=2000000)`を要求へ渡す。JSONでは`mapping.name`が`polygon_same_domain`、要求の`tracking_version`が4、結果の`result_version`が4となる。写像には名前と候補探索上限の両項目を保存する。未知項目、非整数/非正の上限を拒否する。

同じ領域かどうかはbinary64で表現された外周座標を厳密に照合する。外周の開始頂点と、厳密に同一直線上にある途中頂点は正規化する。各メッシュ自体は従来の適合性・向き・連結・外周被覆・面積検査を通す。宣言した外周頂点がそのメッシュにない入力は従来どおり拒否する。

領域の違いを頂点へのfitや絶対許容差で吸収しない。大きな原点にある小さな領域でも同じ条件を使う。回転・移動・尺度変更には別の[相似写像版3](PLANAR_SIMILARITY_TRACKING.md)を使う。版4と形状変更を合成する操作、曲線、穴、材料、伝搬は対象外。

## 元要素からの積分

二つの元三角形の交差を有理数で切り取り、面積を持つ部分だけを三角形に分ける。辺や点だけの接触は面積に数えない。両側のすべての元要素で、交差部分の面積の和が元の面積と厳密に一致することを確認する。全体の面積一致だけでは合格にしない。

元要素のbarycentric座標を使って、保存したFEM係数から電場を評価する。新しい節点への再補間、勾配の節点平均、場の修正を行わない。TE横電場とTMのEzを同じ物理xy座標枠で積分し、U′の異なる規格化はGram行列の正規化で扱う。積分の物理測度は元領域の面積[m²]。

候補選別はAABBの階層木を使う。木の節点比較と葉内の個別候補比較を、比較前に`max_candidate_tests`へ計上する。上限超過では失敗し、途中までの対応を合格として返さない。木の構築は入力要素数で制限される。入力要素数と生成する交差三角形数は要求の`controls.max_overlay_triangles`（既定250000）以内とする。診断の細分には別の`max_refined_triangles`を使う。

## 実行

```python
import json
from pathlib import Path
from superfish_ng.planar_tracking import PlanarTrackingRequest
from superfish_ng.planar_tracking_remesh import PolygonRemeshMapping

request = PlanarTrackingRequest(
    1, 1, ["fundamental"], mapping=PolygonRemeshMapping(),
)
Path("tracking.json").write_text(json.dumps(request.to_dict(), indent=2) + "\n")
```

```sh
python -m superfish_ng execute-planar-tracking previous-native current-native tracking.json --out new-tracking
python -m superfish_ng replay-planar-tracking new-tracking
```

GUIでは「同じ多角形：異なるメッシュ」を選び、二つの保存場と追跡帯域・IDを指定する。尺度・回転・細分関係の入力はこの方式では使わない。要求の読込/保存、結果ダウンロード、元の場の取込/表示、保存ジョブからの復元を同じ版4へ接続している。

上端を検査する追加の正モードが必要であり、求めた全スペクトルをguardなしの追跡帯域へ指定できない。面積由来のシフトを使う有限細分空間診断、3/5次積分、PSD、部分空間と上端guardを再計算する。縮退はID集合として運び、曖昧な対応や不足帯域は`UNVERIFIED`。数値的な二状態の対応を、連続経路の同一性や物理誤差上界とはしない。

## 保存と互換性

両側の元native、要求、結果を所有コピーとして保存する。保存再生では元FEM場と幾何・対応判定を全再計算し、入力や結果の改変を拒否する。旧版1〜3の要求/結果と再生の意味は保持する。

[所有履歴](PLANAR_TRACKING_HISTORY.md)では隣接するnative全ファイルの同一性と帯域・ID集合の連続性を引き続き要求する。同じ領域で解き直した場も、前段の保存場へ黙って置き換えない。各段階を完全に再生するため、履歴が長い場合の計算費用は増える。

受入条件・失敗記録と現在の検証状態は[計画書](PLANAR_REMESH_TRACKING_PLAN.md)に記録する。新しい外部ソース・依存ライブラリーは使用していない。

## 受入証拠（2026-09-10）

同じ多角形の独立メッシュ間の元電場追跡を限定受入。要求/結果版4、厳密な領域・各元要素面積・候補予算、全保存再生・CLI/実worker/GUI・所有履歴を接続した。標準939件（937合格、2skip、1486.136秒）、追加7unit、独立32 FEM/32対応、混次数16比較、幾何24条件、解析16条件、縮退16 FEM、実追跡32/履歴16worker、中止/再起動、Chrome96操作とGUI63保存ジョブを確認。旧版1〜3・38履歴・TM/TE/平面回帰と538sourceも合格。形状変更との合成は[相似変換＋独立内部メッシュの合成追跡](PLANAR_SIMILARITY_REMESH_TRACKING.md)（要求/結果版5）と[可逆アフィン＋独立内部メッシュの合成追跡](PLANAR_AFFINE_REMESH_TRACKING.md)（要求/結果版6）として限定受入済み。境界密度を独立に選ぶ一般合成・非線形変形・曲線・親P02と全計画は未完。

- 標準・538source・TM seed9モード19量: `out/validation-planar-remesh-fixed-final-20260910`
- 独立32 FEM/32対応と両尺度のf/G/Q/損失: `out/planar-remesh-fixed-independent-20260910`
- 24幾何条件・モーメント・候補: `out/planar-remesh-geometry-independent-20260910`
- 三角形解析16条件: `out/planar-remesh-analytic-20260910`
- 混次数16比較: `out/planar-remesh-mixed-order-20260910`
- 縮退16 FEM・基底回転/guard: `out/planar-remesh-subspaces-20260910`
- 候補選別の費用4条件: `out/planar-remesh-candidate-cost-20260910`
- 実追跡32/履歴16worker・中止2件/再起動/CLI/改変拒否: `out/planar-remesh-workflow-20260910`
- CLIの履歴作成/追加/全再生: `out/planar-remesh-cli-history-20260910`
- 新native32件の全再生とhash: `out/planar-remesh-native-replay-20260910`
- 新Chrome8項目: `out/browser-planar-remesh-fixed-20260910`
- 旧Chrome78項目: `out/planar-remesh-browser-regression-20260910`
- 再起動Chrome10項目: `out/browser-planar-remesh-restarted-20260910`
- GUI63保存ジョブの全再生・取込とダウンロード照合: `out/planar-remesh-gui-persistence-20260910`
- 旧版3の32追跡/16履歴と旧版1/2の22履歴全再生: `out/planar-remesh-old-similarity-replay-20260910`
- 旧native/矩形/Study/細分/保存の回帰: `out/planar-remesh-fixed-regressions-20260910`

細かいP2の三角形解析比較は周波数相対誤差最大2.676e-5、電場相対誤差最大0.001434。粗いメッシュの精度未達も保持する。既存TM seedの周波数差は0、RF相対差最大8.882e-16。ベンチマークと許容差は変更していない。ローカルの検証実績であり、hosted CIの実行実績ではない。

標準終了時には既存の一時workspaceの`.manager.lock`について`ResourceWarning`が再度出た。テスト失敗はなく、前段からの未解決の資源解放警告として保持する。今回の追跡機能で修正したとは扱わない。
