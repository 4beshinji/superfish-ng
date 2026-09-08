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

## GUIでの対応比較・履歴操作

「モード対応と追跡履歴」で完了済みの個別結果を2つ選び、以前のIDを周波数順位順に指定する。
結果一覧にないnative保存場は既存の「保存済みの計算結果を取り込む」から検査して取り込む。
2時点比較では対象の個別結果を取り込む。完了Study全体には以下の専用操作を使う。
写像は円筒/profile/明示メッシュ対応から選ぶ。標本次数・重なり・候補差・クラスタ幅・ランクを明示し、
paired_meshではvertex_pairsをJSONで指定する。合流/分裂policyはチェックボックスで明示的に有効化する。

「2つの結果を比較」は共通の保存場APIで計算し、ID/ID集合、個別/部分空間、現在順位、周波数、重なりを表示する。
PASSでも個別ID未確定の部分空間があれば明記する。未確認理由・写像/controls・イベントは診断欄に保持する。
「追跡履歴を開始」後はIDの手入力を使用せず、基準結果を表示して「次の結果へ継続」する。
UNVERIFIED履歴は保存できるが、継続ボタンを無効にする。

「検証済みの文書を保存」でサーバー生成JSONをそのままダウンロードする。
「対応・履歴を開いて再検証」は元保存場から全体を再計算する。改変拒否後は以前の検証済み表示を保持し、
エラーを別表示する。再検証には文書の絶対パスで参照する元保存場が必要。
開始/継続でもサーバーの文書文字列を送信し、JavaScriptによる数値再整形を挟まない。
GUI輸送の既存4 MiB入力上限は維持する。巨大な履歴はCLI/APIで扱う。

5つの接続テストと実Chrome8操作で、円筒縮退例の取込、合流表示、履歴開始/分裂継続、
ダウンロード一致、ファイル再検証、改変拒否、未確認履歴の停止を確認した。
profile/paired_meshは共通APIへ接続するが、今回のブラウザー受入例は円筒写像。
初回ブラウザーでは1.0を1へ再整形した文書の再検証が失敗し、文字列保持へ修正して再実行した。
数値検証条件は変更していない。詳しい実行証拠は[GUI受入](GUI_ACCEPTANCE.md)。

## 完了Studyの隣接点を順番に追跡する

`study_mode_tracking` とtrack-study-modes CLIは、完了したnative Studyを読み取り、
宣言された値の順序で各隣接点を追跡する。Study本体/各点の完了とmanifest、study.jsonと要約の一致、
各点のProjectと生成予定Projectの一致、要約case hash/モード量と保存場の一致を確認する。
未完了/失敗Studyや欠損点は入力エラーとし、点を飛ばして追跡しない。

request版1の全項目は以下。step_controlsには点数-1個のcontrolsを必ず明示する。
全段階の項目名と数値範囲を先に検査する。paired_meshの対応表も各隣接点に対して個別指定する。

```json
{
  "schema_version": 1,
  "study_run": "study",
  "initial_ids": ["TM010", "TM020", "TM011"],
  "step_controls": [
    {"mapping":"normalized_cylinder","sample_order":12,"minimum_overlap":0.98,"minimum_assignment_margin":0.05,"relative_cluster_gap":0.001,"minimum_relative_singular_value":1e-8,"cluster_transition_policy":"retain_subspace","minimum_cluster_link":0.2},
    {"mapping":"normalized_cylinder","sample_order":12,"minimum_overlap":0.98,"minimum_assignment_margin":0.05,"relative_cluster_gap":0.001,"minimum_relative_singular_value":1e-8,"cluster_transition_policy":"retain_subspace","minimum_cluster_link":0.2}
  ]
}
```

study_runの相対パスはrequestファイル所在基準。初期IDは最初の点の周波数順位順で、
以後は履歴から継承する。最初のUNVERIFIED対応で停止し、後続点をNOT_VISITEDとする。
point_results、visited_point_indices、unvisited_point_indicesは0始まりのStudy点番号で、
FEMの1始まりmode_indexとは異なる。後続点のcurrent_mode_ids=nullは未追跡を意味する。
すでに全点を解いたStudyを後処理するため、追跡停止が元の計算を取り消すことはない。

