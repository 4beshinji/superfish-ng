# 曲線TEの宣言比較写像

2026-09-15、開始HEAD `5df18b8`。D02曲線TE調整の前提として、
保存TE場を既存のpiecewise_remesh比較版2/3/4/5へ接続する。
受入条件は実非アフィン形状・独立FEM接続、可変体積重みの独立積分、
Maxwell尺度則、native再生・改変拒否、旧TM互換である。

各側の実P2比較写像を再構築し、native領域との全二次境界一致、正Jacobian、
辺交差、接続または共通参照被覆、履歴、標本数予算を従来どおり検査する。
TEでは元の独立FEM場のEφを評価し、sqrt(r/max(r))*sqrt(detJ/max(detJ))を掛ける。
方位角を変えない子午面の写像なので、方位成分Eφをスカラーとして引き戻す。
可変体積要素r detJは保持し、各側の定数はモード正規化で消える。
TEをHφとして読み替えない。TMの比較文書・場・scopeは維持する。

対応範囲は直接計算した閉PEC・軸境界の曲線P2 TE。
TE/TM混在、通常の非曲線解、鏡映結果、対称境界を拒否する。
対称曲線とその鏡映、曲線TE tune接続、独立実個別ID回復例は後続課題として保持する。
比較写像の成立を連続モード枝やFEM精度の証明と扱わない。

新テストは非対称な曲線変形、独立細分したsolver接続、保存再生とCSV改変拒否、
TE/TM拒否、試験場v=1/Eφ=rの独立P2基底とdblquad積分、比較版3/4/5、
原寸/倍寸の周波数・G・U・Q0・Eφ/Hr/Hz尺度、加速量N/Aを検査する。
試験場は電磁固有モードとは呼ばない。版3/4の非アフィン例は境界上のパラメーター位置が
変わるためordered_curve_verticesを宣言する。

初期baselineは旧型制限で失敗。追加検査で通常SolutionのCase属性参照順の不具合を修正し、
型検査を先に置いた。曲線写像・FEM/RF核・物理許容差は変更していない。
証拠はignored out/te-curved-tracking-20260915。新しい外部資料・依存・旧実装資産は使用していない。

共通参照分割の版4/5は幾何専用_prepareへallow_te=Trueを渡す。
選択領域転送の既定値はFalseで、未検証のworkflow対応を広げない。

検証は分割実行。初期新3件6.883秒PASS、関連33件44.634秒は31成功/2error。
型検査順と境界方式を訂正後の12件41.246秒は11成功、版4のTM限定入口で1error。
その入口を上記のとおり接続後、該当テストとoverlay/reference/selection transferの22件10.780秒PASS。
別のcorrespondence/overlay/partition tuning18件41.317秒もPASS。
各失敗は後続で解消したが、単一の全件PASSとは記録しない。許容差変更なし。
最終ソースで旧TM partition checkpoint完全再生を確認する。新FEMは不要。
全suite/seed/GUIは再実行せず、hosted CIは観測していない。曲線TE tuneの受入は次工程。
