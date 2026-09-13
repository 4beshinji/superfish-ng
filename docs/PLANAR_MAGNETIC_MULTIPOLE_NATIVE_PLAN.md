# S05: 多極抽出結果の保存・元native照合・CLI

2026-09-13 JST。後続限定課題。[実装記録](PLANAR_MAGNETIC_MULTIPOLE_NATIVE.md)の専用API範囲で限定受入。

受け入れ済みの平面線形磁場nativeを入力とし、frame・最大次数・角度標本数を厳密JSONで指定する。元nativeの全5ファイルのSHA256と元FEM抽出の全4系列・係数・診断を、一つの完了したJSON報告へ保存する。元nativeを複製して別の解として出版せず、読み取り専用の出典として明示する。再検証時は元nativeを明示的に指定し、全ファイルの一致、FEM再求解、多極再抽出と全JSONの一致を確認する。報告単体をFEM精度認証と扱わない。

CLIはextract-planar-magnetic-multipoles RUN --request REQUEST --out REPORT、およびreplay-planar-magnetic-multipoles RUN REPORT。成功0、不正入力/改変/出典不一致2。保存先はnative外部、上書き不可。一時ファイルから完了JSONへ出版し、途中失敗で最終報告を残さない。出典・報告のシンボリックリンク、途中変更、ハッシュのみ更新した物理/規約/元標本の改変を拒否する。出典を変更しない。

受入は厳密P1/P2双極・P2四極とP1細分の実FEM、回転/尺度/Az基準、元係数/四系列の保持、改変/型/未定義場/出典差/上書き/途中変更・出版中断を含む。API/CLI報告の全JSONとバイト一致、再検証結果一致、元native全ファイル不変、既存capabilitiesとの整合を確認する。標準検証と既存の周波数/RF差を確認して専用API/CLIのみ限定受入する。GUI・材料拡張・力/トルクは後続工程。