```bash
OPENBLAS_NUM_THREADS=1 python scripts/validate_study_tracking.py --out out/study-tracking-new
python -m superfish_ng track-study-modes out/study-tracking-new/request.json --out out/study-tracking-cli-new.json
python -m superfish_ng replay-study-mode-tracking out/study-tracking-cli-new.json
```

Python APIはbuild/save/read/replay_study_mode_tracking。新規ファイルだけに保存し、
元Studyの独立スペクトル、mode_tracking記述、numerical_statusを変更しない。
別文書のStudy hashと履歴が今回の追跡の証拠となる。追跡PASSはFEM収束の合格ではない。
再読込は全Study出力と順序を再検証し、追跡を再実行して文書全体を照合する。
元Study/子Jobのバイト同一性と比較前後の安定性を検査する。元ファイルと絶対保存先が再検証に必要。
CLI終了コードはPASS=0、UNVERIFIED=1、入力/再検証エラー=2。

追加6テストは実Study順位交差と保存再検証、未確認停止/未使用controlsの検査、失敗点拒否、
manifestを更新しても順序不整合を拒否すること、途中変更/文書改変、CLIと厳密requestを確認する。
独立スクリプトはBessel零点から求めた縮退位置を含む3点を実P2 FEMのStudyとして解き、
解析周波数・集合継承・停止時の未追跡記録・元Study不変を確認する。
追跡付き逐次実行/チェックポイント再開は下記API/CLIへ追加。GUI JobManagerへの組込、適応的点追加、tuneは残件。

## 完了StudyのGUI操作

「完了したStudyを順番に追跡する」で同じGUI workspace内の完了Studyを選び、
最初の点のIDを周波数順位順に指定する。GUIで作成したStudy、またはworkspace直下へ
CLIで保存したStudyを選択できる。個別結果の取込操作はStudy全体の取込ではない。
段階別controlsを空欄にすると、上の写像・閾値を全隣接点へ適用する。
JSON配列を入力すると、その各段階の設定が共通欄より優先される。

結果表は0始まりの全点を初期点・確認済み・未確認・未追跡に分け、
部分空間内の個別ID未確定も表示する。未確認の段階で停止し、後続点を飛ばさない。
保存・再読込は元の文書文字列を保持し、Study全体と保存場を共通APIで再検証する。
再読込時には初期IDと段階別controlsも復元する。Study文書へ一般履歴の継続操作で
別の点を追加することはできない。元Studyの計算・収束判定は変更しない。

追加接続3テストと実Chrome7操作、既存の比較/履歴Chrome8操作がPASS。
証拠と再現手順は[GUI受入](GUI_ACCEPTANCE.md)。一般D01の完了ではない。

## 追跡しながらStudyを計算・再開する

`execute-tracked-study`は各点をnative FEMで解き、保存場の対応を確認してから
次の点へ進む。完了Studyの後処理とは別の実行経路で、最初の未確認の対応で停止する。
後続点は計算せず、`NOT_COMPUTED`と記録する。既存Studyの独立スペクトルや
収束判定をこの追跡状態で上書きしない。

requestはschema_version 1、`study`（通常のStudy宣言）、`initial_ids`、
`step_controls`（全隣接点の設定配列）の4項目。全点のProjectと全controlsを
出力先の作成前に検査する。初期IDは最初の点の周波数順位順に、重複なく指定する。
実例は`scripts/validate_tracked_study.py`が出力するrequest.jsonを参照。

```bash
python -m superfish_ng execute-tracked-study request.json --out out/tracked-NEW --max-new-points 1
python -m superfish_ng replay-tracked-study out/tracked-NEW/checkpoint-001.json
python -m superfish_ng resume-tracked-study out/tracked-NEW/checkpoint-001.json --out out/continued-NEW
```

`--max-new-points`は今回新たに計算する点数の上限。省略すると最後の点または
未確認まで実行する。各点の計算と追跡確認後にcheckpoint-NNN.jsonを新規保存する。
番号はStudyの1始まりの通し番号。文書の点indexは0始まり。
状態は`PAUSED`（確認済みの途中）、`COMPLETE`（全点を計算し対応確認）、
`UNVERIFIED`（対応未確認）。COMPLETEも物理的収束や連続枝の保証ではない。
CLI終了値はPAUSED/COMPLETEが0、UNVERIFIEDが1、入力/実行エラーが2。

