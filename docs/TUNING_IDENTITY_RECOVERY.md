# D01/D02 tuneの個別ID回復と保存再開

2026-09-14。要求版6は、既存の調整入力版1〜5と明示的な個別ID回復方針を組み合わせる。
各FEM試行の部分空間対応がPASSでも個別IDが未確認の場合、以前の試行の保存場と照合し、
全個別対応と継承ID集合の整合が確認できてから探索用の周波数を評価する。
回復失敗では当該試行の周波数をnullとして停止する。親D01/D02と全計画は継続中である。

## 要求

要求版6は次の3キーだけを持つ。

| キー | 内容 |
|---|---|
| `schema_version` | 整数6 |
| `tune_request` | 完全な従来の調整要求。版1〜5。版6の入れ子は禁止 |
| `identity_recovery` | 下記の参照方針と個別場比較条件 |

回復方針は`anchor_selection`と`controls`を必須とする。
`anchor_selection="fixed_trial"`では、0始まりの整数`anchor_trial_index`も必須で、
指定した過去の試行を使用する。番号は`max_trials`未満とし、実際の回復時点では既に評価済みでなければならない。
未来の番号を指定して回復が必要になった場合は入力エラーとし、以前のチェックポイントと失敗記録を保持する。

`anchor_selection="latest_resolved_trial"`では番号を指定せず、直近の個別ID確認済み試行を使う。
未確認試行の後は探索を続けないので、この試行は直前の試行になる。以前に回復した試行も使用できる。
最終細分の親が以前の最良試行である場合、細分元と回復参照先は異なり得る。
各比較はそれぞれの実試行の値・Projectから独立に写像を導出する。

`controls`は既存の個別比較条件で、集合をまとめる`cluster_transition_policy`は禁止する。
通常の親子比較とは別に、入力者が回復比較の条件を指定する。実行中の自動的な閾値変更は行わない。
版1〜3では対応する正規化写像、版4では実際の二試行の相対アフィン写像、
版5では実際の二試行の比較メッシュと元の固定細分履歴を使用する。
版4の`affine_map`と版5の`comparison_meshes`を回復条件へ直接埋め込むことはできない。
既存の各版と同じ検査を開始前に行う。未知キー・不正な選択肢・bool等は拒否する。

再現入力は[identity_recovery.json](../examples/tuning/identity_recovery.json)。
半径100 mmの解析円筒例に、固定試行0からの回復を指定している。
近接集合を定める親子比較のgapは0.2、回復の個別比較のgapは1e-6として最初から明示している。
これらの集合化を、二時点間の物理縮退の証明とは扱わない。

```sh
python -m superfish_ng tune examples/tuning/identity_recovery.json --out first --max-new-trials 2
python -m superfish_ng replay-tune first/checkpoint-002.json
python -m superfish_ng resume-tune first/checkpoint-002.json --out continued
```

## 判断・保存・GUI

親子比較がUNVERIFIEDなら回復を試みず停止する。全個別IDが既に確認済みなら回復を行わない。
PASSの部分空間に対してのみ、既存の`assess_identity_recovery`で参照場との全個別対応と
継承集合内のID一致を確認する。集合境界を越える割当ては受理しない。
成功したIDを試行へ保存し、同じnative固有値の対象順位から周波数を取得する。
FEM場・固有値・周波数順位・規格化・RF量を置き換えない。

回復がUNVERIFIEDなら、親子比較のPASSと回復失敗の両方を保持する。
試行の`frequency_hz`と`target_error_hz`はnull、文書はUNVERIFIED・再開不可となる。
その周波数で符号区間を更新したり、次のFEMや最終細分へ進んだりしない。
二つの周波数ゲート、探索回数と最終細分の予算、失敗記録の契約は維持する。
回復は保存場の比較でありFEMの追加ではない。各非初期試行につき最大1回行う。

外側の`document_type="tune_checkpoint"`は版2になる。
各trialの`identity_recovery`は未実施ならnull、実施時は以下を保存する。

- `schema_version=1`、`document_type="tune_identity_recovery"`。
- 実際の`anchor_trial_index`と`current_trial_index`。
- 全`comparison`（入力、導出写像、native出典、場対応）と`assessment`（候補ID、集合ごとの一致検査）。
- `status`と、保存二時点の再同定に限定する`scope`。

元要求・全保存場から試行順、回復と探索判断を再構築し、版・番号・比較・集合検査・元場の改変を拒否する。
PAUSED文書からだけ、要求を完全に維持し、過去の点を再計算せず新しい出力先へ再開する。
旧要求版1〜5のチェックポイント版1は従来通り読み書きする。

GUIの要求JSON欄は版6を受理し、重複キーをサーバーで拒否する。
形状・調整フォームには内側の入力を復元し、要求欄には回復方針を含む全版6を保持する。
各試行の回復元・確認済み/未確認、回復実施数と診断根拠を表示する。
再開では保存要求を使用する。最終場表示は回復後の対象IDの実順位を開く。

## 検証と範囲

