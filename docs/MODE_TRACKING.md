# D01 重み付き標本と部分空間によるモード追跡

2026-09-08。D01は部分実装・部分検証。既存の周波数順mode_indexやセミナー用バンド同定は変更しない。
`mode_tracking.track_sampled_mode_subspaces` と、閉PEC円筒用の実FEM場アダプターを追加した。
個々の周波数順位と永続ID、縮退部分空間とその基底ベクトルを区別する。

## 標本の比較契約

入力は共通の標本点における実数場の列行列2組、同じ正の重み列、各列に対応する正の昇順周波数、
以前のIDである。IDは重複しない非空文字列で、周波数順位から新しく推測しない。
`comparison_description` に標本の写像・場・重みの意味を明示する。
同じ配列長だけでは物理的に同じ比較写像とは証明できず、汎用標本APIでは呼出側の責任となる。
NaN・複素数・bool配列、非正重み、不整合な形状、降順周波数、無効なIDは拒否する。

必須controlsはminimum_overlap（0より大きく1以下）、minimum_assignment_margin（0以上1以下）、
relative_cluster_gap（0以上1未満）。minimum_relative_singular_valueは既定1e-8。
相対隣接周波数差がrelative_cluster_gap以下なら同じクラスタへ連結する。
周波数はクラスタ形成に使い、異なる時点のIDの対応を周波数の近さで選ばない。

各場の列を尺度調整し、sqrt(weight)を掛けて再正規化する。SVDでクラスタの直交基底Qを作り、
標本の零列や相対特異値が小さい場合はランク不足として未確認にする。
等次元のクラスタ間でQ_previous^T Q_currentの特異値を計算し、最小値を対応スコアとする。
これは一方向だけ合う部分空間を、平均値や最大値で合格にしないためである。
符号、任意振幅、縮退基底の可逆な変更によって同じ部分空間のIDは変わらない。

全体の割当は既存SciPyのlinear_sum_assignmentを使う。採用にはminimum_overlapに加え、
同じ行・列の他候補との差を両方要求する。差の実効下限は明示値と
32*machine_epsilon*max(標本数,各モード数)の大きい方で、controlsにも記録する。
ゼロ差指定で丸め程度の同点を任意選択しない。これは数値的な曖昧判定であり区間証明ではない。
特異値の丸めによる0..1の逸脱だけを数学的範囲へ戻す。

## 結果と利用制限

全旧/新クラスタの対応が採用された場合だけstatus=PASSとなる。
未対応、重なり不足、曖昧、ランク不足、モードの欠落・追加はUNVERIFIEDとして記録する。
部分的に採用した対応も保持するが、全体の合格へ読み替えない。
現APIではクラスタの合流/分裂を別のクラスタ群へ自動変換しない。

1次元の対応はkind=MODEで、current_mode_idsに以前のIDを付ける。
多次元はkind=SUBSPACEで、以前のID集合と現在の周波数順位集合を記録し、
個々のcurrent_mode_idsはnullのままにする。individual_ids_completeで区別する。
`tracked_frequency_hz` は全体UNVERIFIED、未登録ID、部分空間内の個別IDに対して拒否する。
これにより、曖昧な順位の周波数をtuneへ渡す経路を作らない。tune自体はまだ実装していない。

2時点の類似度だけでは、その間を通る連続した物理枝を証明できない。
大きな形状ステップ、比較写像の誤差、標本数、FEM誤差を独立に検査する必要がある。
場の符号や保存係数、RF正規化は変更しない。

## 円筒の実FEM場アダプター

`track_cylindrical_modes(previous_solution,current_solution,previous_ids,...)` は
mapping='normalized_cylinder' とsample_orderを明示必須とする。
支持範囲は一定半径profile・両端PECの軸接続真空TM円筒。可変半径・折返し輪郭・対称端は拒否する。
既存のread_solutionで再読込したP1/P2の実FEM解も使用できる。

共通参照座標rho,zeta∈(0,1)をGauss-Legendre積則で作り、各空洞でr=R*rho、z=L*zetaへ写す。
物理量Hphi_A_per_mを標本化し、参照重みrho d_rho d_zetaで比較する。
各形状の体積Jacobianの定数因子2πR²Lは正規化から消える。可変Jacobianの一般形状へ
この処理をそのまま一般化しない。領域外の標本を黙って捨てず、場評価エラーとして拒否する。
結果には座標点・重み・両寸法・標本次数・場の規約を保存する。

```bash
OPENBLAS_NUM_THREADS=1 python scripts/validate_mode_tracking.py --out out/mode-tracking-new
```

この独立検証は半径0.1 m、長さ0.055/0.075 m、P2、12×12分割、3モードを実FEMで解き、保存後に再読込する。
Bessel零点からの周波数で旧順位TM010/TM020/TM011、新順位TM010/TM011/TM020を独立確認する。
追跡本体へ解析ラベルや解析周波数を候補の決定規則として渡さない。
12×12と18×18の共通標本で同じID対応を確認し、全結果とソースhashをmode_tracking.jsonへ保存する。
出力は新規ディレクトリのみ。合成円筒であり測定構造や旧版の計算結果ではない。

## 受入と残件

