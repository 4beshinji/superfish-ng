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
既定経路ではクラスタの合流/分裂を別のクラスタ群へ自動変換しない。明示policyによる集合継続は後述。

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

一般形状の比較写像・写像精度、クラスタ合流/分裂、合流/分裂を含む一般的な追跡履歴と安定IDの保存/再開、
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

第1版では最後の段階がPASSかつ全個別IDが確定している場合だけcan_extend=trueとなる。
第1版は未確認の段階も保存するが、その後の延長は拒否する。部分空間対応自体がPASSでも、
個別IDが未確定なら履歴はUNVERIFIEDとして停止理由を保持する。
部分空間内の基底へ勝手に個別IDを割り当てない。失敗履歴を消さず、必要なら最後の確認済み履歴から
別の形状ステップを試して新規出力へ分岐する。履歴の自動分岐管理は未実装。

現範囲は円筒の離散段階間で個別IDを継承する履歴であり、標本間を通る連続した物理枝の証明ではない。
一般写像、合流/分裂、適応的ステップ制御、GUI/Study/tuneは残件。部分空間ID集合の多段階継承は次の第2版で対応する。
再検証には全元保存場が必要で、長い履歴では全段階の再計算コストが掛かる。
追加6テストは実FEM3時点交差・保存再開、未確認保存/停止、部分空間停止、
単独で有効でも不連続な段階の拒否、過去入力変更と厳密request、CLI往復を確認する。

## 第2版: 部分空間ID集合の多段階継承

新規履歴はschema_version=2。部分空間対応もPASSなら延長できる。
current_identity_groupsは `{"indices":[1,2],"ids":["A","B"]}` のような集合を持つ。
indicesは現在の1始まり周波数順位で、idsの並びと各基底との1対1対応を意味しない。
current_mode_idsは多次元集合の位置をnullのまま保持し、individual_ids_complete=falseとする。
PASS/can_extend=trueを、個別IDの確定やtuneへの周波数受渡し許可へ読み替えない。

延長で作る2時点requestも第2版とし、previous_idsの代わりにprevious_groupsを必須とする。
各集合は昇順の重複しない順位列と同次元のID集合を持ち、全順位を重複なく覆い、全IDも一意でなければ拒否する。
標本APIではprevious_ids=Noneとprevious_identity_groupsを明示する。両方の同時指定は禁止。
前段階の集合を以前のクラスタとして保持し、新段階の周波数クラスタと最悪主角で比較する。
新しいrelative_cluster_gapで以前の集合を勝手に分割し直さない。
既定では旧集合と新クラスタの次元不一致、合流/分裂、重なり不足をUNVERIFIEDとして保存し、延長を停止する。
履歴の再検証ではID集合の継承も照合する。個別ラベルを仮に基底へ割り当てる内部処理は使わない。

第1版の2時点文書と履歴は元の意味のまま再検証する。第1版の部分空間停止を自動でPASSへ変更しない。
第2版で継続する場合は、保存済みの2時点文書からstart-mode-historyで新しい履歴を明示作成する。
確認済みの第1版個別ID履歴はextend-mode-historyで第2版へ継承できる。
CLIの操作・延長requestの2項目は変わらない。

追加5テストは3時点の独立直交基底回転/順位交差、集合分裂、厳密分割、
native保存場での集合履歴/改変拒否、第1版停止の互換性を確認する。
実FEM検証では明示的に広い周波数gapで3モードを一つの部分空間へまとめる。
これは集合の保存/再開検査であり、3モードが物理的に縮退しているという主張ではない。

## 半径可変profileの体積整合写像

`profile_mode_tracking.track_profile_modes` と保存request/履歴/CLIで
mapping="normalized_profile" を明示すると、正の連続折れ線R(z)を持つprofileへ対応する。
両端PECの真空m=0 TMに限定し、段差、折返し輪郭、native曲線、対称端は拒否する。
解は既存read_solutionで読み込んだ、Caseと実場を含む保存解を渡す。
既存normalized_cylinderは計算・出力とも変更しない。

