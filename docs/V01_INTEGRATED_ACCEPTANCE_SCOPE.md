# V01：統合受入の対象環境・業務・必要証拠

2026-10-07、V01仕様カード。先行B03の原32要件と必須/後続/未確認の分類を維持する。
本書はV02〜V05の検証対象を固定する仕様であり、配布/全互換/利用者評価の合格ではない。
原123カードと全goalを維持し、未確認を対象外へ変えない。

## 対象環境と未決の選択肢

現行READMEの主対象Linuxと、この実機Linux x86_64をリリース候補の第一環境にする。
今回読取で確認した環境はLinux 6.8.0-142-generic/glibc 2.39、Python 3.12.3、
NumPy 2.5.2、SciPy 1.18.1。`.python-version` とuv環境を用いる。
pyprojectのPython>=3.10宣言はその全版の実測合格を意味しない。
V02は候補commitの新規uv環境を用い、解決版/lock相当の全版と実行OSを保存する。
既存`.venv`をそのまま持ち込んだ成功を新規インストール検証へ数えない。

追加OSの必要性は未決。選択肢は「Linux実機を必須とし他OSは後続候補」、
「Linux＋Windowsを必須」、「Linux＋Windows＋macOSを必須」。
未決のままLinux成功を全OS合格や追加OS不要の決定にしない。
Windows/macOS、Python 3.10/3.11等は各OS/版で同じ必須受入を実測するまでUNVERIFIED。
GPU利用は既存必須条件ではなく、今回の候補はCPU solveである。

中核はNumPy/SciPy、可視化Matplotlibは任意。builtin HTTP/ブラウザーGUIも製品導線に含む。
独立参照cavsim2d/NGSolve/Netgenは隔離環境と別成果物にし、製品依存に加えない。
solve時のネットワーク/外部サービスを要求しない。
依存版・ライセンス・再配布条件は [依存記録](DEPENDENCIES.md) とNOTICEで照合する。
ラッパーのライセンスで参照solverを再ライセンスしない。

## 原要件とF/I/O/N/Wの検証経路

Fは物理/機能、Iは厳密入力、Oは規約付き保存/出力、Nは独立参照/収束、Wは利用操作。
各軸は別にPASS/FAIL/UNVERIFIED、N/Aは適用しない根拠がある場合だけ。
元32行の詳細は [B03全行表](development-plan/B03-required-scope.md) と
[互換台帳](COMPATIBILITY_BASELINE.md) を規範とする。以下は統合の証拠経路であり合格表ではない。

| 原K | 製品側の検査・再利用証拠 | 追加の必須照合/環境 |
| --- | --- | --- |
| K01/K02/K03/K05/K19 | `test_legacy_input`、conics/curved_contourの独立幾何、LEGACY_INPUTの限定AF記録 | C01〜C03の版別NT=2/3/省略/枝・全寸法/保存量。根拠不足は変換拒否/UNVERIFIED。LinuxのNG等価計算と対象版の旧動作を分離 |
| K04/K11 | Hφの真空/内導体専用validator、CURVED_HPHI_ACCEPTANCE | H18/C07-hphiの旧内導体/TEM/端条件と独立場。隔離Wine対象版＋LinuxのNG |
| K06/K15 | N01〜N03の元場/RF/幾何系列、`validate_geometry_surface_convergence.py`、N05比較仕様 | N04/N06〜N08の一般精度・費用・失敗/特異性監査。Linux、独立現代参照は別環境 |
| K07 | `compare_superfish.py`、SUPERFISH_COMPARISON、全域探索の専用証拠 | C07-TM/C08。元TM集約raw欠落を解決し対象範囲/実モードを追跡。Wineを実行/保存した版だけ受入 |
| K08 | strict Case/境界タグ・反射/parityの個別tests | C01〜C03/C07の対象版一般境界/半領域。NGの正則条件と旧境界番号を別に検証 |
| K09 | `validate_te_convergence.py`、`validate_te_tracking.py`、STRAIGHT_TE_TUNING_ACCEPTANCE | D04/C07-TEの一般形状/材料/AF。加速量N/A、全壁loss・単位/相補場を別確認 |
| K10 | PLANAR_CURVED_ACCEPTANCE、PLANAR_CURVED_TRACKING_TUNING_ACCEPTANCE、`validate_planar_curved_independent.py` | P10/C07-planar。旧Cartesian偏極・J/m/W/m・全二次領域の実比較が未確認 |
| K12 | MATERIAL_HPHI_ACCEPTANCE、MATERIAL_HPHI_TUNING_ACCEPTANCE、`validate_material_hphi_rf.py` | H17/H18/C07-material。固定実数材料と未決追加損失を分離。旧モデル採否を推定しない |
| K13/K14/K16/K20 | RF定義・保存reader、typed probe/CSVの個別tests、INPUT_OUTPUT | C04〜C06の利用先別ヘッダー/列/桁/符号/単位/標本契約と専用検証、C07/C08の旧テキスト照合 |
| K17 | 個別ID・順位交換・縮退・保存再生のHφ/TE/planar専用証拠、各CLI-worker/GUI | D04/H18/P09等の元要件監査。複数物理のmode indexをIDと扱わない |
| K18 | RF_OPTIMIZATION、D05/D06/D09の専用証拠 | D07〜D11の制約/独立最終/保存操作、L01/L04の旧tuner用途。目的改善だけでは合格しない |
| K21 | テキスト移行先行のC04〜C06/L05仕様 | バイナリbyte互換の必要性/仕様は未確認。非公開binary解析で補完しない。単独NのN/A理由を保持 |
| K22 | 既存CLI/Python/GUIの元場表示・中止/再開・再起動・受渡し記録 | S07/V04の全必須業務を利用者入力から完結。ブラウザー自動検査と本人評価を分離 |
| K23 | `test_package`/`test_save_completion`、LOCAL_DISTRIBUTION_20260909、INPUT_OUTPUT | S07/V02の新規環境・旧保存移行・全追加物理の新規solve/元場再生、V03の固定commit全validate |
| K24 | `validate_electrostatic_solve.py`、静的Project/Jobs/Study/GUI証拠 | S01/S06/C07-staticの旧電極/源/単位/境界の専用照合 |
| K25 | `validate_planar_magnetostatic_solve.py`、元ポテンシャル/電流の独立検査 | S02/S06/C07-staticの対象版規約・外部境界 |
| K26 | `validate_planar_bh_solve.py`、BH失敗/保存検査 | S04/S06/C07-staticの補間/外挿・追加則採否 |
| K27 | `validate_planar_recoil_solve.py`、反跳材料/元場の独立検査 | S03/S06/C07-staticの方向/構成則、追加異方性は未確認 |
| K28 | `validate_planar_magnetic_force.py`、multipole/材料virtual workの専用検査 | S05/S06/L02〜L04の旧多極/力/トルク規約と必要範囲 |
| K29/K30 | B02版別調査とL01〜L05の採否/業務仕様 | 調査必須。未確認のtuner/磁石最適化/熱を架空の製品合格やN/Aへ変えない |
| K31 | L06/L07の寸法/境界/利用権/不確かさ付き実機資料 | 資料と測定比較が必要。N01合成形状は実機資料の代用ではない |
| K32 | 元X01別計画の分類を維持 | 新たな除外ではない。必要性が変更されたらL05で別作業票へ展開 |

