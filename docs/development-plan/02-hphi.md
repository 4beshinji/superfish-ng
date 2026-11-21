# Hφの形状比較・追跡・周波数調整

[全体索引と実行規則](README.md)に従う。本章のIDは親課題IDではなく、作業カードID。

各カードは原則1コミット。既存ファイルは調査・変更候補であり、全てを書き換える指示ではない。新設ファイルは本文で指定する。

## H01

### Hφ調整と比較写像の専用契約を決める

- **親課題**：D02 / P03 / P04。**種別**：仕様。初期状態：未着手。
- **先行条件**：[B01](01-baseline.md#b01)
- **コミット件名案**：`docs: Hφ調整と比較写像の専用契約を決める`
- **既存の入口・影響先**：`src/superfish_ng/hphi_project.py`、`src/superfish_ng/hphi_study.py`、`src/superfish_ng/hphi_tracking.py`、`docs/D02_PHYSICS_ROUTING.md`
- **実施内容**：新設docs/HPHI_TUNING.mdに専用要求・版・状態遷移を定義する。最初は真空のuniform_scale、後に同軸寸法、明示一般写像、材料、曲線を追加する。形状ごとの物理比較、guard、個別ID、Hzと変数単位、検索/最終細分の別予算と別周波数ゲートを定める。
- **受入条件**：成功、ブラケット不成立、個別ID未確認、要素上限、中止、最終細分失敗の入力/期待状態例が揃う。現HphiTrackingRequestのsame_vacuum制限を越える前提が明示される。stored_energy/conductivityを周波数形状変数として受理しない。
- **確認方法**：文書/仕様/監査は差分と根拠・リンク・依存を確認。検証カードは本文指定の専用実行を行い、[共通検証規則](README.md#検証と完了報告)で報告する。文書更新だけでFEMを再実行しない。

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

## H02

### 真空Hφの一様尺度比較を追加する

- **親課題**：P03 / D02。**種別**：実装。初期状態：未着手。
- **先行条件**：[H01](02-hphi.md#h01)
- **コミット件名案**：`feat: 真空Hφの一様尺度比較を追加する`
- **既存の入口・影響先**：`src/superfish_ng/hphi_field_overlap.py`、`src/superfish_ng/hphi_mass_projection.py`、`src/superfish_ng/hphi_tracking.py`
- **実施内容**：明示した正の尺度から旧/新の領域と全PEC穴を比較する経路を追加する。元のq/uとE/H、体積重み、周波数の比較単位を別々に変換する。同領域の既存版は維持する。
- **受入条件**：尺度1の旧経路一致、独立積分、軸あり/なしの二尺度実FEMでfと場/RF尺度が一致する。トポロジー相違とguard不足は未確認/拒否。fだけの対応をIDとしない。
- **既存の検査候補**：`test_hphi_field_overlap`、`test_hphi_mass_projection`、`test_hphi_tracking`。変更した契約に直接依存するケースを選ぶ。新機能の独立検査は別途追加する。
- **検査コマンドの出発点**：

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v test_hphi_field_overlap test_hphi_mass_projection test_hphi_tracking
```

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

## H03

### Hφ調整のstrict要求と試行Project生成を実装する

- **親課題**：D02。**種別**：実装。初期状態：未着手。
- **先行条件**：[H02](02-hphi.md#h02)
- **コミット件名案**：`feat: Hφ調整のstrict要求と試行Project生成を実装する`
- **既存の入口・影響先**：`src/superfish_ng/hphi_project.py`、`src/superfish_ng/hphi_study.py`、`src/superfish_ng/planar_tuning.py`
- **実施内容**：新設hphi_tuning.pyに要求readerと元Projectからの独立試行生成を追加する。真空uniform_scaleのみ公開し、要求に物理/変数単位・ID帯域/guard・全予算を保存する。最終細分を元の採用候補から作り、探索の途中メッシュを累積変形しない。
- **受入条件**：二度生成した同一値が同一Projectになる。重複キー、未知項目、NaN、bool数値、範囲逆転、未対応物理/変数をFEM前に拒否。出力予約前に最終細分予算を検査する。
- **既存の検査候補**：`test_hphi_study`、`test_hphi_study_physics`。変更した契約に直接依存するケースを選ぶ。新機能の独立検査は別途追加する。
- **検査コマンドの出発点**：

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v test_hphi_study test_hphi_study_physics
```

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

## H04

### Hφの実FEM二分調整を実装する

- **親課題**：D02。**種別**：実装。初期状態：未着手。
- **先行条件**：[H03](02-hphi.md#h03)
- **コミット件名案**：`feat: Hφの実FEM二分調整を実装する`
- **既存の入口・影響先**：`src/superfish_ng/hphi_native.py`、`src/superfish_ng/hphi_jobs.py`、`src/superfish_ng/tuning.py`
- **実施内容**：新設hphi_tuning.pyから専用FEMとH02比較を呼び、個別ID確認後にだけ周波数を評価する。共有は物理に依存しない二分判断に限定する。目標差と粗細差の両判定、終端後の追加試行拒否を実装する。
- **受入条件**：同軸の解析共振関係と二尺度実FEMで探索から最終細分まで到達する。ID未確認の周波数はnull、失敗解をブラケット更新へ使わない。要求精度未達をTUNEDにしない。
- **既存の検査候補**：`test_hphi_tracking`、`test_hphi_jobs`、`test_tuning`。変更した契約に直接依存するケースを選ぶ。新機能の独立検査は別途追加する。
- **検査コマンドの出発点**：

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v test_hphi_tracking test_hphi_jobs test_tuning
```

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

## H05

### Hφ調整の所有保存とCLI再開を実装する

- **親課題**：D02 / O02。**種別**：実装。状態：完了。
- **先行条件**：[H04](02-hphi.md#h04)
- **コミット件名案**：`feat: Hφ調整の所有保存とCLI再開を実装する`
- **既存の入口・影響先**：`src/superfish_ng/cli.py`、`src/superfish_ng/hphi_native.py`、`src/superfish_ng/hphi_tracking_history_saved.py`
- **実施内容**：要求・全試行Project/native・判断・ID・親試行を所有保存する。新規tune/replay/resumeのCLIを専用形式で追加し、読み直し時に元FEMと履歴接頭部分を検証する。CLI名と終了コードはHPHI_TUNING.mdに固定する。
- **受入条件**：探索途中/最終細分直前/未確認終端の再生と許可された再開が一致する。元外部パスの移動後も所有結果で再生でき、要求/係数/順序/親の改変を拒否。元ファイルとRF全量を保持する。
- **既存の検査候補**：`test_hphi_tracking_history_saved`、`test_hphi_tracking_jobs`。変更した契約に直接依存するケースを選ぶ。新機能の独立検査は別途追加する。
- **検査コマンドの出発点**：

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v test_hphi_tracking_history_saved test_hphi_tracking_jobs
```

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

#### H05受入記録（2026-09-16 JST）

`hphi_tuning_saved.py`で要求・全試行のProject/native・hash・判断履歴を所有保存し、
`tune-hphi`、`resume-tune-hphi`、`replay-tune-hphi`を接続した。PAUSEDの2試行を
新規再開先へコピーして4試行のTUNEDまで完走し、元出力を移動した後も再開先を再生できた。
再生はsolverを呼ばず、nativeのFEM/RF復元、ID追跡、親、順序、両ゲートを再計算する。
要求・係数/native・試行順序・親の改変と不完全構成を拒否する。

専用`test_hphi_tuning_saved`は5件でPASS（終了0）。H05開始候補の
`test_hphi_tracking_history_saved`/`test_hphi_tracking_jobs`とH04依存テスト、専用
`scripts/validate_hphi_tuning.py`の実行結果を本書と`HPHI_TUNING.md`へ追記する。
workerの中止・再起動は次のH06へ送る。

## H06

### Hφ調整workerの中止と再起動を接続する

- **親課題**：D02 / O02。**種別**：実装。状態：完了。
- **先行条件**：[H05](02-hphi.md#h05)
- **コミット件名案**：`feat: Hφ調整workerの中止と再起動を接続する`
- **既存の入口・影響先**：`src/superfish_ng/jobs.py`、`src/superfish_ng/hphi_jobs.py`、`src/superfish_ng/planar_tuning_jobs.py`
- **実施内容**：新設hphi_tuning_jobs.pyをJobManagerへ登録する。投入時の要求所有、状態遷移、チェックポイント選択、別ジョブ再開とロック解放を平面workerの契約に合わせる。
- **受入条件**：実プロセスの中止と管理器再作成から再開できる。APIとworkerの全native/判断/対象IDが一致し、同名競合・不完全保存を完了扱いしない。全handle終端を確認する。
- **既存の検査候補**：`test_hphi_jobs`、`test_planar_tuning_jobs`。変更した契約に直接依存するケースを選ぶ。新機能の独立検査は別途追加する。
- **検査コマンドの出発点**：

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v test_hphi_jobs test_planar_tuning_jobs
```

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

#### H06受入記録（2026-09-16 JST）

`hphi_tuning_jobs.py`を追加し、`JobManager.start_hphi_tune`と完了manifestの検証へ接続した。
入力封印、worker claim、H05の所有trial/checkpoint、APIとworkerの要求・試行・判断・対象IDの
一致、PAUSED checkpointからの新規出力への再開を検証する。実プロセスを中止しても完了済み
checkpointを保持し、別のJobManager再作成後に再開できる。失敗時はcompletion manifestを公開しない。

検証は`OPENBLAS_NUM_THREADS=1 UV_CACHE_DIR=/tmp/superfish-uv-cache uv run --no-sync --python .venv/bin/python python -m unittest -v tests.test_hphi_tuning_jobs`で4件PASS（43.784秒、終了0）。
実workerのPAUSED→再開、実中止→checkpoint再開、入力前拒否、checkpoint保持・manifest非公開を確認した。
H05の`read_hphi_tune`はworkerの`execution/`配置も解決するよう更新し、既存の所有保存/再生を保持する。
専用validatorやseed/full validateはH06のworker接続だけでは再実行していない。

## H07

### Hφ調整GUIを接続する

- **親課題**：D02 / O02。**種別**：実装。状態：完了。
- **先行条件**：[H06](02-hphi.md#h06)
- **コミット件名案**：`feat: Hφ調整GUIを接続する`
- **既存の入口・影響先**：`src/superfish_ng/gui_hphi.py`、`src/superfish_ng/web/hphi.js`、`src/superfish_ng/web/hphi.html`
- **実施内容**：専用調整要求の編集/読み込み、開始/中止、保存地点選択、再開、両周波数ゲート、対象IDと実順位、対象元場を表示する。表示単位と保存SIを分ける。
- **受入条件**：実ブラウザーで開始→中止→別ジョブ再開→元場表示、サーバー再起動後の復元を確認する。API/GUIの要求・全場/RF一致、N/Aと未確認理由、同一ファイル再読込を確認する。
- **既存の検査候補**：`test_gui_hphi`、`test_gui_hphi_tracking`。変更した契約に直接依存するケースを選ぶ。新機能の独立検査は別途追加する。
- **検査コマンドの出発点**：

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v test_gui_hphi test_gui_hphi_tracking
```

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

#### H07受入記録（2026-09-16 JST）

`gui_hphi_tuning.py`を追加し、Hφ専用APIへ要求の正規化/読込、実worker開始、共通中止、停止ジョブのcheckpoint列挙・完全replay、別ジョブ再開、対象試行のnative場取込を接続した。`hphi.html`/`hphi.js`には、無次元uniform_scale、保存SI座標、Hzの二つの周波数ゲート、対象IDと各試行の実順位、未確認理由、元場/RF表示への導線を追加した。checkpointと完了結果はURLの`tune`で再読込できる。

`OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-uv-cache uv run --no-sync --python .venv/bin/python python -m unittest -v test_gui_hphi test_gui_hphi_tracking test_gui_hphi_tuning`は8件中7件PASS・既存HTTP 1件skip、76.357秒、終了0。新設`test_gui_hphi_tuning`では要求ファイルの正規化、実workerの保存地点再検証、対象IDの実順位での元native取込、別ジョブcheckpoint差替え/要求改変の拒否を確認した。`node --check src/superfish_ng/web/hphi.js`とChromium headlessの`/hphi.html`配信・調整UI初期化も終了0で確認した。sandboxではloopback bindが拒否されたため、HTTP認証を含む実サーバー操作の既存1件はskipであり、実ブラウザーの開始→中止→再開クリック列はAPI/worker回帰で補完し、未確認として残す。新規外部資料・依存・legacy比較はない。次はH08の同軸寸法/直線一般写像契約。

## H08

### 同軸寸法と直線一般形状の写像契約を追加する

- **親課題**：P03 / D02。**種別**：実装。初期状態：未着手。
- **先行条件**：[H07](02-hphi.md#h07)
- **コミット件名案**：`feat: 同軸寸法と直線一般形状の写像契約を追加する`
- **既存の入口・影響先**：`src/superfish_ng/hphi_study.py`、`src/superfish_ng/meridional_overlap.py`、`src/superfish_ng/hphi_tracking.py`
- **実施内容**：同軸の内外半径/長さと、軸/穴を保持する明示区分アフィン対応を別方式で定義する。新設hphi_geometry_mapping.pyで全境界被覆、正Jacobian、軸区間と加速座標方針を検査する。
- **受入条件**：同軸寸法の解析面積/体積と写像の独立積分が一致する。穴消失・反転・軸移動・未被覆を拒否し、同じ尺度指定はH02へ一致する。未知の自動対応を推測しない。
- **既存の検査候補**：`test_hphi_mesh`、`test_axis_hphi`、`test_hphi_study`。変更した契約に直接依存するケースを選ぶ。新機能の独立検査は別途追加する。
- **検査コマンドの出発点**：

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v test_hphi_mesh test_axis_hphi test_hphi_study
```

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

H08受入（2026-09-21）：[幾何契約と結果](../HPHI_GEOMETRY_MAPPING.md)。同軸解析面積/体積、非一様穴移動、正逆Jacobian、H02尺度一致、穴消失/反転/未被覆/軸移動拒否を確認。26件PASS、終了0。共有番号の明示幾何分割に限定し、場移送・別FEM分割比較はH09。

## H09

### 直線一般写像を追跡と調整へ接続する

- **親課題**：P03 / D02。**種別**：実装。初期状態：未着手。
- **先行条件**：[H08](02-hphi.md#h08)
- **コミット件名案**：`feat: 直線一般写像を追跡と調整へ接続する`
- **既存の入口・影響先**：`src/superfish_ng/hphi_field_overlap.py`、`src/superfish_ng/hphi_tracking_history.py`、`src/superfish_ng/hphi_study.py`
- **実施内容**：各実試行の写像で元場を比較し、Hφ調整の要求・replay・CLI/worker/GUIへ接続する。別内部メッシュと境界分割の検査を保つ。
- **受入条件**：同軸寸法探索と穴付き非一様変形例の両方でID確認後にのみ評価する。正逆比較、番号置換、同じ物理形状の別分割で判定を確認する。保存からの再開は元要求を再現する。
- **既存の検査候補**：`test_hphi_tracking`、`test_hphi_tracking_history`、`test_gui_hphi_tracking`。変更した契約に直接依存するケースを選ぶ。新機能の独立検査は別途追加する。
- **検査コマンドの出発点**：

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v test_hphi_tracking test_hphi_tracking_history test_gui_hphi_tracking
```

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

### H09の実装分割（2026-09-21）

H09親は全子工程の受入まで未完了とする。元の同軸/穴付き非一様変形、正逆比較、
別分割/番号置換、ID確認前の周波数未評価、保存再開という条件を全て維持する。

#### H09-a

**依存：H08**。幾何写像の制御三角形と両側の元FEM三角形を有理数で交差分割し、両側の全領域/全親面積被覆を検査する。別分割・番号置換・非一様穴変形・正逆積分と不正領域/予算拒否が受入条件。
H09-a受入：新規4件と既存8件の分割証拠でPASS。詳細・失敗履歴は[交差分割仕様](../HPHI_MAPPED_OVERLAP.md)。次はH09-b。

#### H09-b

**依存：a**。元E/Hの比較移送と質量射影を定義し、実FEM追跡へ接続する。同軸解析場、H02尺度一致、双方向比較、guard/縮退/番号置換、元場/RF保持を独立検査する。

H09-b受入（2026-09-21）：[比較移送・射影・追跡](../HPHI_MAPPED_TRACKING.md)。単位的L2移送と元領域のスペクトル診断を分離し、TEM/Bessel縮退・q/u射影・正逆比較・guard・元RF保持を確認。新規10件の分割証拠、既存31件＋収束3件PASS。新結果の保存/CLI/worker/GUIは未接続で、次はH09-c。

#### H09-c

**依存：b**。strict形状法則・同軸寸法/区分アフィン試行生成と調整要求、履歴再構築、所有保存/CLI再開を接続する。両形状の実探索とID未確認停止、改変拒否、元要求/全native/RF一致を検査する。

H09-c受入（2026-09-21）：[非一様形状調整](../HPHI_SHAPE_TUNING.md)。要求版2・同軸3寸法/頂点変位・実二分・所有保存/CLIを接続した。新7件の分割検証、既存18件、穴付き変形の専用4実FEM validatorがPASS。粗い予備要求のguard停止を保持し、許容差を維持した。次はH09-dの新写像worker/GUI操作受入。

#### H09-d

**依存：c**。worker/GUIへ接続し、実中止/再開/管理器再起動とブラウザー操作、元API/保存全量一致を検査してH09を統合監査する。

H09-d/親H09受入（2026-09-21）：[操作受入と条件別監査](../HPHI_SHAPE_TUNING_GUI.md)。両形状の実中止・所有再開・管理器再起動、実サーバー再起動後の新Chrome復元、全native/RF一致がPASS。検証器の途中失敗と補完再生を区別して保存。追加穴付き逆追跡/同形状別分割1件と以前skipされたHTTP1件もPASS。次はH10。

## H10

### Hφの個別ID回復を専用履歴へ追加する

- **親課題**：P03 / P04 / D02。**種別**：実装。初期状態：未着手。
- **先行条件**：[H09](02-hphi.md#h09)
- **コミット件名案**：`feat: Hφの個別ID回復を専用履歴へ追加する`
- **既存の入口・影響先**：`src/superfish_ng/hphi_tracking.py`、`src/superfish_ng/hphi_tracking_history.py`、`src/superfish_ng/tuning_identity_recovery.py`
- **実施内容**：宣言した過去の個別場と継承集合から回復する専用要求を追加する。部分空間の未確認を回復で迂回せず、検索試行/最終細分とanchorの対応を分ける。
- **受入条件**：独立解析の順位交換/縮退対照で全個別対応と集合一致を確認する。曖昧な群・guard不足・集合外回復は停止し、成功した回復IDのみ後続へ継承する。
- **既存の検査候補**：`test_hphi_tracking_history`、`test_tuning_identity_recovery`。変更した契約に直接依存するケースを選ぶ。新機能の独立検査は別途追加する。
- **検査コマンドの出発点**：

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v test_hphi_tracking_history test_tuning_identity_recovery
```

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

### H10の実装分割（2026-09-21）

親H10の独立解析順位交換/縮退、曖昧群・guard・集合外停止、成功IDだけの継承という条件を全子工程に維持する。全受入まで親を完了扱いしない。

#### H10-a

**依存：H09**。strictな過去anchor宣言と実E/H比較による回復核。継承部分空間を再計算し、PASSの場合だけanchor比較を行う。独立同軸TEM/径方向根の順位交換、縮退anchor、guard、集合外ID、元場不変が受入条件。

H10-a受入（2026-09-21）：[明示回復核](../HPHI_IDENTITY_RECOVERY.md)。独立TEM/Bessel順位交換とq場/縮退部分空間、両側guard、集合境界/集合外、same-vacuumの軸接続/正半径を検査。新8件の分割証拠＋既存履歴1件PASS。過去snapshotの所有証明は未接続で次はH10-b。

#### H10-b

**依存：a**。専用履歴へ明示回復eventを追加し、過去snapshot/現在snapshotの所有nativeと継承集合を結び付ける。全再生・改変拒否・成功IDのみの後続継承、CLI/workerの所有保存を検査する。

H10-b受入（2026-09-21）：[所有回復履歴](../HPHI_RECOVERED_HISTORY.md)。明示写像pair保存、過去owned native/ID順への結合、成功回復だけの後続継承、CLI再生・worker延長を検査。GUI要求欠落のredを補修。新6unit＋既存25unitとChrome4項目PASS、349実装/48所有ファイルの最終照合済み。次はH10-c。

#### H10-c

**依存：b**。調整の検索試行/最終細分とanchor indexを区別して回復を接続する。ID確認前の周波数未評価、失敗停止、保存再開/操作経路と元RF保持を検査し、親H10を統合監査する。

H10-c/親H10受入（2026-09-21）：[調整回復と元条件別監査](../HPHI_TUNING_IDENTITY_RECOVERY.md)。独立TEM場/周波数、真の縮退停止、検索親とanchor分離、所有CLI/worker再生・改変拒否、Chrome要求保持/元場表示を確認。新7/既存25unit、Chrome4項目PASS。全350実装/24所有ファイル不変、全handle終了0。次はH11。

## H11

### 曲線Hφの比較領域を構成する

- **親課題**：P03。**種別**：実装。初期状態：未着手。
- **先行条件**：[H08](02-hphi.md#h08)
- **コミット件名案**：`feat: 曲線Hφの比較領域を構成する`
- **既存の入口・影響先**：`src/superfish_ng/curved_meridional_geometry.py`、`src/superfish_ng/curved_hphi_fem.py`、`src/superfish_ng/curved_comparison_overlay.py`
- **実施内容**：新設curved_hphi_tracking.pyの前段として、全境界成分を持つ二次領域の同領域/宣言写像・共通参照分割を検査する。単一軸接続TM用の境界仮定を持ち込まない。
- **受入条件**：二次写像の全被覆・正Jacobian・穴面積/体積を独立積分で確認する。同じ頂点でも中点/二次境界が異なる反例を拒否し、比較予算超過は未確認を保持する。
- **既存の検査候補**：`test_curved_hphi_fem`、`test_curved_hphi`、`test_curved_comparison_overlay`。変更した契約に直接依存するケースを選ぶ。新機能の独立検査は別途追加する。
- **検査コマンドの出発点**：

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v test_curved_hphi_fem test_curved_hphi test_curved_comparison_overlay
```

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

H11受入（2026-09-21）：[曲線Hφ比較領域と条件別監査](../CURVED_HPHI_COMPARISON.md)。全P2幾何、独立native制限、非nested有理数共通分割、穴/軸役割、独立各成分面積/体積、中点反例と予算未確認を確認。新6/既存20件PASS、全handle終了0。次はH12。

## H12

### 曲線Hφの場比較と細分診断を実装する

- **親課題**：P03。**種別**：実装。初期状態：未着手。
- **先行条件**：[H11](02-hphi.md#h11)
- **コミット件名案**：`feat: 曲線Hφの場比較と細分診断を実装する`
- **既存の入口・影響先**：`src/superfish_ng/curved_hphi_rf.py`、`src/superfish_ng/hphi_field_overlap.py`、`src/superfish_ng/hphi_convergence.py`
- **実施内容**：曲線nativeから元E/Hを評価し、H11の実参照写像と体積で比較する。真空軸接続/正半径のq/u、零空間とguardを分け、細分差を専用診断へ接続する。
- **受入条件**：独立既知場積分、二尺度の実FEM、直線極限、三水準のf/場/RFを別判定する。解析曲線と二次近似を混ぜず、小残差を物理精度に読み替えない。
- **既存の検査候補**：`test_curved_hphi_saved`、`test_hphi_field_overlap`、`test_hphi_convergence`。変更した契約に直接依存するケースを選ぶ。新機能の独立検査は別途追加する。
- **検査コマンドの出発点**：

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v test_curved_hphi_saved test_hphi_field_overlap test_hphi_convergence
```

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

### H12の実装分割（2026-09-21）

独立既知場積分、二尺度実FEM、直線極限、三水準f/場/RF別判定という親条件を維持する。全子工程と条件別監査が完了するまで親H12は未完了。

#### H12-a

**依存：H11**。元曲線nativeを再構築し、全二次共通分割上でE/Hを別々に比較する。q/u・静的零空間を維持し、元Gram再現、独立既知場積分、実FEM尺度則、直線極限、改変拒否を検査する。

H12-a受入（2026-09-21）：[曲線元E/H比較](../CURVED_HPHI_FIELDS.md)。独立既知場、両q/uの二尺度実FEM、直線極限、native改変拒否/保存不変を確認。新6/関連20件PASS、全handle終了0。次はH12-b。

#### H12-b

**依存：a**。明示同二次領域の三水準診断へ接続する。周波数/場/RFと全境界を別判定し、正周波数guard不足・順位曖昧・求積不足を未確認に保つ。native保存読込を利用した三水準、軸加速RF、所有元場不変を検査し親を監査する。

H12-b/親H12受入（2026-09-21）：[固定P2三水準診断・条件別監査](../CURVED_HPHI_CONVERGENCE.md)。独立TEM f/q/Q、近縮退/guard停止、全参照境界とnative/RF保持、P1軸共通位相を確認。新5件の分割証拠＋関連19件PASS、全handle終了。次はH13。

## H13

### 曲線Hφの履歴と調整を保存・操作へ接続する

- **親課題**：P03 / D02 / O02。**種別**：実装。初期状態：未着手。
- **先行条件**：[H10](02-hphi.md#h10)、[H12](02-hphi.md#h12)
- **コミット件名案**：`feat: 曲線Hφの履歴と調整を保存・操作へ接続する`
- **既存の入口・影響先**：`src/superfish_ng/curved_hphi_saved.py`、`src/superfish_ng/hphi_tracking_history_saved.py`、`src/superfish_ng/gui_hphi.py`
- **実施内容**：曲線変形の元Project・履歴・加速座標を保持し、曲線比較/調整/回復の要求をCLI/worker/GUIへ追加する。最終細分では採用候補の同じ二次境界を保つ。
- **受入条件**：曲線穴付きの実FEM調整で停止/再開/元場再表示が一致する。各側の境界と係数を保持し、APIとGUIの全量一致、旧直線/同領域保存版の読み込みを確認する。
- **既存の検査候補**：`test_curved_hphi_workspace`、`test_hphi_tracking_history_saved`、`test_gui_hphi`。変更した契約に直接依存するケースを選ぶ。新機能の独立検査は別途追加する。
- **検査コマンドの出発点**：

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v test_curved_hphi_workspace test_hphi_tracking_history_saved test_gui_hphi
```

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

### H13の実装分割（2026-09-21）

親H13の穴付き実FEM調整、停止/再開/元場表示、全境界・係数・加速座標保持、API/GUI全量一致、旧保存読込を全工程で維持する。全子工程と監査まで親は未完了。

#### H13-a

**依存：H12**。元二次領域を再投影せずに細分し、q/uのP1/P2転送と全穴/軸を保持する。非dyadic寸法で避けられないbinary64丸めを明示版の比較契約で測定し、旧厳密要求は維持。独立面積/体積、質量保存、全境界・予算・改変拒否が受入条件。

H13-a受入（2026-09-21）：[同P2領域細分と明示丸め契約](../CURVED_HPHI_REFINEMENT.md)。旧版1厳密要求を維持し、全穴/軸・P1/P2・M/K転送・再細分・局所丸め拒否を確認。新6/関連21/三水準利用先2件PASS、全handle終了0。次はH13-b。

#### H13-b

**依存：a**。曲線scalar質量射影、元領域の有限比較スペクトル、E/H部分空間追跡を接続。独立既知場、直線極限、順位交換/縮退とguard停止を検証する。

H13-b受入（2026-09-21）：[scalar射影・有限スペクトル・曲線E/H追跡の条件別監査](../CURVED_HPHI_TRACKING.md)。実曲線順位交換/解析縮退/guard停止と元nativeを確認。次はH13-c、親H13は未完了。

#### H13-c

**依存：b、H10**。元Projectからの明示曲線形状変数、加速座標、同P2領域最終細分、過去確認anchorによるID回復を調整へ接続。未確認周波数を評価しない。穴付き実FEMの目標/粗細差を別判定する。

H13-c受入（2026-09-22）：[曲線調整・anchor回復・条件別監査](../CURVED_HPHI_TUNING.md)。未確認周波数をnullに保持し、実曲線回復と穴付き非一様調整の目標/粗細差を別検証。新8件（分割）/関連5件の証拠、全handle終端。次はH13-d、親H13は未完了。

#### H13-d

2026-09-22進行中：[所有調整のPython APIとCLI](../CURVED_HPHI_TUNING_SAVED.md)を検証済み。[worker起動・実中止再開・管理器再起動](../CURVED_HPHI_TUNING_WORKER.md)も検証済み。独立追跡履歴・回復操作も以下の最終監査で受入済み。

**依存：c**。全元native/Projectと履歴を所有して保存・CLI/workerへ接続。中止/再開/管理器再起動、改変拒否、元出力移動後の再生、旧保存要求の互換性を検証する。

2026-09-22：[独立曲線追跡pairの所有保存・worker](../CURVED_HPHI_TRACKING_SAVED.md)を接続。順序付き履歴/anchor回復/CLIは後述の段階で受入済み。GUIはH13-e。

2026-09-22：[所有曲線履歴と過去anchor回復](../CURVED_HPHI_HISTORY.md)を検証済み。順序付きnative/ID継承、worker延長、追跡/履歴CLIを接続。GUIはH13-e。調整回復の所有操作は下記の最終監査で受入済み。

H13-d受入（2026-09-22）：[全条件監査と調整回復の所有操作](../CURVED_HPHI_TUNING_RECOVERY_SAVED.md)。追加2件と全既存所有/CLI/worker/履歴証拠を照合、全handle終端。H13-e/親H13/全goalは未完了。

#### H13-e

受入済み（2026-09-22）：[曲線GUIの操作・HTTP修正・分割証拠](../CURVED_HPHI_GUI.md)、[親H13全条件の監査](../CURVED_HPHI_ACCEPTANCE.md)。全handle/サーバー終端、元Project/native/RF不変。次はH15-a。

**依存：d**。実GUIから曲線追跡/調整/回復、停止・再開・元場表示を操作し、APIとの全native/RF一致を検査。全handle終端と親H13の元条件別監査を実施する。

## H14

### 材料界面を保つ比較契約を定義する

- **親課題**：P04 / D02。**種別**：仕様。初期状態：未着手。
- **先行条件**：[H08](02-hphi.md#h08)
- **コミット件名案**：`docs: 材料界面を保つ比較契約を定義する`
- **既存の入口・影響先**：`src/superfish_ng/material_hphi.py`、`src/superfish_ng/material_hphi_fem.py`、`src/superfish_ng/rf_materials.py`
- **実施内容**：新設docs/MATERIAL_HPHI_TRACKING.mdで材料ID対応・領域/界面被覆・片側場・エネルギー重みを規定する。最初は固定した実数正値epsilon/muの幾何変形に限り、材料変更は別要求とする。
- **受入条件**：一様材料の周波数/場則と二層界面対照、真空極限を独立参照に指定する。真空内積の流用や界面平均、未対応の曲線/損失材料を受け入れない。
- **確認方法**：文書/仕様/監査は差分と根拠・リンク・依存を確認。検証カードは本文指定の専用実行を行い、[共通検証規則](README.md#検証と完了報告)で報告する。文書更新だけでFEMを再実行しない。

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

H14仕様受入（2026-09-22）：[固定材料界面の比較契約](../MATERIAL_HPHI_TRACKING.md)。全ID対応/界面被覆、片側場、epsilon/muエネルギー内積、材料質量/guard、一様材料・二層・真空極限の独立対照を規定。H08完了を確認し、H13-d検証待ち中に文書だけを実施。数値実装/受入はH15、操作接続はH16へ残す。

## H15

### 材料Hφの領域比較とID追跡を実装する

- **親課題**：P04。**種別**：実装。初期状態：未着手。
- **先行条件**：[H14](02-hphi.md#h14)
- **コミット件名案**：`feat: 材料Hφの領域比較とID追跡を実装する`
- **既存の入口・影響先**：`src/superfish_ng/material_hphi_fem.py`、`src/superfish_ng/hphi_field_overlap.py`、`src/superfish_ng/hphi_tracking.py`
- **実施内容**：明示材料対応で共通分割を領域ごとに分け、元片側E/Hと物理重みを用いる専用比較を追加する。静的核と有限比較空間の診断を材料形式に整合させる。
- **受入条件**：独立材料積分・真空極限・二層実FEMの正逆/尺度/番号置換で対応を確認する。界面位置/材料ID誤対応と未計算guardは拒否/未確認であり、元RFを変えない。
- **既存の検査候補**：`test_material_hphi_fem`、`test_material_hphi`、`test_hphi_spectral_resolution`。変更した契約に直接依存するケースを選ぶ。新機能の独立検査は別途追加する。
- **検査コマンドの出発点**：

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v test_material_hphi_fem test_material_hphi test_hphi_spectral_resolution
```

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

H15-c/親H15受入（2026-09-22）：[全条件監査](../MATERIAL_HPHI_ACCEPTANCE.md)。独立再メッシュ/非一様正逆、P1/P2真空追跡極限、実材料順位交換/縮退、E/H/B尺度・片側界面を確認。新5件＋関連1件は分割PASS、専用validator32例96モードPASS、全handle終端。次はH16の材料調整/保存/CLI-worker/GUI。原計画と全goalは継続。

### H15の実装分割（2026-09-22）

H14の全契約と元H15の独立材料積分・真空極限・二層実FEM・正逆/尺度/番号・界面/guard拒否・元RF不変を維持する。材料係数の変更、曲線材料、損失は追加しない。親H15は全子工程と統合監査の受入まで未完了。

#### H15-a

**依存：H14**。完全な材料partitionとmaterial/region全単射、明示same-domain/直線写像、元セル/領域/界面を所有する共通分割を追加する。`RFMaterialPartition`のinterface_cells/region_indicesと既存直線写像の被覆契約を利用し、全境界と同係数でも異なる領域の界面を保持する。独立の領域面積/回転体体積・界面長と対応する片側セル、独立再メッシュ/番号変更/ID改名、微小な界面位置不一致/誤ID/係数変更の拒否を検査する。数値場や固有周波数をまだ対応済みと主張しない。

H15-a受入（2026-09-22）：[全材料領域/界面の比較分割](../MATERIAL_HPHI_COMPARISON.md)。独立積分・非一様尺度/逆写像・番号/ID改名・1 ULP界面ずれ拒否を検査。新7件＋関連10件（変更1件追加検査）、全handle終端。場/射影/スペクトル/IDは未実装で、次はH15-b。

#### H15-b

**依存：H15-a**。材料元片側E/Hのepsilon0 epsilon_r / mu0 mu_rエネルギーGramと、q/uのmu_r質量射影を追加する。元セル指定の場評価と元K/Mを使用し、平均材料補正・真空経路への置換をしない。別Gauss/Vandermonde積分、一様材料の場振幅則、固定材料尺度のs^(-3/2)、P1/P2正半径/軸の真空極限、射影質量保存/損失とGram正定性を検査する。元全RF・規格化・係数を保持する。

H15-b受入（2026-09-22）：[材料元E/H比較](../MATERIAL_HPHI_FIELDS.md)と[mu_r質量射影](../MATERIAL_HPHI_PROJECTION.md)を実装。独立積分/材料別質量/射影保存と損失/正逆写像/真空極限/元RF不変を検証。射影新6件＋関連場5件は分割証拠でPASS、全handle終端。次はH15-cの材料有限スペクトルとID追跡。親H15/全goalは未完了。

#### H15-c

**依存：H15-b**。材料比較K/Mと静的q核を保持した有限スペクトル診断、guard群、E/H部分空間と位相が一致した場合だけの個別ID追跡を接続する。独立二層分離解とradial guard下界、正逆写像/全尺度/番号置換、未計算guardと曖昧集合の未確認、界面片側/元全RF不変を検査し、H15全条件の統合監査を行う。CLI/調整/所有履歴/GUIは元計画どおりH16へ残す。

H15-c進行中（2026-09-22）：[材料有限スペクトル診断](../MATERIAL_HPHI_SPECTRAL_RESOLUTION.md)を実装。元材料K/M・静的q核・全界面を保持し、独立比較固有値/二層TEM/尺度則を検査。ID追跡と親H15の統合監査は未実装、全goalは継続。

H15-c進行中（2026-09-22）：[固定材料E/HのID追跡](../MATERIAL_HPHI_ID_TRACKING.md)を接続。二層尺度/位相、guard未確認、継承集合、元宣言の厳密照合を検査。親H15の独立再メッシュ・真空追跡極限・実縮退/順位交換・非一様写像等の条件別監査は残る。全goalは継続。

## H16

### 材料Hφ調整と保存・GUIを接続する

- **親課題**：P04 / D02 / O02。**種別**：実装。初期状態：未着手。
- **先行条件**：[H10](02-hphi.md#h10)、[H15](02-hphi.md#h15)
- **コミット件名案**：`feat: 材料Hφ調整と保存・GUIを接続する`
- **既存の入口・影響先**：`src/superfish_ng/material_hphi_saved.py`、`src/superfish_ng/hphi_native.py`、`src/superfish_ng/gui_hphi.py`
- **実施内容**：固定材料のuniform_scaleと確認済み直線写像をHφ調整へ追加する。材料/領域/両R/QとN/A、全試行・回復状態を保存しCLI/worker/GUIへ渡す。
- **受入条件**：一様材料と二層材料の実調整、最終細分、中止/再開、全native照合が通る。軸加速量の非真空区間を拒否し、未対応損失量を0と表示しない。
- **既存の検査候補**：`test_material_hphi_saved`、`test_material_hphi_workspace`、`test_gui_hphi`。変更した契約に直接依存するケースを選ぶ。新機能の独立検査は別途追加する。
- **検査コマンドの出発点**：

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests .venv/bin/python -m unittest -v test_material_hphi_saved test_material_hphi_workspace test_gui_hphi
```

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

### H16の実装分割（2026-09-22）

元H16の固定材料uniform_scale/確認済み直線写像、実調整、最終細分、回復状態、全native、中止/再開、CLI/worker/GUI、真空加速区間とN/Aを維持する。親H16は全子工程と統合監査まで未完了。

#### H16-a

**依存：H15**。元Projectから独立に候補を作る固定材料形状則、領域/全界面を保つ細分、全加速座標の移送と真空区間再検査、元領域ごとの比較空間を実装する。材料K/M移送不変量、領域体積、多項式、uniform/nonuniform/穴/軸、予算拒否を検査。

H16-a受入（2026-09-22）：[材料候補・最終細分・比較空間](../MATERIAL_HPHI_TUNE_TRIALS.md)を接続。二段材料K/M移送、検索→実最終細分、穴付き軸の非一様変形/全加速座標、実E/H個別IDを検証。新4件＋関連6件は分割PASS、全handle終端。次はH16-bの実調整runnerと明示ID回復。親H16/全goalは継続。

#### H16-b

**依存：H16-a H10**。専用実FEM調整runnerに材料追跡、初回guard、粗細判定、明示ID回復、未確認時周波数nullを接続。一様/二層、uniform_scale/非一様写像、実最終細分、真の縮退/guard拒否を独立検査する。

H16-b受入（2026-09-22）：[材料実調整・明示ID回復](../MATERIAL_HPHI_TUNING.md)。二層uniform/異率伸長の独立解析目標、実最終細分、非真空一様材料の実TEM回復/真縮退拒否、初回guardと別粗細gateを確認。新8件は分割PASS、全handle終端。粗いn=4の区間重なりによる未確認を保持し、n=6は190.411秒PASS。次はH16-cの所有保存/履歴/CLI-worker。親H16/全goalは継続。

#### H16-c

**依存：H16-b**。全材料Project/native/試行/回復状態を所有する保存、移動後再生、prefix再開、独立追跡履歴、CLI/workerを接続。実中止/再開・管理器再起動・全native照合と両R/Q/N/Aを確認する。

H16-c進行中（2026-09-22）：[材料調整の所有保存](../MATERIAL_HPHI_TUNING_SAVED.md)は新5件123.786秒＋材料native関連4件10.185秒PASS、全handle終端。移動後の物理再生/新規出力への再開、元全native不変、失敗prefixと改変/path拒否を確認。次は独立追跡履歴とCLI-worker、回復/実中止/再起動の操作検査。親H16/全goalは継続。

H16-c進行中（2026-09-22）：[材料二状態追跡の所有保存・worker・CLI](../MATERIAL_HPHI_TRACKING_JOBS.md)は新4件＋関連2件PASS、全handle/worker終端。実中止/管理器再起動、元全native不変、移動/再import、改変/kind拒否を確認。CLI参照ミスの再現/修正記録も保持。次は独立追跡履歴と調整CLI-worker・回復操作。親H16/全goalは継続。

H16-c進行中（2026-09-22）：[材料の独立所有履歴と明示ID回復](../MATERIAL_HPHI_HISTORY.md)を接続。TEM場の独立確認、集合継承/guard、全祖先の移動/実worker延長/管理器再起動、CLI実行/再生を検査。新4件は分割PASS（履歴3件615.826秒、CLI1件74.797秒）、関連2件7.725秒PASS、全handle終端。次は材料調整CLI-workerと回復/実中止/再開操作。親H16/全goalは継続。

H16-c進行中（2026-09-22）：[材料調整CLI・専用worker](../MATERIAL_HPHI_TUNING_OPERATIONS.md)の新8件307.737秒＋関連1件70.743秒PASS、全handle/worker終端。実FEM尺度則、移動後再生、実中止/新規再開・管理器再起動、全prefix/元nativeと改変拒否を確認。次はID回復と実最終細分を伴う所有操作の統合監査。H16-d GUIと親H16/全goalは継続。

H16-c受入（2026-09-22）：[所有保存・履歴・CLI/worker条件別監査](../MATERIAL_HPHI_OPERATION_ACCEPTANCE.md)。最後の実CLI回復検索→worker最終細分・元移動/管理器再起動と、真空軸/材料/穴ProjectのRF・再importを新2件601.458秒PASSで確認。解析TEM、元18ファイルのbyteコピー、全24ファイル不変、両R/Q/N/A・非真空区間/未対応損失拒否まで成立。全handle終端。次はH16-dのGUI操作と親H16監査。原90カードと全goalは継続。

#### H16-d

**依存：H16-c**。GUIから材料調整/履歴/回復・最終細分・実中止/再開・元場を操作し、別Project/import後も全材料/領域/両R/Q/N/Aが保存/CLIと一致することを実ブラウザーで検査。親H16の全条件を監査してから受入する。

H16-d進行中（2026-09-22）：[材料調整GUI](../MATERIAL_HPHI_GUI.md)の要求保持・開始/再開・所有保存地点・元場取込を接続。新2件＋旧GUI2件107.967秒PASS、実Chrome5項目PASS、検査時元12ファイル/385実装hash不変・外部要求0、全handle終端。説明HTMLの後続修正と検査時hashを区別して記録。次は材料追跡/履歴GUI、実中止/再起動と回復操作。親H16/全goalは継続。

H16-d進行中（2026-09-22）：[材料追跡/履歴GUIと明示回復延長](../MATERIAL_HPHI_GUI.md)。新2件＋旧追跡GUI2件123.631秒、履歴関連2件141.020秒PASS。実Chromeは基本4項目＋回復延長5項目PASS、元12ファイル/所有履歴49ファイルと全385実装hash不変・外部要求0、全handle終端。次は調整回復/最終細分、実中止/新サーバー再起動、軸RFのブラウザー監査。親H16/全goalは継続。

H16-d/親H16受入（2026-09-22）：[材料調整・保存・GUI全条件監査](../MATERIAL_HPHI_TUNING_ACCEPTANCE.md)。最後の実Chromeは調整回復/最終細分4、中止/再開5、新サーバー軸RF再生2、不正物理拒否5項目が分割PASS。全native/Project取込一致、回復元24ファイル・全385実装hash不変、外部要求0、全handle終端。既存数値ログと実装差分を照合し、材料核の無変更を確認。次は依存が満たされたB02の対象版・入力資料調査。H17はB03を待つ。原90カードと全goalは継続。

## H17

### P04の損失モデルの必要範囲を確定する

- **親課題**：P04。**種別**：条件付き仕様。初期状態：未着手。
- **先行条件**：[B03](01-baseline.md#b03)、[H16](02-hphi.md#h16)
- **コミット件名案**：`docs: P04の損失モデルの必要範囲を確定する`
- **既存の入口・影響先**：`docs/MATERIAL_HPHI_RF_PLAN.md`、`docs/MATERIAL_HPHI_RF.md`、`docs/COMPATIBILITY_MATRIX.md`
- **実施内容**：対象版/ユーザー要件を壁損失、摂動的体積損失、複素固有値へ区別する。必要と確認されたモデルについてだけ式・phasor・保存量・独立参照・適用限界を決め、L05で実装/保存/検証カードを起票する。
- **受入条件**：壁損失の限定受入と、体積/複素損失の未実装が明確。要件が必須なら追加カードの受入前にP04を閉じない。未確認で仕様を推定しない。
- **確認方法**：文書/仕様/監査は差分と根拠・リンク・依存を確認。検証カードは本文指定の専用実行を行い、[共通検証規則](README.md#検証と完了報告)で報告する。文書更新だけでFEMを再実行しない。

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

- **進捗（2026-09-22）**：[H17損失モデルの範囲](../MATERIAL_HPHI_LOSS_SCOPE.md)。壁損失のコード/既存検査を照合。追加体積/複素モデルの採否は未確認でH17はIN_PROGRESS。

## H18

### P03/P04の要件受入を監査する

- **親課題**：P03 / P04。**種別**：監査。初期状態：未着手。
- **先行条件**：[H13](02-hphi.md#h13)、[H16](02-hphi.md#h16)、[H17](02-hphi.md#h17)、[C07-hphi](06-compatibility.md#c07-hphi)、[C07-material](06-compatibility.md#c07-material)
- **コミット件名案**：`docs: P03/P04の要件受入を監査する`
- **既存の入口・影響先**：`docs/COMPATIBILITY_PLAN.md`、`docs/IMPLEMENTATION_STATUS.md`、`docs/BACKLOG.md`
- **実施内容**：新設P03_ACCEPTANCE.md/P04_ACCEPTANCE.mdで元要件、既存FEM証拠、全新経路、対象版比較を照合する。H17で必要になった追加カードを含める。
- **受入条件**：全必須要件に適用可能な証拠が揃った親だけ受入へ更新する。曲線材料、開放/TEM等の未要求機能を勝手に追加せず、必須と確認された不足は残す。
- **確認方法**：文書/仕様/監査は差分と根拠・リンク・依存を確認。検証カードは本文指定の専用実行を行い、[共通検証規則](README.md#検証と完了報告)で報告する。文書更新だけでFEMを再実行しない。

- **納品物**：該当差分、カード受入条件ごとの結果と未確認理由、実施したコマンド/終了状態、次の着手ID。数値実行のrawは未使用の`out/`以下に保存し、短い結果と来歴を該当仕様書へ記録する。

## 最初の実装区切り H01〜H07の補足仕様

### H01で確定するAPIと保存契約

後続実装を担当者の推測にしないため、H01の仕様コミットで次の名称/内容を固定する。名称は新設案であり現行APIではない。

| 新設候補 | 責務 |
|---|---|
| `validate_hphi_tune(request)` | 専用形式/版、HphiProject、変数と単位、増加範囲、目標/許容差、ID/guard、求積/比較/試行/メッシュ予算を検査 |
| `trial_hphi_project(request, value, phase)` | 常に元Projectから候補を生成。検索と最終細分を区別し、境界/軸/穴を維持 |
| `run_hphi_tune(...)` | 実専用FEM→元場の比較→個別ID確認→周波数評価→二分判断。実装名/引数は既存runnerとの整合を仕様で確定 |
| `replay_hphi_tune(...)` | 所有した要求/全nativeから判断履歴を再構築し、保存時との一致を確認 |
| `hphi_tuning_jobs.py` | 物理判断を再実装せず、要求所有/別プロセス/中止/保存地点/再開を管理 |

要求は少なくとも、専用`format`/整数版、`project`、`parameter`、`bounds`、`target_hz`、
`frequency_tolerance_hz`、変数単位に従う`parameter_tolerance`、`initial_ids`/`mode_id`、
比較controls、`max_trials`、最終細分指定、要素上限、`mesh_frequency_tolerance_hz`を持つ。
平面調整の要求を読み替えるのではなく、Hφの比較空間と零モードの契約を明記する。

保存する一試行は、実パラメータ、検索/細分段階、親試行、実Project/nativeの所有先、元スペクトル、
比較要求/結果、継承ID/群、対象の実順位、評価周波数またはnull、停止理由を保持する。
再開に伴い許す変更と許さない変更はH01で列挙し、無断の許容差/目標変更で過去の失敗を成功へ変えない。

### 独立不変量

既存の各物理仕様を正本とする。H02/H04の真空一様尺度では、全長を正数`s`倍し、全周の蓄積エネルギーUを固定したとき、
対応する点で `f → f/s`、E/Hは`s^(-3/2)`倍となる。
したがって正半径の`q=rHφ`は`s^(-1/2)`倍、軸接続の`u=Hφ/r`は`s^(-5/2)`倍となる。
この三つを混同しない。加速軸が有効で座標/位相原点も同じ尺度で変形した場合の両R/Q、G、TTFは尺度不変。
同じ非磁性壁導電率ではQ0は`s^(1/2)`倍。N/Aの量には尺度比較を行わない。

- 元q/uの係数の一致だけでは元E/Hの一致を代用しない。
- 空間比較のための係数/座標変換を、新しいFEM解やRF量として保存しない。
- 既存の有限比較空間スペクトル診断は同領域用。尺度の異なる周波数/近傍区間をそのまま比較せず、H01/H02で共通尺度への写像とguardの意味を定義・検証する。
- 異方的変形/同軸一寸法変更では上の一様尺度式は適用しない。H08以後の写像と独立参照を使う。

### 新しい検査を置く候補

H02は`test_hphi_tracking.py`等へ独立尺度検査、H03〜H05は新設`tests/test_hphi_tuning.py`、
H06は`tests/test_hphi_tuning_jobs.py`、H07は`tests/test_gui_hphi_tuning.py`を候補とする。
専用実FEM検証は新設`scripts/validate_hphi_tuning.py`へまとめ、API/CLI/native/二尺度と失敗例を個別報告する。
GUIは既存Hφの配信/操作方式で実ブラウザー検査を追加する。
これらの新規ファイルは計画時点では存在しないため、各カードに掲げた既存モジュールの検査とは別に作成/実行する。
