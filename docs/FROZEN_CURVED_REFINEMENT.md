# 曲線局所細分の選択を固定した形状変換

2026-09-14追補：固定履歴を[調和変位による曲線変形](CURVED_HARMONIC_DEFORMATION.md)へ接続した。曲線番号/分率を宣言し、非アフィンな移動でも同じ親子関係と品質/予算を維持する。

2026-09-14追補：固定したProjectを[曲線アフィンStudy](CURVED_AFFINE_STUDY.md)へ接続した。通常掃引・保存追跡・逐次/適応再開とGUIで、元の分割と実比較点の写像を保持する。以下は固定機能の受入時点の記録。

2026-09-14 JST、N04の履歴付き形状変更に必要な保存契約を追加した。
元の形状で選ばれた分割辺と遷移要素の対角線を保存し、宣言したアフィン変形後も
同じ参照三角形の分割を再構築する。元の番号付きメッシュもProjectへ保存する。
通常の局所細分は従来どおり現在の形状から選択する。固定は明示操作である。

## 問題と受入条件

従来の局所細分は、接触する要素の最長弦辺を追加分割し、二辺分割の遷移要素では
短い対角線を選ぶ。この幾何依存の選択は異方的な変形で変わる。
そのため、元のmarked番号列を維持しても後段の親子関係が変わり得る。
既存のProject変形は各段階を照合してUNVERIFIEDとして拒否していた。

先に保存した負例は、合成した二つの半楕円の輪郭で、marked [0] → uniform →
marked [0]、最小頂点接線角1度、半径2倍・軸方向0.5倍。
固定前の変形は接続不一致で拒否される。必要な独立不変量は、参照領域の制限と
宣言アフィン変換が可換で、子の親要素・節点接続・境界所属が保たれることである。
拒否を誤周波数として数えず、既存の拒否条件もテストに残した。

受入条件は次の範囲とした。

1. 元の全二次幾何配列を変えずに選択を固定し、保存往復と再固定が同じ結果になる。
2. 固定後の異方的変形で節点・親子接続を保持し、質量測度と独立面積/体積の変換則を満たす。
3. 異なる親接続、不完全な分割、未知入力、品質・要素予算の違反を拒否する。
4. 実FEMの保存再検証、追跡、周波数調整、CLIとGUI保存・解除・Undoへ接続する。
5. 旧入力経路とseedの周波数・RF量を確認する。固定を物理精度保証とは呼ばない。

## 操作と保存形式

Pythonでは `freeze_curved_refinement(project)` が新しいProjectを返す。
入力は組立sectionsのない二次幾何Projectで、少なくとも一つのmarked段階が必要。
元メッシュがなければ元Caseから一度生成し、明示元メッシュとして保存する。

```sh
.venv/bin/python -m superfish_ng freeze-curved-refinement source-project.json --out frozen-project.json
```

出力は新規ファイルだけに作成する。元入力と既存出力を上書きしない。
固定したProjectを既存の `transform_curved_project`、曲線tune要求版4へ渡せる。
RF座標のfixed/axial方針、物理/近似条件の再検査は
[アフィン変形](CURVED_PROJECT_TRANSFORM.md)と[曲線調整](CURVED_TUNING.md)に従う。

Case版3の各marked段階に省略可能な `split_pattern` を追加した。
未指定の旧JSONは変えない。uniform段階での指定は拒否する。
入れ子の宣言版1は次の全フィールドを要求し、未知・欠落フィールドを拒否する。

| フィールド | 意味 |
|---|---|
| `schema_version` | 整数1 |
| `parent_topology_sha256` | 直前P2接続とラベル付き境界所属のSHA256 |
| `marked_cells` | 元の要求と一致する、整列済みの一意な0始まり要素番号 |
| `split_edges` | 実際に分割する親の頂点番号対。各対は小さい番号から、対列も整列・一意 |
| `transition_diagonals` | 二辺分割の全親要素について、要素番号と既存テンプレートの対角線選択0/1 |

二辺分割では親の頂点列を巡回させ、未分割辺をAB、残る頂点をCとする。
P/Qを参照辺BC/CAの中点とすると、共通の子は(Q,P,C)。選択0は
(A,B,P)/(A,P,Q)、選択1は(A,B,Q)/(B,P,Q)を加える。
固定しない場合は物理弦APとBQの長さを比べ、AP≤BQなら0を選ぶ。

SHAの対象は `cell_nodes`、`boundary_nodes`、`boundary_curve_indices`、
`boundary_tags` のsort_keys/compact JSON。座標とcurve fractionは含めない。
これは番号付き接続への拘束であり、任意のメッシュ間の物理対応の証明ではない。
変形そのものの対応は宣言写像と二次幾何全体の照合が担う。

再構築では、全指定辺が存在すること、要求要素の三辺をすべて分割すること、
二辺分割要素に過不足なく対角線を指定することを確認する。
元の参照テンプレートで構築し、正Jacobian・半径・全辺の適合性/交差・境界、
現在の頂点接線角と要素予算を再検査する。固定した選択でもこれらの違反は拒否する。
native読込・入れ子追跡・適応計算の履歴適用も同じ宣言を使用する。