再開できるのはPAUSEDのみ。元request・ID・閾値を変更せず、全先行点の入力・保存場・
Jobファイルの同一性と履歴を再検証する。新しい出力先に未計算の点だけを解き、
以前の点の絶対パスと証拠を継承するため、再検証には元の出力先も必要。
各点の計算中に先行点のソースが変わった場合もチェックポイントを公開しない。
未確認状態を閾値変更で上書き再開する操作は提供しない。

後続の計算が失敗した場合、保存済みの直前チェックポイントから別の出力先へ再開できる。
既存出力先は上書きしない。実行中プロセスの状態を再開対象とはしない。
OS強制終了・電源断の回復保証、適応的点追加、tuneは残件。JobManagerとブラウザーは以下で接続する。

## JobManagerから追跡付きStudyを実行する

`JobManager.start_tracked_study(request, max_new_points=None, checkpoint=None)`は
上記の実行APIを別プロセスで起動し、既存のstatus/cancel/list/closeを共用する。
requestは逐次実行APIと同じ。checkpointは再検証可能なPAUSED文書に限る。
再開は常に新しいJobを作り、前のJobの点を再計算・上書きしない。

Jobルートにtracked-study-request.json、tracked-study-results.json、manifest.jsonを保存する。
点とチェックポイントはexecution/以下に保存する。Jobの`status=complete`はワーカーの
処理と保存の完了を表し、`tracking_status=PAUSED/COMPLETE/UNVERIFIED`とは別である。
`numerical_validation=not_checked`を保持し、未確認を収束合格へ読み替えない。

`status(id, verify=True)`は現在のJobのmanifestだけでなく、継承した過去Jobの点も
再検証する。追跡状態・点数・再開可否の要約が保存文書と違う場合も拒否する。
中止・ワーカー異常終了では成功を公開しない。保存済みチェックポイントは残るが、
中止が書込み途中だったファイルは有効な再開点とみなさず、再検証できた文書を使う。
アプリ再起動時のinterrupted状態にもtracked_studyのJob種別を保持する。

このAPIを下記のブラウザー操作へ接続する。電源断回復保証、適応的点追加、tuneは残件。

## ブラウザーで追跡付きStudyを実行する

「追跡しながらStudyを計算する」の「現在のStudy・追跡設定を取り込む」で、
通常Study欄の入力と追跡欄の初期ID・共通/段階別controlsからrequestを作る。
JSON欄で入力を確認して開始する。点数上限を空欄にすると最後または未確認まで、
正の整数を指定すると今回の新規計算をその点数まで行う。

計算一覧で中止・完了結果の表示ができる。追跡付きJobは個別結果の比較選択欄へ混ぜない。
初点だけで停止して履歴がまだない場合も、各点の初期/確認済み/未確認/未計算を表示する。
部分空間内の個別ID未確定とID集合の診断を保持する。

チェックポイントは元JSON文字列のままダウンロードでき、ファイル再読込で全証拠を再検証する。
PAUSEDのみ「確認済みの続きから再開」が有効。再開は検証済み文書のrequestを用いるため、
JSON入力欄の編集で保存ID・閾値が変わることはない。変更した入力で実行する場合は新規開始する。
再開時にも点数上限を指定できる。COMPLETEとUNVERIFIEDからの再開は無効。

中止/失敗Jobの途中チェックポイントは、再検証できる保存ファイルを別途開ける。
計算一覧から途中ファイルを自動選択する操作は未実装。元の保存先が再検証に必要。
画面に残る結果は最後に検証した結果であり、入力編集や新規Job開始でその証拠を差し替えない。

## 未確認区間の適応的な二分

`execute-adaptive-study`は、対応がUNVERIFIEDになった幾何掃引区間へ中点を追加し、
実FEMで計算して再比較する。閾値は変更しない。確認できた点だけをID履歴へ追加し、
失敗した比較もattemptsに保持する。すでに計算した同じパラメータ値の端点は保存場を再利用する。

requestはschema_version 1、study、initial_ids、step_controls、adaptiveの5項目。
studyは厳密に増加または減少する数値の`/case/geometry/` sweepに限定する。
全元点と元区間の中点のProjectを事前検査し、追加候補も計算前に検査する。離散項目・未対応指定を黙って受理しない。
step_controlsは元の隣接目標点ごとの設定で、その区間に追加する点にも同じ設定を使う。

