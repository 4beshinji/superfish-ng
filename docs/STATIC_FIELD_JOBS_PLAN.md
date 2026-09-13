# O02: 静的Projectの実worker・成功/非線形失敗保存・CLI

2026-09-13 JST。[実装記録](STATIC_FIELD_JOBS.md)の専用worker/API/CLI範囲を限定受入。[専用Project入力契約](STATIC_FIELD_PROJECT_PLAN.md)に続く[O02](COMPATIBILITY_PLAN.md)の工程。

受入済み11種類の静的CaseをStaticFieldProjectから同じ専用FEMへ渡す。新しい数値ソルバーは作らない。JobManagerの専用kind、所有Project、別プロセスでの求解、既存nativeの成功5ファイルとB-H失敗3ファイル、実装来歴と完了manifestを接続する。SI、全領域/材料/境界、求積次数、初期値と全非線形反復履歴を保つ。

求解成功、再現可能な非線形求解失敗、不正入力/保存/worker中断を区別する。非線形失敗を正常な場やゼロへ変換しない。失敗nativeは既存の専用replayで実際の失敗と全履歴を照合し、一般のJob完了は求解成功だけに使う。CLI solve-static-projectとreplay-static-projectは成功0、検証済みの非線形失敗1、不正/未完/IOエラー2を返す。描画・GUI編集・Studyは後続とする。

受入条件は全11形式/対応P1/P2のAPI・実worker・CLIと元nativeの全Case/結果一致、B-Hの3座標系で実失敗/初期値/履歴の一致、表示単位の保持、完了後と管理再起動後の再読込。Project/native/manifestの改変、kind除去、リンク、上書き、途中の入力/実装変更、保存途中の例外、二重worker、中止/強制終了を検査する。未完のJobや失敗場を有効な成功結果として公開しない。既存RFと磁気報告Jobの意味を保持する。

独立検証では既存の解析・物理不変量で受入済みの成功/実失敗Caseを使用し、元FEM結果をProject経由で再現する。参照出力を変更しない。標準回帰では周波数とRF量を別確認し、許容差・ベンチマークを変更しない。新規依存、旧版コード参照、solve時の外部接続は導入しない。これをO02親や全計画の完了とは扱わない。
