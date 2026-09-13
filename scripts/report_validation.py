# SPDX-License-Identifier: Apache-2.0
"""Generate the Japanese validation summary from actual JSON evidence."""
import argparse
import json
import re
from pathlib import Path


def test_summary(root, report):
    """Describe executed tests, including scoped runs and old serial reports."""
    if report.get('tests', {}).get('status') == 'NOT_RUN':
        return 'unittestは未実行（--skip-tests）。seed数値検証のみを実行した。'
    parallel = root / 'test-run' / 'report.json'
    if parallel.exists():
        count = json.loads(parallel.read_text())['tests_run']
    else:
        count = int(re.search(r'Ran (\d+) tests?', (root/'tests.log').read_text()).group(1))
    return f'unittest {count}件と収束ゲートを実行した。'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('validation',type=Path)
    parser.add_argument('--out',type=Path,required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error('output already exists')
    root = args.validation
    report = json.loads((root/'validation.json').read_text())
    conv = json.loads((root/'pillbox_convergence.json').read_text())
    modes = json.loads((root/'multimode.json').read_text())
    shaped = json.loads((root/'shaped_refinement.json').read_text())
    env = report['environment']
    lines = ['# 数値検証報告','',
             f"実行範囲の結果: **{'PASS' if report['passed'] else 'FAIL'}**。{test_summary(root, report)}",
             'これは実装のverificationであり、実機やlegacy SUPERFISHによるvalidation完了を意味しない。','',
             f"環境: Python {env['python']} / NumPy {env['numpy']} / SciPy {env['scipy']}。",
             '詳しいコマンド、所要時間、source hashは実行出力の `validation.json`。',
             'unittest実行時のみ `tests.log` があり、並列時の全件集計は `test-run/report.json`。','',
             '## Pillbox TM010 の周波数収束','',
             '半径0.1 m、長さ0.2 m、真空、全PEC、β=1、σ=5.8e7 S/m。',
             f"解析周波数: **{conv['analytic']['frequency_hz']/1e6:.9f} MHz**。",'',
             '| nr=nz | 節点数 | 周波数 MHz | 相対誤差 | R/Q 相対誤差 |',
             '|---:|---:|---:|---:|---:|']
    for row in conv['rows']:
        e,q = row['relative_errors'],row['quantities']
        lines.append(f"| {row['nr']} | {row['nodes']} | {q['frequency_hz']/1e6:.9f} | {e['frequency_hz']:.3e} | {e['r_over_q_accelerator_ohm']:.3e} |")
    lines += ['', '周波数は約2次で改善するが、軸上Ezを用いるR/Qはより遅い。周波数誤差をRF量全体の誤差と読み替えない。', '',
              '## 最細メッシュのRF量','', '| 量 | 解析値 | FEM値 | 相対誤差 |','|---|---:|---:|---:|']
    last = conv['rows'][-1]
    for key in ['frequency_hz','q0','geometry_factor_ohm','r_over_q_accelerator_ohm','transit_time_factor_abs','epk_over_eacc_estimate','bpk_over_eacc_estimate_mt_per_mv_per_m']:
        lines.append(f"| {key} | {conv['analytic'][key]:.9g} | {last['quantities'][key]:.9g} | {last['relative_errors'][key]:.3e} |")
    lines += ['', 'ピーク比の単位と推定範囲はPHYSICS.md参照。長いpillboxのためTTFが約0.279で、R/Qは短い空洞の値とは異なる。','',
              '## 高次モード','', 'nr=40、nz=48。同じ解析スペクトルの先頭6個を比較する。',
              'これはm=0 TMの6個であり、TEやm>0を含めた全Maxwellスペクトルではない。','',
              '| 解析ラベル | 解析 MHz | FEM MHz | 相対誤差 |','|---|---:|---:|---:|']
    for row in modes:
        lines.append(f"| {row['label']} | {row['analytic_hz']/1e6:.6f} | {row['numerical_hz']/1e6:.6f} | {row['relative_error']:.3e} |")
    lines += ['', '高次モードの合格条件は0.3%であり、基本モードの1e-4条件を全モードが満たしたという意味ではない。', '',
              '## 非円筒形状の自己収束','',
              '`examples/shaped_cell.json` は合成した首付き空洞。両端は閉じたPEC端板で、実機のビームポートではない。','',
              '| nr | nz目安 | 節点 | f MHz | R/Q(acc) Ω | Q0 | Epk/Eacc 推定 |',
              '|---:|---:|---:|---:|---:|---:|---:|']
    for row in shaped['rows']:
        q=row['quantities']
        lines.append(f"| {row['nr']} | {row['nz']} | {row['nodes']} | {q['frequency_hz']/1e6:.6f} | {q['r_over_q_accelerator_ohm']:.6f} | {q['q0']:.3f} | {q['epk_over_eacc_estimate']:.6f} |")
    lines += ['', '**周波数・積分量が落ち着いても、角部のEpkは増加している。** この表をピーク電場の収束証明に使ってはいけない。',
              '実用設計では丸め半径を指定した滑らかな形状と高次メッシュで検証する必要がある。',
              '外部参照のないため、これらの絶対値の精度は確定していない。','',
              '## unittestで確認する項目（実行有無は冒頭参照）','',
              '- Bessel場との重み付きL2比較で、周波数だけを再現する誤実装を検出。',
              '- 質量内積のモード直交性、固有値残差、電気/磁気エネルギーを確認。',
              '- 任意形状の一様拡大でf∝1/s、R/Q一定、常伝導Q∝sqrt(s)を確認。',
              '- Uを9倍、σを4倍とした場合の場振幅、壁損失、Qのスケーリングを確認。',
              '- 軸上区分線形場の通過位相積分を独立した数値積分と比較。',
              '- 未対応入力・重複キー・既存出力への上書きを拒否することを確認。','',
              '## 未実施','',
              *['- ' + item for item in report['not_performed']], '',
              '図の生成・目視確認やHosted CIは、この数値報告からは実施を主張しない。','',
              '## 再実行','', '```bash',
              'OPENBLAS_NUM_THREADS=1 python scripts/validate.py ' + ('--skip-tests ' if report.get('tests', {}).get('status') == 'NOT_RUN' else '') + '--out out/validation-new',
              'python scripts/plot_results.py out/validation-new/shaped_cell --out out/validation-new/shaped_cell.png',
              'python scripts/report_validation.py out/validation-new --out out/validation-report.md', '```','',
              '新しい結果は納品ベースラインと比較し、精度を改善した場合も旧エビデンスを説明なく差し替えない。','']
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text('\n'.join(lines),encoding='utf-8')


if __name__ == '__main__':
    main()