```json
"adaptive": {
  "max_depth": 4,
  "max_attempts": 16,
  "minimum_parameter_step": 0.000001
}
```

深さは元の区間を0として数える。max_depthは0〜20、max_attemptsは全体の比較回数上限。
minimum_parameter_stepは変更するパラメータと同じ単位で、二分して作る両区間の最小幅。
元の指定点の間隔を変更する制限ではない。中点が端点と浮動小数点で区別できない場合も停止する。
上限に達した場合はUNVERIFIEDと未到達の元目標点を記録し、後続目標を飛ばさない。
写像非対応・入力不正・FEM計算失敗は例外として停止し、自動細分で隠さない。

```bash
python -m superfish_ng execute-adaptive-study request.json --out out/adaptive-NEW
python -m superfish_ng replay-adaptive-study out/adaptive-NEW/adaptive-study-results.json
```

出力先は新規限定。`points`は計算順の全点で、未確認だった端点も含む。
`accepted_point_indices`はその配列への0始まりの参照をパラメータ順に並べるため、
番号順とは限らない。例えば初点→端点失敗→中点成功→保存端点成功なら`[0,2,1]`。
`reached_target_indices`と`unreached_target_indices`は元Studyの目標点番号。
`attempts`は全比較、採否、二分点、元目標番号、深さ、停止理由を持つ。

再読込は保存場から同じ二分判断を再実行し、全点の入力/hash、失敗した比較、
確認済みID履歴、停止理由を照合する。FEMを再計算しない。
COMPLETEは全元目標への標本対応の確認であり、連続枝や物理的収束の保証ではない。
細分で避けた区間内の縮退・未観測の交差を否定するものではない。

この段階はAPI/CLI。途中保存・再開は以下の保存版2で接続する。JobManager/GUIへの組込、
非幾何/非単調掃引、一般の再メッシュ写像・多対多/個別枝回復は残る。
通常の指定点列による逐次実行/再開と、そのGUIは従来の契約を維持する。

## 適応二分の途中チェックポイントと再開（保存版2）

新しい適応実行は保存文書schema_version 2を出力する。requestのschema_versionは1のまま。
旧保存版1のCOMPLETE/UNVERIFIED文書も同じ数値・二分判断で再検証できる。

```bash
python -m superfish_ng execute-adaptive-study request.json --out out/adaptive-first-NEW --max-new-attempts 1
python -m superfish_ng resume-adaptive-study out/adaptive-first-NEW/checkpoint-001.json --out out/adaptive-next-NEW
```

`--max-new-attempts`は今回新たに行う比較回数の上限。省略すると完了または本来の停止条件まで進む。
元requestのmax_attemptsは全実行を通じた上限として保持し、再開してもリセットしない。
深さ・最小幅・閾値・ID・目標点も変更しない。

各比較後に入力・保存場の安定性を確認してcheckpoint-NNN.jsonを新規保存する。
NNNは1始まりの全比較通し番号で、点の番号ではない。
版2はPAUSEDとcan_resume、次に比較する順のpending_targetsを持つ。
比較が未確認でも二分が可能なら、その失敗証拠と中点待ち状態をPAUSEDとして保存できる。
上限に達したUNVERIFIEDや全目標に到達したCOMPLETEからは再開できない。
PAUSED/COMPLETEのCLI終了値は0、UNVERIFIEDは1、入力/実行エラーは2。

再開は元文書の全比較を保存場から再検証し、同じ二分待ち列を復元してから新しい処理へ進む。
新しい出力先へ必要な点だけを計算し、すでに計算した端点・中点は元の絶対パスの場を再利用する。
過去の比較を再検証することはFEMの再計算ではない。新しい点が不要で比較だけで完了する場合もある。
元の出力先が失われたり変更された場合は再開・再検証できない。

中点の計算等で失敗しても、先に保存した有効なPAUSEDチェックポイントは残り、別出力先で再開できる。
書込み中断で壊れたファイルを有効な再開点に扱わない。電源断回復や実行中プロセスの再接続は保証しない。
適応実行も以下のJobManager/GUIへ接続する。通常の指定点列の再開文書とは別形式である。

## 適応二分のJobManager接続