参照写像を r=rho R(L zeta), z=L zeta と定義する。体積要素は
2π L R(L zeta)² rho d_rho d_zetaなので、比較標本をHphi*R(z)/Rmaxとし、
共通重みrho d_rho d_zetaを使う。一定因子2π L Rmax²は各モードの正規化で消える。
この処理は磁場の物理的な二乗積分に含まれる変動体積要素を保持する。
異形状間の対応はこの明示写像で定義するもので、唯一の物理対応を保証するものではない。

両形状のz/L節点の和集合で参照区間を分割し、各区間と半径方向にsample_order点の
Gauss-Legendre則を使う。標本次数・点・重み・分割点・両profile・場の倍率を結果へ保存する。
標本総数は262144以下とし、超過は次数や節点数を減らすよう明示的に拒否する。
参照節点の尺度変換による潰れ、半径比のunderflow、非正重みも黙って進めない。
節点分割はFEM要素境界を全て含む積分ではなく、標本数を変えた検査は引き続き必要。

```bash
OPENBLAS_NUM_THREADS=1 python scripts/validate_profile_tracking.py --out out/profile-tracking-new
python -m superfish_ng replay-mode-tracking out/profile-tracking-new/pair.json
python -m superfish_ng replay-mode-history out/profile-tracking-new/history.json
```

独立検証は合成半径可変profileを実P2 FEMで解き、2倍相似形状と局所半径1%変更形状を保存する。
相似則f→f/2、R/QとGの不変性を検査する。標本次数8/12の両方で対応を確認し、
保存後の2時点対応・履歴再開も検証する。局所変更例の対応成功は任意の形状変化へ一般化しない。

追加6テストは、正則な試験場Hphi=rの体積積分から導く重なり
(7/3)/sqrt(31/5)、両側節点と冗長な直線節点の不変性、未対応入力、
実FEM相似則と標本次数、保存/履歴、円筒極限で従来写像との一致を確認する。
試験場の積分検査と、実FEM固有モードの検証を分離する。
折返し・曲線等への一般写像、合流/分裂の解決、適応的ステップ、GUI/Study/tuneは残件。

## 明示頂点対応による折返し・曲線メッシュの比較

`paired_mesh_tracking.track_paired_mesh_modes`、保存request、履歴、CLIで
mapping="paired_mesh" を明示すると、同じ三角形接続構造を持つ保存メッシュを比較できる。
controlsは従来6項目にvertex_pairsを必須追加する。各組は `[旧頂点番号, 新頂点番号]` の
0始まり整数で、両方の全幾何頂点を重複なく覆う。頂点番号の一致を暗黙の対応として扱わない。
二次幾何ではcell_nodesの先頭3節点に現れる頂点だけを指定し、辺中点の対応は対応辺から決まる。
中点を含む全DOF番号の対応表ではない。

全三角形の全単射と、軸/PEC境界辺・タグの一致を検査する。要素順・局所頂点順・頂点番号は
一致しなくてよい。対称境界は拒否する。メッシュが別の接続構造を持つ場合の自動対応は行わない。
各保存メッシュは既存のnative読込検証を通す。三角形の参照重心座標を頂点対応で並べ替え、
各側の直線/二次幾何写像とP1/P2場から直接Hphiを評価する。実FEM場を解析場に置き換えない。
曲線要素を弦へ置換せず、要素内の実際の二次Jacobianを使う。

共通参照三角形上で体積要素は2π r detJ d_xi d_etaとなる。
場標本にsqrt(r/max(r))*sqrt(detJ/max(detJ))を掛け、Duffy積Gaussの正重みで比較する。
各側の一定因子2π max(r) max(detJ)は正規化から消える。物理体積の変動部分は残る。
半径・Jacobian・倍率の非正/非有限値、underflowを黙って進めない。
次数は各三角形2〜32、総標本262144以下。メッシュ節点対応、要素対応、局所順序、
参照点・重み・倍率の定義を保存し、履歴再開時も次のvertex_pairsを明示する。

```bash
OPENBLAS_NUM_THREADS=1 python scripts/validate_paired_mesh_tracking.py --out out/paired-tracking-new
python -m superfish_ng track-modes out/paired-tracking-new/folded-request.json --out out/paired-cli-new.json
python -m superfish_ng replay-mode-history out/paired-tracking-new/ellipse-history.json
```