開始HEAD `991560a`。要求版6不在の変更前失敗は`out/tuning-identity-recovery-20260914/baseline.log`。
最初の2不変条件は1.360秒PASS。その後の最終実装で、新`test_tuning_identity_recovery`9件が195.776秒PASS。
固定参照、回復済み参照、細分親と異なる参照、失敗時の周波数未評価、回復不要時の非実施、厳密入力、
改変拒否、後続失敗記録、CLI、JobManager再作成後のGUI transport再開を確認した。
非アフィン曲線の3モードでも、実FEMと固定局所履歴、回復元の実メッシュ、独立Green面積・体積の細分不変を検査した。
この曲線の調整目標は初期FEMから作った試験入力であり、解析周波数の精度基準ではない。

関連51件は319.436秒PASS。対象は`test_tuning`、`test_coupled_tuning`、`test_polynomial_tuning`、
`test_curved_tuning`、`test_curved_harmonic_tuning`、`test_tuning_jobs`、`test_gui_tuning`、`test_mode_identity_recovery`。
この二実行は計60件。追加で直接利用先test_te_jobsのTE未対応拒否1件（0.044秒）と、外側版6でのprofile/curved TE拒否2確認を実施した。
unitは計61件の三つの実行記録であり、全suiteの受入ではない。

`validate_tuning_identity_recovery.py`の専用55実FEMは54.516秒PASS。
基準・全長2倍・U4倍の各17試行（探索16＋最終細分1）と、回復未確認/実解析縮退の停止各2試行を含む。
各完了系列で15回回復し、1試行は親子比較だけで個別IDを確認したため回復を行わない。
2試行で停止してから再開し、837保存ファイル不変、CLI再生、求積次数12/16/18・直近参照・内側版2/3の同じ判断を確認した。
次数・参照方針・内側版の変更は既存解を再利用し、追加FEM0。
L=83.00048828125 mm、最終目標差約−8722.05 Hz、粗細差約3551.50 Hzで、それぞれの10000 Hz条件を満たす。
Bessel解析周波数最大相対差5.631e-6（事前閾値2e-5）、最終細分は2e-6以内。
全17試行×3モードの両R/Q・G・周波数と内部16点のH/E尺度則を別検査し、最大RF差6.862e-14・場差4.600e-14。
電場は全ベクトルのノルムで比較する。これらの事前閾値は2e-9で、代数残差から物理精度を推定していない。

別workerの19実FEMは13.340秒PASS。JobManager再作成後の再開と未確認停止を確認し、
全17native配列・RFは直接実行と完全一致した。
追加のCLI `resume-tune`は1新FEMだけを実行し、元2試行を保持、同じ第3試行と全配列・RFが完全一致した。
Chrome新版21/旧版16項目PASS、外部HTTP0。GUI新版17点も直接実行と完全一致し、CLI分と合わせて525元ファイル不変、照合の新FEM0。
GUIで完了した新FEMは72解。結果画像を目視し、全12GUIジョブ（10完了・2中止）の終端後に専用GUIを停止した。
一部の検証は並行しており、記録時間を単独性能と扱わない。

回復の二時点比較は連続した物理枝の保証ではない。tuneの最終二水準の差も離散化誤差上界やRF/ピーク収束の保証ではない。
新文献・依存・旧資産参照はない。全suite/seed/Hosted CI/新Wine比較は今回未実行。
親33=9受入/17進行/6他未受入/1範囲外、全計画goal ACTIVEを維持する。


2026-09-15 JST追加検証：`validate_tuning_recovery_curved_replay.py` は2859.966秒で終了0、PASS。
旧アフィン円筒の尺度1/2・単位m/1の各4解と、固定履歴付き調和変形円筒4解、計20保存解を再利用した。
固定/直近参照の10チェックポイントを構築し、保存再生、元の周波数との完全一致、実anchorからの写像導出を確認した。
追加FEMは0。Bessel周波数差の最大は2.274473e-5、最終細分は1.392679e-6未満、RF尺度差最大1.620926e-14。
元325ファイルと1075ソース系ファイルは検証中不変。数値時間は他検証と並行した観測値。
本専用の形状は円筒であり、非アフィン3モードの実形状は前記unitで別に検証した。
根拠は`out/tuning-identity-recovery-20260914/curved-replay/validation.json`。
2026-09-15 JST最終検証：[tune個別ID回復](TUNING_IDENTITY_RECOVERY.md)の曲線保存再生20解/10条件がPASS（追加FEM0）。
全339モジュール1742件の実行は1858.249秒で移行テスト3subtest ERROR、3skipを記録して終了1。
Study例をCaseとして読むテストを修正し、当該8件が0.383秒PASS。HTTP制限のskip1件も許可環境で0.563秒PASS。
最終証拠は1740件成功・任意NGSolve参照2件skipの分割実行。単一の全validate.py成功とは呼ばない。
標準数値は別の--skip-testsでPASS、既存9モード23量のf差0/最大相対差8.882e-16未満。曲線検証後のソース差は移行テスト1ファイルだけ。
受入索引out/tuning-identity-recovery-20260914/acceptance.json。全handle終端回収。親33=9/17/6/1、全計画goal ACTIVE。