`JobManager.start_adaptive_study(request, max_new_attempts=None, checkpoint=None)`は
適応実行APIを別プロセスで動かし、既存のstatus/cancel/list/closeを共用する。
再開は版2の有効なPAUSED文書に限り、新しいJobへ必要な点だけを計算する。
request・制限値・再開文書はJobの作成前に検査する。

Job種別はadaptive_study。ルートにadaptive-study-request.json、adaptive-study-results.json、
manifest.jsonを保存し、点と比較ごとのチェックポイントはexecution/以下へ置く。
Job status=completeと追跡状態PAUSED/COMPLETE/UNVERIFIEDを分け、
numerical_validation=not_checkedを維持する。

computed_pointsは失敗した比較の端点を含む計算済み点数、accepted_pointsは採用した点数、
completed_attemptsは比較回数。unreached_target_indicesは未到達の元目標番号を示す。
`status(id, verify=True)`はこれらの要約と文書を照合し、以前のJobから継承した保存場・
全失敗比較と二分判断も再検証する。要約だけを変更して完走や確認済みに見せることはできない。

共通中止処理を使い、中止・ワーカー失敗を成功へ移さない。再起動後もJob種別を保持する。
このJobManagerのPython APIへ、以下の適応実行用ブラウザー操作を接続する。
指定点列の通常追跡GUIや保存文書の契約を、適応実行の受入へ読み替えない。

## 適応二分のGUI操作

「追跡しながらStudyを計算する」で「取り込む設定に適応二分を追加」を選び、
最大深さ・総比較回数・追加区間の最小幅を指定して設定を取り込む。
開始方式はJSONにadaptiveがあるかで決まり、チェックボックスだけで既存JSONを書き換えない。
通常の処理上限は新規点数、適応実行では新規比較回数。適応の総上限は再開しても維持する。

計算一覧は適応Studyを区別し、中止・結果表示を共通経路で行う。
適応結果は計算済み点数、採用点数、比較回数、到達した元目標数を別々に示す。
点表は計算順と採用順、元目標と追加点を区別する。比較表には全ての採用/二分/停止と
対応のPASS/UNVERIFIEDを残すため、完了後にも粗い比較の失敗を確認できる。
二分待ちの次目標、未到達の元目標番号、上限等の停止理由も表示する。

元JSON文字列の保存・ファイル再検証・PAUSEDからの再開に対応する。
再開は保存文書のadaptive/ID/閾値/上限を用い、入力欄やチェックボックスの変更を反映しない。
COMPLETE/UNVERIFIED、または再開状態を持たない保存版1では再開できない。
通常追跡文書と適応文書は別の検証APIへ送り、形式を混同しない。
適応Jobは個別結果の比較選択欄には出さない。

このGUIで一般追跡、非幾何/非単調掃引、tune、電源断回復を受入済みにはしない。
中止/失敗後の有効な途中文書はファイルから再検証して開けるが、一覧からの自動選択は残る。

## 複数クラスタ間の保守的な集合継承（2026-09-08）

API/CLIのcontrolsに `cluster_transition_policy="retain_connected_subspace"` と
`minimum_cluster_link` を指定すると、既存の合流/分裂に加え、多対多のリンク連結成分を検査する。
両側とも複数クラスタで、両側に少なくとも一つ多次元クラスタがあり、
合計次元が等しい場合だけ和部分空間を候補とする。単一モードだけの曖昧な混合はまとめない。
候補化後も全ランク・最悪主角重なり・競合割当余裕を検査する。
合格した `REPARTITION` はID集合の継承を表し、各モードのIDはnullのまま。
無関係な単一モードの対応は維持でき、集合の順位は非連続でもよい。
連結和を選ぶことで保持する情報は粗くなるため、このpolicyは明示指定に限定する。
旧 `retain_subspace` の条件・保存文書の再検証結果は変更しない。

2時点保存・履歴とStudyのcontrols JSONに指定できる。GUIでは「モード群をID集合として
継続する」を有効にし、「集合継承の方式」で1対多/多対1または多対多を含む方式を選ぶ。
保存文書を再検証すると方式も復元する。無効化するとpolicy/linkを送らない。
再検証済み文書の集合継承は個別枝回復を意味しない。

