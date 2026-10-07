# N06：元Case/sourceと保存全領域の束縛

2026-10-08 JST、`adaptive_efficiency_domain.verify_efficiency_saved_domain` を限定受入する。
[N05固定入力](N05_ADAPTIVE_EFFICIENCY_PLAN.md)・[全点元場](N06_NATIVE_FIELD_LOOKUP.md)・
[全域解析格子](N06_ANALYTIC_REFERENCE_GRIDS.md)の接続に使う幾何leafである。
DOMAIN_VERIFIEDは域だけの判定で、個別ID/精度/予算/収束PASSではない。

元strict adaptive request readerを使い、新しい初期履歴なしの閉PEC/真空/m=0 TM/P2を要求する。
保存前後の全native通常file（CSV/VTK/protocol/completionを含む）をSHAで束縛し、
元strict saved readerでgeometry/fieldsを再構築する。symlinkと異常fileを拒否する。
元例外は伝播し、結果を書き換えたり再solveしたりしない。
曲線はCaseの末尾numerical refinement level/stepsだけを除いて完全元Caseと比較する。
元source mesh全項目の完全一致と、全curve parameterの全P2 Bernstein境界係数を確認する。
元の512eps係数/parameter条件を保ち、解析曲線への再投影を認めない。
直線は完全Caseを保ち、全tag付き境界segmentの双方向被覆を元128eps条件で確認する。
初期meshそのものとの一致も別項目へ保存する。細分済み直線一場だけで初期source ancestryを
確認したとは扱わず、callerへ初回mesh/実nested parent trackingの別検査を要求する。
reflected source sectorをこの全領域経路へ混ぜない。
physical_error_bound=null、individual_mode_identity_status=NOT_CHECKEDを維持する。

## 独立の失敗不変量と実検査

先に同じ球の解析曲線を保ちながらchord partitionを変える二native spaceを構成した。
全P2境界一致の独立不変量が元境界比較器で失敗することを再現した（新FEM0）。
正しい二入力は解析曲線が同じでも完全Case/chord条件は異なる。
初回のCase変更でderived contourを残した失敗と、細かいsourceを元Case polygonへ
混ぜた失敗は元validatorが拒否し、元logを保全した。正しい各Caseから各spaceを構成し、
全P2境界の失敗を確認してから新保存域validatorを実装した。数値許容差の変更はない。

未実装ImportErrorを保存し、新5個別unitは2.248秒・終了0/PASS。
実球の初回/uniform一回、実円筒の初回/全marked一回を保存/再構築し、
完全Case/source、全tag境界/P2係数、元係数array不変、全native file不変を確認した。
球の同じ境界でもtriangles順を変えた正当な初期meshを指定すると、元source不一致で拒否する。
同じ解析球の細かいchord Caseは実求解/保存readerには正当だが、元Case/全P2域として拒否する。
未対応TE/linked sourceはnative reader前に拒否し、再構築後のaxis CSV変異も終端SHAで検出する。
新開発FEMは6回、N06計23回で、12独立benchmarkへ数えない。

主uv/BLAS1/明示PYTHONPATH、standard unittestを一度実行。
元1423対象源は全byte不変、新1425対象/1218 Python源、N06計59個別unit。
新seed/full/12benchmark/legacyは0。元1405源のN03 fullを追加源へ昇格しない。
rawは `out/n06-cost-recording-20261007/domain-*.log` と `domain-leaf-acceptance.json`。
参照bundle/actual ID/段階費用のworker接続と12実行は後続。
N06・N04・親G03・原32要件/全goalは継続する。