追加9テストは解析的な交差、近接の小ステップ、縮退基底回転、曖昧同点、欠落/ランク不足/合流、
重み・座標順・符号・極端な振幅、厳密入力、最悪主角による方向喪失、保存後の実FEM円筒交差。
標準周波数/RF回帰と独立実行の数値は[引継ぎ](CODEX_HANDOFF.md)に記録する。

一般形状の比較写像・写像精度、クラスタ合流/分裂、部分空間を含む一般的な追跡履歴と安定IDの保存/再開、
GUI・Study/tuneへの統合は未完了。2時点の保存とCLIは以下の範囲で実装した。D01親課題全体やD02を完了とは扱わない。
既存の同一形状細分比較・条件付きバンド同定は従来どおり利用できる。
重み付き内積の直交基底とSVDの基底不変性から独立実装し、新規外部資料・依存は追加していない。

## 2時点の保存・再検証とCLI

`track-modes REQUEST --out NEW.json` はnative保存場2組から対応を計算する。
request版1は次の全項目を必須とし、未知項目を拒否する。相対パスはrequestファイルの所在を基準に解決する。

```json
{
  "schema_version": 1,
  "previous_run": "mode-tracking-new/cylinder-0",
  "current_run": "mode-tracking-new/cylinder-1",
  "previous_ids": ["TM010", "TM020", "TM011"],
  "controls": {
    "mapping": "normalized_cylinder",
    "sample_order": 12,
    "minimum_overlap": 0.98,
    "minimum_assignment_margin": 0.05,
    "relative_cluster_gap": 0.000001,
    "minimum_relative_singular_value": 0.00000001
  }
}
```

上の独立検証コマンドで保存場を作り、このrequestを `out/tracking-request.json` に置く。

```bash
OPENBLAS_NUM_THREADS=1 python -m superfish_ng track-modes out/tracking-request.json --out out/tracking-new.json
OPENBLAS_NUM_THREADS=1 python -m superfish_ng replay-mode-tracking out/tracking-new.json
```

新規ファイルだけに保存し、UNVERIFIEDも理由と部分対応を保持する。
終了コードはPASSが0、UNVERIFIEDが1、入力/再検証エラーが2。
Python APIは `saved_mode_tracking.save_mode_tracking` / `read_mode_tracking`。
保存文書には絶対入力パス、requestのSHA256、元case/results/fieldsと存在するmesh・保存protocol・完了markerの
SHA256、写像/重み/閾値/対応を記録する。比較前後で入力のバイト同一性を検査する。
再検証はnative保存の整合性検査と実場からの対応再計算を行い、文書全体と照合する。固有値問題は解き直さない。
元ファイル・保存先パス・数値環境が必要であり、移動後の透過的再開や署名による真正性を保証しない。
入力の空白だけの変更でもバイト同一性は失われる。移動や変更後はrequestから新しい文書を生成する。
これは2時点の対応記録であり、多段階の連続履歴・安定ID再開やFEM収束証明ではない。

追加6テストで実FEM交差の保存/再検証、改変拒否、比較中の入力変更、入力バイト同一性、
UNVERIFIEDの往復、CLIと厳密requestを確認した。

## 順序付き履歴と個別IDの再開

`mode_tracking_history` は確認済みの2時点文書から履歴を開始し、次の保存場へ延長する。
各段階の文書を丸ごと保持し、隣接する元データのパス/hashとprevious_idsの連続性を検査する。
延長時は全過去段階を再検証し、以前のcurrent_mode_idsを次のprevious_idsへ渡す。
利用者によるID上書きは受け付けない。元履歴は変更せず、新しい出力へ保存する。
controlsは延長requestで毎回明示し、段階ごとの変更も記録する。

```bash
python -m superfish_ng start-mode-history out/tracking-new.json --out out/history-first.json
python -m superfish_ng extend-mode-history out/history-first.json out/extension.json --out out/history-second.json
python -m superfish_ng replay-mode-history out/history-second.json
```

extension.jsonは `{"current_run":"next-saved-run","controls":{...}}` の2項目のみ。
controlsは2時点requestと同じ全6項目を明記する。相対current_runはextension.json所在基準。
Python APIはstart_mode_history、extend_mode_history、save_mode_history、read_mode_history。
終了コードはPASS=0、UNVERIFIED=1、入力/再検証エラー=2。

最後の段階がPASSかつ全個別IDが確定している場合だけcan_extend=trueとなる。
未確認の段階も保存するが、その後の延長は拒否する。部分空間対応自体がPASSでも、
個別IDが未確定なら履歴はUNVERIFIEDとして停止理由を保持する。
部分空間内の基底へ勝手に個別IDを割り当てない。失敗履歴を消さず、必要なら最後の確認済み履歴から
別の形状ステップを試して新規出力へ分岐する。履歴の自動分岐管理は未実装。

現範囲は円筒の離散段階間で個別IDを継承する履歴であり、標本間を通る連続した物理枝の証明ではない。
一般写像、部分空間ID集合の多段階継承、合流/分裂、適応的ステップ制御、GUI/Study/tuneは残件。
再検証には全元保存場が必要で、長い履歴では全段階の再計算コストが掛かる。
追加6テストは実FEM3時点交差・保存再開、未確認保存/停止、部分空間停止、
単独で有効でも不連続な段階の拒否、過去入力変更と厳密request、CLI往復を確認する。