`tests/test_cluster_repartition.py` は重み付き直交部分空間の分割変更、
基底回転/符号/倍率不変性、非連続順位、方向喪失・ランク不足・次元不一致の拒否を検査する。
`scripts/validate_cluster_repartition.py` は解析TM020/TM012縮退の円筒をP2 FEMで解き、
5周波数とBessel解析値を比較し、標本次数12/18で保存・履歴再検証を確認する。
これは同じ保存場に意図的な初期不確定ID集合を与える検査であり、
その集合が実際の形状掃引で生じたという証拠ではない。一般の枝回復・再メッシュ対応は残る。

## 同一領域の独立再メッシュ比較（2026-09-08）

controlsの `mapping="same_domain"` は、同じ直線辺の物理領域に対する異なる
三角形分割の保存場を比較する。頂点番号・頂点数・三角形接続の一致を要求しない。
軸接続の閉PEC領域に限定し、折返し境界とP1/P2場の相互比較にも対応する。
`sample_order` は各三角形の次数2〜32、両メッシュ合計262144標本以下。
その他のcontrolsとID集合policyは共通。追加のvertex_pairsは受け付けない。

各境界辺が相手側の同じタグを持つ共線辺で隙間なく被覆されることを双方向に確認する。
辺の細分は許す。判定の丸め幅は座標最大絶対値×128εで、値を診断へ保存する。
両メッシュの各三角形で正の積分点・重みを生成し、同じ物理座標で双方のHphiを評価する。
片方ずつの体積測度 `r detJ w` を1/2ずつ合わせるため、比較はメッシュの選択に対して対称。
共通定数2πは正規化で相殺される。積分体積、三角形数、標本数と方式を診断に記録する。
外側の標本を落としたり補間値を埋めたりせず、場評価の領域外は失敗させる。

これはメッシュ交差分割上の厳密積分ではない。異なる要素の境界で場の導関数が変わるため、
利用者は標本次数を上げて対応結果を確認する必要がある。小さい標本次数差だけで
厳密な積分誤差上界やFEM収束を主張しない。異なる形状・曲線二次幾何はこの方式で受理しない。
同じ解析曲線でも異なる曲線近似領域を勝手に同一視しない。形状変形と再メッシュを
同時に扱う一般写像は残件。GUIでは「同じ直線境界の領域（異なるメッシュ）」を選択する。
保存対応/履歴から写像を復元し、比較と履歴継続に使用する。

API `same_domain_tracking.track_same_domain_modes` と既存track-modes/履歴CLIで指定できる。
`tests/test_same_domain_tracking.py` は独立多項式場の重なり1、円筒体積、P1/P2相互比較と
双方向一致、境界変更/タグ/曲線/上限拒否、保存再検証と履歴を検査する。
`scripts/validate_same_domain_tracking.py` はP2円筒と合成折返し領域を別々に再メッシュし、
次数3/5、円筒Bessel周波数、多角形体積式、Maxwell相似則f/RQ/G、保存再検証を検査する。

今回の独立再メッシュ例では、円筒2モードのメッシュ間相対差は周波数最大3.629e-6、
R/Q最大2.654e-4、G最大1.826e-5。粗い折返し例ではそれぞれ0.006614、0.02811、0.01022。
対応判定PASSでも粗いメッシュのRF量が収束したわけではない。
実数値は `out/d01-same-domain-final-20260908/remesh_differences.json` に保存する。

## 明示アフィン変形と独立再メッシュ（2026-09-08）

`mapping="affine_remesh"` と次のcontrolsを指定する。

```json
"affine_map": {"radial_scale": 1.2, "axial_scale": 0.8, "axial_shear": 0.0}
```

旧座標から新座標への変換は `r_new=a*r_old`、`z_new=b*r_old+c*z_old`。
上記のキーは順にa、c、bに対応し、すべて明示する。a,cは有限の正数、bは有限数。
軸と原点を保ち、反転・軸移動・非アフィン変形は指定できない。
Case自体の軸接続/領域制約も引き続き適用される。

新メッシュの座標を逆変換し、旧メッシュとの境界全辺被覆・タグ一致をsame_domain方式で
検査する。座標を推測せず、誤った変換は境界不一致として拒否する。接続や頂点数の一致は不要。
P1/P2係数は接続を保持したまま逆変換座標で評価する。P2の接続一致も検査する。
新側の評価値は `r_old*u_new = Hphi_new/a`。この定数倍率と体積比 `a²c` は
正規化した部分空間比較で相殺される。物理的な場の変換やFEM再計算を置き換えるものではない。
保存診断には指定変換、体積比、逆変換領域/実領域の体積、標本数、適用範囲を残す。
標本次数2〜32と合計262144標本上限、次数を上げた確認、領域外拒否はsame_domainと共通。

