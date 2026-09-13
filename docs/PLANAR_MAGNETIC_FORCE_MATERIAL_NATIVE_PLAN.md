# S05: B-H・反跳材料の力・仮想仕事報告保存・CLI

2026-09-13 JST。後続限定課題。[実装記録](PLANAR_MAGNETIC_FORCE_MATERIAL_NATIVE.md)の専用保存API・CLI範囲で限定受入。

成功した平面B-H P1/反跳P1/P2の5ファイルnativeから、[材料応力](PLANAR_MAGNETIC_FORCE_MATERIALS_PLAN.md)と[材料仮想仕事](PLANAR_MAGNETIC_VIRTUAL_WORK_MATERIALS_PLAN.md)を保存・再計算する。既存の線形報告version 1と全CLI/JSON/バイト互換を維持し、材料報告をversion 2に分ける。元manifestの厳密dispatch、5ファイルSHA、元Case/係数/材料/非線形履歴を固定する。失敗した元nativeを成功した場として扱わない。

要求は既存の厳密version 1を使い、virtual_workは必須nullまたは明示刻み。材料応力のみの場合は仮想仕事を省いた事実を保持する。仮想仕事を指定した場合は専用 `material_planar_magnetic_virtual_work` を実行し、全変位Case・対象の材料方向・構成ポテンシャル/基準・J/Ht仕事・反復履歴・係数SHAを保存する。線形用APIの材料拒否契約は維持する。

材料報告version 2は完了/仮想仕事失敗の状態、元physics/manifest、要求、元SHA、応力version 2、nullまたは仮想仕事version 2、比較結果を保持する。仮想仕事が失敗した場合は例外reportを完全に保存し、成功した応力と完了した差分系列、失敗した符号/刻み/Case・非線形履歴を保持する。失敗した対の比較/差分はnull。完了0、保存された実求解失敗1、不正入力/保存/改変2のCLI終了規約を明示する。

出力は元native外に完了JSONを一時作成し、非上書き公開する。再読込では元nativeを明示し、成功/失敗を含む元FEM/全変位FEMを再実行して完全JSONを比較する。途中の元/要求/報告改変、未知版/物理・単位・材料方向・ポテンシャル・失敗履歴/最後の有効係数の改変、リンク・非通常ファイル、上書きと出力中断を拒否する。

受入はP1/P2・線形極限/非線形B-H/異方性残留磁化、非零電流力と磁気モーメントトルク、仮想仕事あり/null、真の変位先非線形失敗の保存を含める。API/CLIの全JSONとバイト、再読込での同じ失敗再現、元ファイル不変を確認する。標準回帰と旧周波数/RF差、旧線形24報告の完全再現後、専用保存API/CLIのみ限定受入する。GUI・Project/Study受渡し、軸対称、S05全体と全計画は未完。
