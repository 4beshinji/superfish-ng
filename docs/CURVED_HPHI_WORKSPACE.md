# 明示曲線HφのProject・表示・独立掃引

2026-09-13 JST：[受入計画](CURVED_HPHI_WORKSPACE_PLAN.md)に沿う別候補
`/tmp/superfish-curved-hphi-workspace-20260913`の固定候補656sourceを主662sourceへ統合し、本書の範囲で限定受入。

HphiProject version 1へ専用curved caseを接続した。二次幾何・軸経路・規格化を完全定義で保持し、
共通native入口から専用の全幾何/FEM/RF再生を呼ぶ。実worker・取込・取消・再起動と
既存のProject/Study/GUI保存処理を接続し、既存の形式と保存内容を保持する。

曲線表示は各元参照三角形を64分割し、元P1/P2場を写像した参照重心で評価する。
各小領域の3頂点と3中点から二次Bezier境界を構成し、曲線パッチで色を塗る。
P1の場でも二次の物理幾何を保持し、元セルに含まれない穴を描画しない。
メッシュ表示は元の二次辺。描画点数の上限は250000で、超過時はSIプローブを案内する。
色は片側の元場の標本であり、連続場の表面ピーク・離散化精度・RF積分へ流用しない。
PNGメタデータは曲線境界、参照分割、標本位置と元native hashを明記する。
全18成分E/H/BのCSVは元逆写像を使い、軸・穴・SI・phasorの既存規約を保つ。

独立Studyは一様尺度、全3D蓄積エネルギー、壁導電率を接続した。
一様尺度は元頂点・全中点・外周/穴の宣言点・軸区間/位相原点を同じ倍率で変換する。
円筒寸法による曲線メッシュの書換えは拒否する。順位にモード追跡の同一性を付けない。
曲線の細分差診断・場比較/射影・スペクトル比較・追跡は未実装として入力段階で拒否し、
GUIの直線用追跡候補から曲線結果を除外する。

実装前は同じ曲線解をProjectが拒否し、表示が直線用mesh属性を読んで失敗することを確認した。
追加5unitは36.670秒、関連32unitは56.855秒（31合格、ローカルHTTP環境1skip）でPASS。
独立12ケース（軸あり/なし、穴0/1/2、P1/P2、R=r+2r²・Z=z−r²）は319.164秒でPASS。
実Project worker12、Study worker12/24 FEM点、所有取込24、再起動12、取消1、CLI36を実行した。
描画Bezierそのものの境界積分を変換した長方形の解析面積・半径一次モーメントと照合し、
全穴を引いた最大相対差4.663e-15を確認した。尺度則の最大相対差3.486e-14。
元300nativeファイルと12Projectは不変で、GUI/CLI/元保存先移動後のPNG/CSVはbyte一致した。
実Chromeの曲線入力・単位・軸・場・native取得・Study・URL復元18操作もPASS。

独立検証後、任意Matplotlibなしの表示テストがskipせず失敗することをimport遮断で再現し、
同テストにskipを追加した。製品コード・独立検証器は不変。修正前後の失敗/skip証拠を保持する。
最初の標準回帰27730は意図的に停止（終了143）し、合格には数えない。
最終固定候補656sourceの標準1104件は`out/validation-curved-hphi-workspace-final-20260913`へ終了0。
最初の独立報告は修正前テストを含むsource hashを保持し、差はこのテスト2行だけと記録した。

証拠はignored `out/curved-hphi-workspace-development-20260913`、
`out/curved-hphi-workspace-independent-20260913`、`out/curved-hphi-workspace-browser-20260913`。
内部source tarは検証時点の記録であり配布用パッケージではない。
新規依存・外部資料・旧版ソース/実行参照なし。一般の形状写像・曲線追跡・旧版照合と全計画は未完。

復元Chrome8、旧Hφ8、旧TM/TE/平面5もPASSし、新規18と合わせて39操作を確認した。
保存artifact照合は17ジョブ（16complete・1cancelled）、元80native不変、移動元2件、6CLIでPASS（11.905秒）。
曲線PNG/CSVは新/復元ChromeとCLIで一致し、旧同軸PNG/CSVも受入済みの曲線追加前とbyte一致した。
検証器の旧workspace参照とartifactのimport名を修正し、初回の失敗記録と修正後のPASSを保持した。製品ソースの変更はない。
全ブラウザー/GUIサーバーは停止済み。標準回帰93189も終了0。

標準1104件（1101合格・3skip）は2210.902秒、ResourceWarningなしでPASS。
skipは任意NGSolve参照2件とsandboxの既存HTTP待受1件。実Chromeの39操作は別に合格した。
主5unitは27.937秒、主12ケース/24Study FEMは308.111秒、主17保存ジョブ/6CLIは11.887秒でPASS。
候補656sourceと主662source（不変egg-info 6件）の一致を確認した。
旧seed9モード19量はf差0、最大相対差8.882e-16。ベンチマークと数値しきい値は不変。
統合証拠はout/validation-curved-hphi-workspace-final-20260913/seed_regression.json。