逆方向の履歴継続には `a_inv=1/a、c_inv=1/c、b_inv=-b/(a*c)` を明示する。
同じ変換を逆方向へ再利用しない。API・track-modes・履歴CLIとStudyのcontrols JSONで指定できる。
GUIでは「軸を保つアフィン変形」を選び、a,c,bを入力する。保存文書からも復元する。
「入力した変換を逆変換にする」は入力欄だけを逆変換へ変える。比較対象は利用者が選ぶ。
不正な逆変換は入力を部分更新せず拒否する。他写像では係数を送らない。
二次曲線幾何、任意非アフィン写像と連続枝の同定は未対応。
既存same_domainの計算・保存再検証結果は変更していない。

追加検査はP1/P2独立多項式場の重なり1、恒等写像一致、逆変換の双方向一致、
不正変換/境界不一致の拒否、保存/履歴再検証。
`validate_affine_remesh_tracking.py` は異方倍率円筒とせん断三角形を別々に再メッシュし、
Bessel周波数・独立体積式・全長2倍のMaxwell相似則f/RQ/G・次数3/5・保存再検証を確認する。
三角形は合成幾何。せん断後の厳密固有周波数やRF収束を受入したものではない。

## 比較用メッシュによる区分アフィン変形（2026-09-08）

`mapping="piecewise_remesh"` と `comparison_meshes=[旧比較メッシュ,新比較メッシュ]`
をcontrolsに指定する。それぞれは既存の[タグ付きメッシュJSON](MESH_INPUT.md)の完全なオブジェクト。
schema_version=1、length_unit=m、coordinate_order=rz、index_base=0を明示し、points/triangles/boundary_edges/boundary_tagsを含む。
旧・新で頂点数、三角形の向き付き接続、境界辺とタグの配列が一致する必要がある。
同じ番号の頂点を結ぶ写像を明示する契約で、番号を自動推定しない。

比較メッシュは、各Caseの物理領域を正の三角形で完全に覆う連結円板として検証する。
穴・反転・余分/欠損境界・未使用点・不正タグ等は拒否し、実FEM境界とも全辺を照合する。
実FEMメッシュの頂点数・接続は比較メッシュと一致する必要がない。
比較三角形の同じ重心座標から旧/新の物理位置を求め、その位置で保存したP1/P2場を評価する。
比較メッシュの節点へ場を補間してから再補間する方式ではない。

両側それぞれ `Hphi * sqrt(r/max(r)) * sqrt(detJ/max(detJ))` を標本値に使う。
共通の基準三角形測度に引き戻す際の可変体積因子を保持し、定数だけを正規化で相殺する。
局所的な径/長さ変更に対して体積因子を一定と仮定しない。
`sample_order` は2〜32、比較三角形数×次数²は262144以下。
比較用三角形と実FEM要素は異なるため、次数を上げて標本対応を確認する。
厳密な交差分割積分・積分誤差上界・FEM収束証明ではない。

controlsの完全な比較メッシュを保存要求に保持し、診断には各メッシュのSHA-256、
比較/実FEMの三角形数、標本数、積分体積、ヤコビアン範囲、境界丸め幅を記録する。
逆方向へ継続する場合はcomparison_meshesの2要素を入れ替える。
API・track-modes・履歴CLIとStudyのcontrols JSONで使用できる。APIにはCase付きの
native保存解を渡す。GUIの入力は後続。二次曲線幾何と対応の自動推定は未対応。
個別枝の連続同定や物理収束の保証も含まない。

追加5検査は、可変体積因子を含む重なりと独立二重積分の一致、反転/欠損セル/
不正境界拒否、独立FEM接続、保存と逆方向履歴、入れ子の厳密schemaを検査する。
`validate_piecewise_remesh_tracking.py` は局所profile変形と合成折返し変形を実FEMで解く。
比較/旧FEM/新FEM三角形数は8/240/468、44/74/167。次数6/10、解析体積、
初期円筒Bessel周波数、全長2倍のMaxwell相似則f/RQ/Gを検査する。
変形後の厳密固有周波数・物理RF収束を受入したものではない。
