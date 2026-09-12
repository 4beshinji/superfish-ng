# 実装済み能力表の整合

2026-09-13 JST：[計画](CAPABILITY_INVENTORY_PLAN.md)の別候補
`/tmp/superfish-capability-inventory-20260913`の固定候補659sourceを主665sourceへ統合し、本書の範囲で限定受入。

`capabilities`へ専用Hφの4形式を追加した。case/native/resultの形式と版、P1/P2、
軸の有無、q/uと静的零空間、軸加速量のN/A、全3D単位と位相、実CLIを明記する。
Project/GUI/worker、独立Study、直線だけの場比較・細分差診断・追跡・所有履歴を区別した。
曲線の比較・追跡、材料、静的場を利用可能にはしない。能力表は記述用で、受理するパーサーを変更しない。

平面追跡の版1〜7と各写像を列挙した。版5/6の境界点列の一致要件と、
版7の有理数評価による独立境界分割を区別する。既存キーとcanonical Modelは保持する。

実装前、実パーサーが追跡版7を受理するのに一覧にはなく、Hφ全体も欠落していたことを確認した。
追加3unitは5.987秒、関連11unitは6.221秒でPASS。
実際の5種のHφ例（曲線の軸あり/なしを分離）でAPI・専用CLI・Projectのnative5をbyte比較した。
宣言した38コマンドのhelpを含む59CLI、75nativeファイル不変と全18成分プローブを確認し、16.070秒でPASS。
独立検証器の初回は旧プローブにcase本体が入っていると仮定して失敗した。元native5のhashとの照合へ直し、
旧出力形式を変更せず、元場の値も照合して再検証した。初回の失敗ログを保持する。

標準1107件は`out/validation-capability-inventory-candidate-20260913`へ終了0。
主ツリー統合、最終標準と主ツリーの対応照合も完了。
証拠は`out/capability-inventory-development-20260913`と`out/capability-inventory-independent-retry-20260913`。
新しい数値方式・依存・外部資料・旧版参照なし。親課題の完了数と全計画の未完状態を保持する。

標準1107件（1104合格・任意NGSolve2/HTTP環境1skip）は2221.826秒、ResourceWarningなしでPASS。
主3unitは5.787秒、主5例/59CLIは16.020秒でPASS。候補659と主665source（不変egg-info6件）を照合。
旧seed9モード19量はf差0、最大相対差8.882e-16。ベンチマーク不変。統合証拠はout/validation-capability-inventory-candidate-20260913/seed_regression.json。