GUIの「現在の局所分割を固定する」は、元メッシュと全marked段階を保存し、
固定状態を行に表示する。固定中の種類/番号は保護する。
「固定を解除」または図上での再選択により、その段階の固定を明示的に解く。
後続marked段階の番号と固定宣言は無効化し、旧番号を参照用に表示して再指定を求める。
図上操作のUndoは固定宣言も復元する。非同期処理中に入力が変われば応答を適用しない。

## 独立検証と観測値

証拠の親ディレクトリは `out/frozen-curved-refinement-20260914/`。
`baseline-red.json` は固定前の拒否、`source-project.json` と `frozen-project.json` は
実CLIで使用した入力/出力である。外部資料・依存・旧資産の新規参照はない。

関連unitは `test_frozen_curved_refinement`、`test_curved_marked_refinement`、
`test_curved_refinement_steps`、`test_curved_project_transform` の21件が14.777秒PASS。
その後に追加した入れ子追跡とCLI上書き拒否の2件も2.139秒PASS。
同一の23件を一度に実行した記録ではない。

`scripts/validate_frozen_curved_refinement.py --out <新規ディレクトリ>` は
75.988秒PASS。専用検証の新規FEMは8回で、四形状の直接求解と実tuneの四試行からなる。
元形状I、A=diag(2,0.5)、2I、2Aはいずれも108要素で、同じ固定履歴を保持する。
座標は宣言変換に絶対2e-15 m以内で一致し、接続と境界所属は完全一致した。

u=Hφ/rの質量測度r³ dr dzは、半径倍率a・軸倍率cに対しa⁴c倍になる。
組立質量行列との差は最大4.660e-16。別のGreen境界積分による面積ac・回転体積a²cの
尺度則も相対1e-12以内。保存nativeの再読込でuは完全一致した。
同じ蓄積エネルギーで一様2倍した二組について、fは1/2、両R/Q・G・TTFは不変で、
これらの最大相対差は3.176e-14。Hφ/Er/Ezのλ^(-3/2)則は最大4.103e-12。

曲線tuneはAの後の一様倍率xを[1,1.2]で探索し、目標をf(A)/1.1とした。
三探索試行と最終一様細分の四試行でTUNED、x=1.1。
元の50 kHz目標/メッシュ差条件を維持し、最終メッシュ周波数差は7498.935 Hz。
全試行で固定prefixを保ち、保存された判断の完全replayも一致する。
二メッシュ差は診断であり、離散化誤差上界やRF/表面収束の保証ではない。

実Chromeは `browser/report.json` の新9項目と
`history-regression/report.json` の既存途中挿入20項目がPASS。
CLIとの固定入力一致、行の保護、保存往復、解除/再選択/Undo、実worker/native保存、
処理中入力変更の拒否を確認した。既存の6,656要素Canvas途中挿入も通る。
両実行で外部HTTP要求0、製品ファイル不変。`browser/frozen-history.png` を目視確認した。
専用native検証中のsrc/tests/scripts/examples 1,002ファイルも不変。

## 共有経路の全件試行と補修

新しい履歴契約がCase/native/追跡/適応へ共有されるため、製品を固定して
`OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/validate.py --out out/validation-frozen-curved-refinement-20260914`
を一度実行した。全320モジュール/1,602テストを888.194秒で回収し、
1,598合格・2 skip・2不合格、終了1。初回のFAIL記録を保持する。
不合格は既存幾何診断テストの旧期待値で、新規診断の版を8とする箇所（現行13）と、
拒否メッセージの対応構築版一覧を9までに固定する箇所（現行10を含む）だった。

製品を変更せず、その2テストファイルだけを修正した。
新規診断は版13を要求し、旧版1の保存/CLI完全再生を引き続き検査する。
未対応構築の拒否は、変動する版一覧全体ではなく意味のある拒否理由を照合する。
`test_coincident_circle_arcs` / `test_construction_diagnostics` の全12件を
1.198秒で再実行しPASS。記録は `diagnostic-test-repair.log` / `.json`。

全件試行は不合格によりseed前に止まるため、seedだけを別の新規出力
`out/validation-frozen-curved-refinement-seed-20260914/` で実行しPASS。
`seed-regression.json` はbenchmarks/validationの9モード・19周波数/RF/エネルギー量を照合し、
周波数差0 Hz、最大相対差8.882e-16。専用nativeとseedの1,002ソース系SHAは一致し、
以後の変更は前記2テストだけ。両Chromeが記録した製品311ファイルも最終状態と一致する。
全件試行・修正後の対象再実行・seed別実行を合わせた証拠であり、
修正後の単一full-validator PASSとして表示しない。合格済みの全件を件数更新のため再実行しない。
Hosted CI、実測、新しい旧ソルバー比較は未実施。

全証拠の索引は `out/frozen-curved-refinement-20260914/acceptance.json`。
専用GUI PID1056389は完全argv照合後にSIGINTで停止し、終了0。
全検証プロセスの終了結果を回収した。

## 残る範囲

この契約は、元の分割を保持できる宣言アフィン形状変更と既存曲線tuneへの接続である。
後続の[宣言アフィンStudy](CURVED_AFFINE_STUDY.md)は接続済み。一般形状/初期再メッシュの掃引、独立メッシュへの自動番号対応、
一般非線形分割移送、物理枝の自動回復は別途必要。
N04全体の一般精度/効率、C00.V/G03/V02と全計画goalは継続する。
親33課題の8受入/17進行/7他未受入/1範囲外は変更しない。
