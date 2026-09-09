# 平面モード追跡の保存履歴

以下の範囲で限定受入。矩形の宣言写像（追跡版1）、明示多角形の原点一様尺度（追跡版2）、[宣言相似写像（追跡版3）](PLANAR_SIMILARITY_TRACKING.md)を、所有する保存場の連続性で結ぶ。各段階の数値的対応を全再生し、履歴のPASSを連続した物理経路の同一性や誤差上界とはしない。

## 接続する条件

前段階のcurrentと次段階のpreviousのnative全5ファイルが同一であること、対象帯域数が一致すること、順位付き個別IDまたは部分空間のID集合が連続することを要求する。同じ周波数・Case・ID名だけでは足りない。同じCaseから再計算した場も暗黙に置き換えない。

縮退で個別IDが未確定になった場合、その後に固有値が分離しても集合を保持する。最後がUNVERIFIEDなら、その段階を証拠として保存するが、追加を拒否し、現在のID集合を確定情報として公開しない。段階上限に達した場合も追加を拒否するが、対応のPASSと確定したID集合は保持する。`can_extend`は数値対応と段階予算の両方を満たす場合だけtrueとし、停止理由で両者を区別する。各二点追跡の写像・閾値・帯域guard・電場積分・有限細分空間の検査をそのまま使う。

## CLI

要求は厳密な版1のJSON。例えば次の2段階を指定する。

```json
{
  "format": "superfish_ng_planar_tracking_history_request",
  "history_version": 1,
  "step_count": 2,
  "max_steps": 100
}
```

```sh
python -m superfish_ng execute-planar-history history-request.json \
  --steps out/pair-1 out/pair-2 --out out/history-1
python -m superfish_ng extend-planar-history out/history-1 out/pair-3 \
  --out out/history-2
python -m superfish_ng replay-planar-history out/history-2
```

出力先は毎回新規にする。上限に達した要求や不連続な連鎖は拒否する。開始時に各段階のnativeと全二点文書をコピーし、元の外部パスが消えても所有コピーだけで再検証できる。

`history.json`、`sources.json`、各`step-NNNN/`の全二点保存、`history-results.json`、`manifest.json`、`job.json`を結合する。結果のhashを貼り直しても、完全な祖先再生と異なる要約は拒否する。専用job kindは`planar_tracking_history`。

## ローカルジョブとGUI

`JobManager.start_planar_history(paths, request)`と`extend_planar_history(history, next_pair)`は実workerを起動する。投入準備で全祖先を検証して所有コピーを確定し、以後workerはその全コピーと実装が完了まで変化しないことを検証する。元履歴の準備中変更は起動前に拒否する。同期CLI追加では完了後にも元履歴の変化を検査する。途中失敗した出力はfailedとなる。中止・再起動・重複worker拒否は通常の管理操作へ接続する。

平面GUIの「モード追跡の履歴」で、順序付き追跡結果IDと最大段階数を指定する。履歴条件の保存文書は段階数と上限を保持し、読込時はこのワークスペースの追跡IDを明示する。結果には各段階の状態・写像・個別IDの確定状態、現在のID集合、停止理由を表示する。追加は別の履歴を作り、旧履歴を変更しない。

最後の保存場は独立した平面結果として取り込み、描画・SIプローブで調べられる。「次の追跡へID集合を引き継ぐ」は最後の場と帯域・ID集合を設定する。次の場と写像は利用者が指定する。履歴は平面の単独スペクトルや軸対称追跡の候補にはしない。

## 検証と制限

実装前に、各々PASSかつ同じID名のcrossing→mergeが保存場不連続である反例と、merge→splitの正しい集合連続性を確認した。関連unitは、偽連鎖・帯域差・ID捏造・改変要約・コピー中変更・追加時の祖先欠損・実worker・中止・管理再起動・元ファイル削除後の再生を検査する。CLIとGUI経由の結果も完全再生へ照合する。

開発段階の独立16条件（三角形/凹形状、TE/TM、P1/P2、尺度0.37/2）の往復2段階と、管理再起動後の全再生は782.726秒で合格し、531sourceの不変を確認した。これは最終GUI/CLI統合の受入証拠とは区別する。修正後の最終検証は下記に記録する。

全コピー・全再検証の費用は段階数と場データ量に増加する。任意多角形変形・連続経路の追跡証明・真の物理誤差上界は対象外。親P02と開発計画全体は未完了。

## 最終受入の証拠

標準は`out/validation-planar-history-budget-fixed-final-20260910`。923件中921合格・2skip、unittest 1417.539秒。関連15unitは93.659秒で合格。`verify_completion.py`で全証拠と532sourceの完全一致、保存hash、TM seed9モード19量を再照合した。周波数差0.000e+00、RF相対差最大8.882e-16。数値許容差は緩めていない。

| 検証 | 結果 |
|---|---|
| 三角形/凹形状・TE/TM・P1/P2・尺度0.37/2の往復、矩形交差→縮退→分離と未解決停止 | 18実履歴workerと管理再起動後の全再生が合格、694.250秒 |
| GUIで実計算した矩形3形状の解析周波数・電場部分空間 | 周波数誤差最大1.599e-5、電場誤差最大0.005666。0.1%/1%基準に合格 |
| Chrome | 履歴17・旧機能52・再起動7の計76操作。外部HTTPなし、製品source不変 |
| GUI保存 | 47完了ジョブ（履歴4、二点追跡8、Study5、細分3、平面単独24、軸対称3）を全再検証、49.214秒。再起動後の取込1も末尾nativeと同一、7.283秒 |
| 旧機能 | 保存追跡22/44native＋取込10、矩形追跡11＋取込6、Study29/61点、細分18/54水準、平面native32、TE10の再生が合格、253.656秒 |

段階上限時に追加可能フラグだけがtrueとなる開発中の不一致を修正し、修正前の未完標準と反例を保持した。予算停止はPASSとID集合を保持し、未解決停止と区別する。詳しい失敗・再検証経過は[計画記録](PLANAR_TRACKING_HISTORY_PLAN.md)。ローカル検証であり、hosted CIの実行は主張しない。

次は[回転・平行移動を含む宣言相似写像](PLANAR_SIMILARITY_TRACKING_PLAN.md)。隔離候補の検証を、製品の対応範囲とは数えない。
