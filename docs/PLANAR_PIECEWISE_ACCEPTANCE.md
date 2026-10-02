# 平面区分比較・調整の条件別監査（P04受入）

2026-10-02。原P04の実装範囲は、P03の連続区分アフィン宣言を使う元TE/TM場の比較と、
元頂点の有限多項式変位法則による調整、所有履歴/再開/GUI接続。
滑らかな曲線のP2幾何/非線形写像は後続P05〜P09。P04の部分合格を原親P02/D02の完了にはしない。

| 原P04の条件 | 専用証拠と成立範囲 |
| --- | --- |
| 元TE/TM場を各実点写像で比較 | [P04-a](PLANAR_PIECEWISE_TRACKING.md)：有理数共同分割、全元nativeセル被覆、TEのadjugate移送/TM scalar合成、独立多項式/curl積分 |
| 相似極限の解析一致 | P04-aの実TE/TM f・元場・U′/RF、[形状子a](PLANAR_PIECEWISE_SHAPE.md)の相似法則、[実調整子b](PLANAR_PIECEWISE_TUNING_SAVED.md)の独立解析尺度/全RF |
| 非アフィン合成形状の独立細分 | P04-aの独立3×4/5×3元メッシュ、子bのTE/TM cutoffと独立細分。粗いG/iteration limit未達と適切な細分後PASSを区別し、許容差を維持 |
| 元Projectの形状法則・全試行の実FEM | 子aの元mesh/閉区間Jacobian・全域接触/丸め拒否、子bの元Projectからの検索/最終細分、FEM native物理再生。解析式をsolverに代用しない |
| 未確認群を評価しない | 子b/workerのguard/true縮退と周波数null、[調整GUI](PLANAR_PIECEWISE_TUNING_GUI.md)の実UNVERIFIED取込/再開無効。既知IDのみ周波数/目標評価 |
| 追跡履歴へ接続 | P04-aの所有pair/履歴/CLI-worker・元移動後再生、[新版追跡GUI](PLANAR_PIECEWISE_TRACKING_GUI.md)の9→10→細分10とID集合引継ぎ。隣接native/群/順序を完全照合 |
| 再開・保存再生一致 | 子bの可搬な全試行所有/移動後CLI再生、[worker子c](PLANAR_PIECEWISE_TUNING_WORKER.md)の投入時祖先所有/実中止/管理器再作成/別job。要求・判断・Project・全native/RFを保持 |
| 旧平面調整版を保持 | 子bの旧版1〜3直接消費先14件、worker直接消費先12件、GUI旧5件と実Chrome旧アフィン5項目。新旧保存意味を区別して検証 |
| 新要求・GUIとAPI一致 | 調整GUIの要求4/独立API4試行/全50配列・Project/要求/判断/RF、追跡GUIの版1〜10フォーム/strict輸送/所有履歴/独立API比較。追跡側は独立API3pairの全結果/所有履歴と70配列・全RF/最終Project一致、表示修正/新サーバー復元もPASS |

数値証拠は各専用文書の分割実行を再利用する。一度の全suite/全validate成功とは報告しない。
P04-aは57種類、形状子aは初回非影響12/再検査17、実調整子bは22、worker子cは17種類、
調整GUIはPython6/実Chrome20項目。重複した直接消費先を総テスト数に足し合わせない。
新旧コード経路と実装hashを各証拠に束縛し、GUIだけの変更でFEM証拠を再実行しない。
canonical seed、物理許容差、SI/peak phasor、二つのR/Q定義に変更なし。

本監査は独立実装の科学的範囲を示す。公開版の全互換・測定構造・certified clean-roomを主張しない。
新外部資料/依存/legacy参照なし。全操作/所有照合/表示/資源回収を確認し、開発カードP04-c/P04をDONEにする。原互換親P02/D02、H17/H18と後続P05〜P09は未完了のまま。
