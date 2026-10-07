# N06：既存呼出しの段階費用観測

2026-10-07、N06の計測接続だけを別ツリーで限定受入。
先行の[費用記録器](N06_EFFICIENCY_TIMING.md)は変更していない。
主N03の全検証1405対象ファイルを固定し、N06の実FEM接続/12比較は後続とする。

`adaptive_efficiency_observation.observe_selected_calls` は新しいserial worker内で、
明示したmodule・属性・stage名の呼出しをPhaseRecorderで囲む。
元関数へ同じ引数を渡し、同じ返り値object/元例外を返す。
関数body・FEM/RF/固有値コード・永続科学データを書き換えない。
入れ子の費用は既存記録器のexclusive配分で二重加算しない。
観測自体のoverheadも壁時計に含まれ、推定して差し引かない。

全bindingを変更前に検証する。重複、存在しない/非callable属性、
同一関数の別名に異なるstage名、二重observerを拒否する。
部分的な登録失敗でも先に登録した属性を復元し、元例外を再送出する。
正常/元solver失敗のどちらでも逆順で元bindingを復元する。
外からbindingが置換された場合はその変更を上書きせず、正常closureならエラー、
元例外がある場合はその例外を保ち、対応Pythonではnoteに衝突を残す。
このcontextはfresh worker/元thread内だけの計測用で、共有実行サービスへ適用しない。
未列挙のaliasや関数を自動計測したと主張しない。

未実装moduleのImportErrorをbaselineとして保存。
新5個別unitは0.001秒・終了0/PASS。
独立時計0→10秒の実入れ子callで親7秒/子3秒、exclusive4/3秒、未配賦3秒を確認。
引数/keyword/返り値のobject identity、元例外objectのidentityとbinding復元、
不正末尾bindingの変更前拒否、外の置換保全/二重観測拒否、部分登録失敗の復元を確認した。
これらは費用配分と関数接続の検査であり、物理精度の検査ではない。

tempの明示PYTHONPATHとmainのuv環境で
`python -m unittest -v test_adaptive_efficiency_observation` を実行した。
元1200源と既受入六源は不変、temp1208 Python源/全1409点（主生成egg-info六点なし）。
mainの全1405対象源は不変。既存7/10/5unitと参照準備の証拠を再実行せず再利用した。
rawは `out/n06-cost-recording-20261007/call-observation-*.log` と
`call-observation-acceptance.json`。新FEM/seed/full/GUI/12benchmarkは0。

実workerにsolver/組立/固有値/mesh・細分/追跡/求積/RF/peak/保存/再構築の
元aliasを列挙し、未配賦とinline規格化などの残余費用を正確に名付ける工程は後続。
計測接続の限定受入でN06・親N04・全goalを閉じない。
