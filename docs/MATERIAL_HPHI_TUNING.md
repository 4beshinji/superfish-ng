# 固定材料の実FEM調整と明示ID回復

2026-09-22。H16-bの専用runnerと明示ID回復を受入。所有保存・永続再開・CLI/worker/GUIはH16-c/dに残る。全H16/全計画の受入とはしない。

要求`superfish_ng_material_hphi_tune`版1は完全な元Project、専用shape_law、正の無次元bounds、目標/周波数許容差、粗細周波数差許容値、探索回数、全初期prefix IDと選択ID、controls、最終細分段数、要素/DOF/点/界面予算、任意の明示identity_recoveryを持つ。非JSON型、未知キー、重複/不足ID、未計算guard、不正境界/予算を拒否する。生成前に最終/比較空間までの予算を検査する。

`run_material_hphi_tune`は各試行を元Projectから生成し、専用材料FEMをsolveする。初回も自己比較＋元領域の有限スペクトルguardでIDを確認する。以後の検索親は初回試行、最終細分親は対象検索試行とし、全E/H個別IDが確認されるまで周波数・目標差をnullに保つ。解析式は製品の周波数生成に使用しない。

確認済み周波数を用いて括弧内二分探索し、目標を満たした検索点を材料領域付きで実細分する。最終目標差と検索/最終の周波数差を別判定し、両者を満たした場合だけTUNED。片方不合格はREFINEMENT_FAILEDで、二メッシュ差を連続問題の誤差上界と扱わない。未確認ID/guardはUNVERIFIEDとして停止する。実行は完成したメモリ内試行間で区切ることができ、永続checkpointの代用品ではない。

`assess_material_hphi_tune`は元FEM列から全試行と判断を再生成する。各Caseを要求から作った候補Projectと照合し、元の全低順位正スペクトル・係数を再検証する。保存された周波数だけの辞書や改変係数は証拠として受理しない。`trial_material_hphi_project`と厳密JSON readerも同じ要求検証を使用する。

ID回復は、元E/H対応がPASSだが個別IDが未分離の集合を持つ場合にだけ行う。宣言された過去の確認済みanchorと改めて元E/Hを比較し、全個別IDと継承集合の整合を要求する。anchorと検索/細分親を別に保存し、未来/未確認anchorを拒否。guard失敗は回復へ渡さず、真の縮退を強制分解しない。

## 検証記録

runnerは`OPENBLAS_NUM_THREADS=1 PYTHONPATH=.:src:tests UV_CACHE_DIR=/tmp/superfish-uv-cache uv run --no-sync --python .venv/bin/python python`。出力は`out/h16-material-tuning-20260922/`。

- `before.log`は専用API未実装のred。`initial.log`は検査側がNumPyの解析周波数をJSON要求に混入したため拒否された記録で、検査入力をfloatへ変換した。製品の厳密型拒否は維持。
- `runner.log`：`test_material_hphi_tuning`新4件、64.249秒PASS/終了0。独立二層解析目標で検索3＋最終細分1試行がTUNED。初回guardで周波数null、改変元解拒否、要求/予算を確認。
- `nonuniform.log`：新1件、44.578秒PASS/終了0。epsilon=1/4・mu=1の二層を異なる率で伸長し、独立な接続式`sin(kL1)cos(2kL2)+(1/2)cos(kL1)sin(2kL2)=0`の最初の正根を目標に実調整。両層の体積比が異なること、全試行のfと実最終細分の両判定を確認。
- `recovery.log`：新2件の初期実行は83.671秒、1成功/1失敗。真の材料TEM/Bessel縮退を回復しない検査は成功。粗いn=4の成功対照は回復を未確認で停止した。
- `recovery-diagnostic.json`とlog：n=4では0.99試行の元周波数397.459/401.472 MHzに対し、有限区間395.198〜399.719/399.232〜403.710 MHzが重なる。回復側も集合しか確認できずUNVERIFIED。これは許容差で隠さず、比較空間の分離不足として保持する。

成功回復の対照はn=6へ細分し、`recovery-refined.log`で再検査。1件190.411秒PASS/終了0。解析周波数・実TEM場の材料質量overlap、検索/最終それぞれの別anchor、継承raw集合、未来anchor拒否、同じ実測最終試行に対する独立粗細gateを検証した。許容値や元の静的核/区間判定は変更していない。

`reader.log`は厳密JSON読込/重複キー/不正回復方針の追加1件、1.294秒PASS/終了0。新8件は分割実行証拠であり、一括suite成功とはしない。n=4の未確認とn=6の成功は別の証拠として保持する。全実行handle終端。

H16-bの一様材料/二層、uniform_scale/非一様写像、独立実最終細分、初回guard、回復成功と真の縮退拒否、周波数null、別目標/粗細gateという条件を上記で確認した。H16-aの形状/細分/元場検証を再利用し、元材料・規格化・RF規約を変更していない。

## 来歴と限界

既存自作の括弧内探索・決定関数・E/H回復集合判定を再利用し、専用材料Project/試行/solve/追跡へ接続した。二層接続式は既存弱形式のqとepsilon逆数付き軸微分連続条件から独立に導出し、検査側だけで求根する。新外部資料・依存・legacy参照なし。

共有FEM core/seed TMは変更しておらず、専用実調整・独立解析対照と既受入のH16-a基盤を検証範囲とする。全suiteや操作・永続保存を受入済みとは主張しない。RF収束、連続経路ID、物理誤差上界の保証を目標/二メッシュ判定から推測しない。
