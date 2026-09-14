# 曲線TEの固定RFメタデータによる形状調整

2026-09-15、開始HEAD `f7c9e9e`。曲線TE追跡から、実形状変形とtuneへの接続を進める。
本書は検証中の実装記録であり、全計画またはD02全体の受入を宣言しない。

要求版5の多項式と版7のcurved_harmonic式で、直接計算する閉PEC/軸境界のP2 TE形状を扱う。
曲線の幾何パラメーターから境界節点を移し、内部の調和変位を求め、元の凍結した細分履歴を保持する。
比較には実試行ごとの二次写像とEφ・可変体積重みを用いる。最終細分は同じ二次領域を制限する。

TEは軸方向加速場を持たないため、rf_coordinatesはfixedのみとする。
形状変形時にactive_length/voltage_interval/phase_originを追加せず、元のRFメタデータを保持する。
従来TMのfixed/axis_fraction処理は維持する。幾何のみを生成するcurved_harmonic Studyも同契約を使用する。
境界、Jacobian、辺交差、品質、細分予算を緩和しない。

版4のaffine_remesh、版8の分割切替、曲線対称面/鏡映、実個別ID回復例は後続課題。
既存の成功した直線profile・曲線比較の検証を、新しいtuneの数値受入へ読み替えない。

新規検査：多項式の曲線TE調整は2試行で停止して再開し、TUNEDと最終細分、
全試行の加速量N/A・TE追跡・保存再生を確認。式入力とStudyの生成形状も確認する。
最初の2件153.667秒は多項式側が成功、式側が試験変数名の不一致でエラー。
要求パラメーターを式と同じxに訂正し、当該1件34.140秒PASS。
独立Green積分の面積・体積尺度1件3.982秒PASS。許容差変更なし。
専用TE Studyは2実FEMで完了し、read_jobと両R/QのN/Aを確認した。
これらは分割検証であり、単一実行の全件成功とは記録しない。

証拠はignored out/te-curved-tuning-20260915のbaseline/new-tests/expression-fixed/green-test.log、
te-study-validation.jsonと2点のnative保存。新たな外部資料・依存・旧実装資産は使用していない。
GUI用要求はこの保存Studyの同じ形状の周波数を目標として作成済み。
同一FEMによる目標設定は実行経路の検査であり、独立解析精度の証明ではない。
実GUIと追加の場/RF尺度検証は未実施。full suite/seed/hosted CIも実行していない。

関連検証はcurved_harmonic_deformation、curved_harmonic_study、curved_harmonic_tuning、
expression_tuning、te_tuning、TEJobの未接続workflow拒否で34件482.550秒PASS。
全検証プロセスは終了。API接続の検証を記録し、実GUI・追加場/RF尺度検証を次工程として残す。
GUIの旧未対応説明も次の実検証に合わせて更新する。計画全体のゴールは継続中。