表の製品validatorはLinux/uvで実行する。旧入力/出力/仕様の比較は許可済みblack-boxだけで、
legacy solver源/バイナリを取得・読解・複製しない。raw旧結果はignored outに保つ。
未作成のC/S/L専用比較は担当カードで入力/期待量/単位/失敗条件を確定してから作成する。
既存modern validatorだけを旧版互換の合格に数えない。

再利用は、対象Case/完全物理・境界/規格化/量/許容差/元場・ソース/参照byte・終端状態を
今回の候補へ対応付ける。ソース差の影響が未解決なら元のPASSを昇格しない。
失敗/費用/skip理由を保全し、partial/seedをfullや全追加物理の受入と呼ばない。
V03は依存受入後の固定commitで全validateを一度実行し、seedのfと全RFを別に比較する。
今回のN03全validate handle72074はその節目の証拠であり、V03実施済みではない。
hosted CIは実際のrunを観測した場合だけ記録する。

## 業務・保存移行・配布の境界

V04の業務は、入力/形状編集→物理選択/求解→元場/RF/独立確認→実ID追跡→
寸法調整/制約探索→中止/再開/再起動→保存受渡し/再検証・probe/CSV利用、を物理別に記録する。
各業務に入力、期待単位/対象ID、出力、未達表示、失敗からの戻り方を付ける。
未決の実業務範囲の選択肢は「現在のRF/静的CLIとGUI受渡し」、
「指定した旧後処理へのCSV/テキスト受渡しを追加」、「実機設計/追加tuner/熱の業務を追加」。
原必須機能はどの選択肢でも保持し、追加利用先の期待列を推測しない。
本人操作評価が必要で未実施なら、自動UIログを渡して未実施を明示する。

V02の移行対象はINPUT_OUTPUTで公開済みのCase/Project/native/Study/追跡/調整/探索/
adaptive/Job保存の各版。型・全byte/completion・元規約を各専用readerで完全再生する。
旧版readerの拒否/未対応、非完了保存、改変、移動/祖先欠落を確認する。
バージョン番号を付け替えて意味を変えたり、旧原場を新solveとして再保存したりしない。
異なる物理のJとJ/m、WとW/m、N/Aをalias化しない。

候補配布物は現行 `scripts/package.py` のallowlistとwheel設定を使い、
新規出力のZIP/manifest/wheelをV02で内容検査・新規インストールする。
src/docs/examples/scripts/tests/benchmarks等の選択境界、全LICENSE/NOTICE・依存条件を照合する。
ユーザー所有SUPERFISH/.wine-superfish/archives/セミナーPDF/解説/legacy launcher、
out/.venv/.git・隔離参照solver・元旧結果を混入させない。
symlink拒否、SHA/CRCと完全性を検査する。署名付き公開リリースやclean-room認証とは呼ばない。

今回の受入は対象/証拠/未決選択肢の仕様のみ。新unit/FEM/seed/full/配布実行0。
V02/V03/V04/V05、元OS/実業務の未決、原32要件の個別受入と全goalは継続する。
