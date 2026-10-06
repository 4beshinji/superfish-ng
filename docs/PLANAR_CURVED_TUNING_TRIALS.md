# 平面曲線調整の元写像付き試行生成

2026-10-07、P09の試行生成leaf。P09はIN_PROGRESS。実検索controller/両周波数gate/所有保存/再開/GUIは未受入。
先行は[元全二次節点の形状則](PLANAR_CURVED_SHAPE_LAW.md)。
`planar_curved_tuning_trials.py` の `generate_planar_curved_trial` は元Project/完全shape law/値から
毎回reference Projectを生成し、指定0〜8回のuniform四分割でnative Projectを作る。
検索は0回、最終検査は要求level数で同じ関数を使う。元Domainの全二次外周を保持し、真円等へ再投影しない。

各子の有理参照chartを前段の有理chartへ合成して、元referenceのセルへ直接対応させる。
最終nativeの全六節点多項式・全セル被覆・全PEC外周を元referenceへ照合する。
512ε局所extent上限は累積した元写像誤差へ適用し、直前levelの丸め表示だけを信用しない。
計算済みの元チャートはtuple/Fractionで保持し、`native_cells` は毎回fresh JSONを返す。

全最終予算を細分前に検査する。元Tセル/E corner edge/N nodeに対し、各levelで
T←4T、E←2E+3T、N←N+2E+3T（右辺は前level）。
一つの元セルにd=4**levels子があるので、元referenceとの完全比較pairはT_original*d*(d+1)/2。
元セルごとの自己重複と交差を全て含む。標準max_triangles/max_dofsは各250,000、pair2,000,000。
large/deep細分ではこの明示pair予算が先に尽き得る。予算自動拡張・元セルごとのリセット・部分試行の受入はしない。
Domain幾何予算は元Caseの明示値を保持し、作成後の全counts/実比較pair数も予定値と照合する。

`PlanarCurvedTrial` はreference/native Project、元chart、生成診断を持つ。
`planar_curved_trial_comparison` は同じ完全元Project/shape lawから生成した両trialに限り、
両reference Domainの完全なdeclared quadratic correspondenceを作る。
元trial値/細分level・各元nativeの全hash/所有prefixは後続tuning ownerが要求から再生成して検証する。
生成診断dictそのものをsaved nativeの正しさの証拠にはしない。
本生成関数はFEM/周波数/IDを作らず、二次Domainと明示chartだけを返す。

## 独立対照と限定検査

最初に二段細分の全子六節点を元既知二次patchの閉式で検査し、API不在の
ModuleNotFoundErrorを `trials-baseline.log` に保存した。元数値回帰の失敗ではない。
元patch x=-1/4+u/8、y=(v+u*(1-u-v)/4)/8 に、x×3/2,y×5/4を適用し、
全子のcorner/midを独立有理式と完全一致させる。全被覆・U′/元Project不変も確認する。
実楕円TE/TMの検索→二段最終meshで元E/H Gramを積分し、両元K/M energyを再現、全元byte/RFを保持する。
chart入力コピーへの変更が保存chartを変えないこと、全counts/pair/dof予算の細分前停止、
異なる元Projectの比較拒否、後段の実座標改変を局所zero-error表示で受入しないことを分けて確認する。
合成patch/楕円は測定構造ではない。

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src:tests UV_CACHE_DIR=/tmp/superfish-ng-uv-cache \
uv run --no-sync python -m unittest -v \
test_planar_curved_tuning_trials test_planar_curved_shape test_planar_curved_comparison
```

新4＋関連11、15件10.289秒PASS（終了0）。rawは
`out/p09-planar-curved-comparison-20261007/trials-selected-tests.log`。
`trials-acceptance.json` は実装/test/元FAIL/成功log hashと基準972af74の元409製品不変を照合した。
新製品は専用trial生成1モジュール。曲線/共有kernelは不変。
unit内の元実FEM/元場比較は実行し、full/seed/GUI/新大型validatorは実行していない。
自作shape law・P2制限・Fraction chart・完全比較だけを再利用し、累積元mapへ直接検証する。
新外部資料/依存/legacy参照なし。
次は `planar_curved_tuning.py` のstrict要求・実FEM試行/完全native replay・元E/Hの選択周波数・
検索/最終の二gateと明示過去anchor回復。続いて所有prefix保存/再開、CLI/worker/GUIを接続する。
P09はこれら全てと円/非円形実例の条件別受入まで継続する。