独立検証は合成折返し輪郭とnative楕円曲線のP2 FEMで、2倍相似に加えて頂点番号を逆順、
要素順を逆順、局所頂点順を巡回置換する。利用者指定に相当する対応表を明示生成し、
f→f/2、R/QとGの不変性、次数3/5の対応、保存・履歴の往復を確認する。
これらは同じ接続構造に対する写像の検証であり、独立に再メッシュした形状の対応推定ではない。

追加5テストは曲線写像r=xi,z=eta(1+a xi)、正則試験場Hphi=rの独立積分、
厳密全単射/境界/接続/予算検査、折返し相似・番号置換、native二次曲線相似、保存/履歴を確認。
曲線試験場の重なりは独立1次元積分を、各側の二乗積分1/20と1/20+a/30で正規化して照合する。
この対応指定は位相的に整合する写像を与えるが、物理モード枝の唯一性や連続追跡の証明ではない。
接続が変わる再メッシュ間の写像、合流/分裂解決、適応的ステップ、GUI/Study/tuneは残件。

## 合流・分裂をID集合として継続する明示policy

controlsに次の2項目を同時に指定すると、標本API・全写像・保存・履歴で集合継続を有効にする。
指定しない既存requestと保存文書は従来の計算結果・停止意味を維持する。

```json
{"cluster_transition_policy":"retain_subspace","minimum_cluster_link":0.2}
```

minimum_cluster_linkは0より大きく1以下。旧/新クラスタの重み付き直交基底U,Vから
sqrt(||U^T V||_F² / min(dimU,dimV))を求め、閾値以上を二部グラフの辺とする。
これは小さい側の部分空間が相手に含まれる割合から作る、基底に依存しない候補指標。
辺は候補抽出にだけ使い、追跡の合格判定には使わない。

連結成分が多対一または一対多で、旧/新の合計次元が等しい場合だけ、双方を一つの比較集合へまとめる。
まとめた場を再直交化し、既存の最悪主角・ランク・割当分離の全条件で対応を検査する。
ランク不足、方向喪失、重なり不足は集合候補ができてもUNVERIFIED。
全て単一モードの曖昧な回転や、多対多の再構成を大きな集合にまとめて合格へ変換しない。
各候補のMERGE/SPLIT、旧/新順位・ID集合・次元・判定、元クラスタとlink行列を保存する。
判定はこの比較段階のクラスタ関係であり、連続した時間経過の物理イベントの証明ではない。

分裂後もID集合を保持し、個別ラベルを基底へ付け直さない。集合の順位は非連続でもよい。
例えばindices=[1,3], ids=["A","B"]と、indices=[2], ids=["C"]を同時に持てる。
集合内の個別周波数は拒否し、独立に確認された単一IDだけを受け渡す。
非連続順位の集合でも全順位の重複なし分割とIDの一意性は必須。
継承集合と現在の周波数クラスタが異なる場合、各比較でSPLIT候補を再検査する。

```bash
OPENBLAS_NUM_THREADS=1 python scripts/validate_cluster_transitions.py --out out/cluster-transitions-new
python -m superfish_ng replay-mode-history out/cluster-transitions-new/history-c-12.json
```

半径0.1 mの円筒で、Bessel零点からL=πR/sqrt(j02²-j01²)を独立に求める。
L=0.055 m→縮退位置→0.075 mをP2 FEMで解き、TM020/TM011の合流と分裂を標本次数12/18で検査する。
解析式は検証形状と参照周波数にだけ使用し、追跡のID選択には渡さない。
縮退後はTM010を個別に保持し、TM020/TM011は集合のままで、個別枝の回復を主張しない。

追加6検査: 解析基底回転での合流、非連続順位への分裂/継承、単一モードの曖昧混合、
候補集合の方向喪失/ランク不足、厳密policy、実FEM縮退と保存再開/改変拒否。
多対多の再構成、分裂後の個別枝回復、接続が変わる再メッシュの写像、適応的ステップ、GUI/Study/tuneは残件。
