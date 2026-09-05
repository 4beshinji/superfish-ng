# SPDX-License-Identifier: Apache-2.0
"""Fresh all-exercise regression and a local seminar navigation page."""
import argparse
import hashlib
import html
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def job_success(exit_code, report):
    return exit_code == 0 and isinstance(report, dict) and report.get('passed') is True


def wait_for_reference_files(paths, timeout_s, interval_s=5.):
    """Read-only wait for nonempty, stable files; the child still validates contents."""
    start, last_notice, previous = time.monotonic(), -60., None
    while True:
        snapshot = tuple((p.stat().st_size, p.stat().st_mtime_ns) if p.is_file() else (0, 0) for p in paths)
        if all(size > 0 for size, _ in snapshot) and (snapshot == previous or timeout_s == 0):
            return True
        elapsed = time.monotonic()-start
        if elapsed >= timeout_s: return False
        if elapsed-last_notice >= 60:
            print(f'WAIT reference outputs: {sum(size > 0 for size, _ in snapshot)}/{len(paths)} nonempty files; {elapsed:.0f} s', flush=True)
            last_notice = elapsed
        previous = snapshot
        time.sleep(min(interval_s, timeout_s-elapsed))


def portal(out, jobs, numerical_passed):
    options, panels, rows = [], [], []
    for job in jobs:
        name = job['name']
        directory = out/name
        page = directory/'index.html'
        figures = sorted(directory.rglob('*.png')) if page.exists() else []
        label = html.escape(job['label'])
        if figures:
            options.append(f'<option value="{name}">{label}</option>')
            source = html.escape(figures[0].relative_to(out).as_posix(), quote=True)
            panels.append(f'<section class="mode" id="{name}" {"hidden" if panels else ""}>'
                          f'<h2>{label}</h2><p><a href="{name}/index.html">全モード・場・CSVを開く</a></p>'
                          f'<img src="{source}" alt="{label}: calculated result preview"></section>')
        report = directory/job['report_file']
        link = f'<a href="{name}/{job["report_file"]}">数値記録</a>' if report.exists() else '数値記録なし'
        rows.append(f'<tr><td>{label}</td><td>{html.escape(job["status"])}</td><td>{link}</td></tr>')
    (out/'index.html').write_text('<!doctype html><html lang="ja"><meta charset="utf-8"><title>Superfish-NG seminar</title>'
        '<style>body{font:16px system-ui;max-width:1150px;margin:32px auto;padding:0 20px}img{width:100%}select{font:inherit;padding:8px}'
        'td,th{padding:8px;border-bottom:1px solid #ccc;text-align:left}pre{overflow:auto;background:#eee;padding:16px}</style>'
        f'<h1>教育加速器セミナー：例題計算と可視化</h1><p>全数値ゲート：{"PASS" if numerical_passed else "FAIL / INCOMPLETE"}。'
        '新規NG計算。参照照合・画面操作の検査を分けて記録します。</p>'
        '<p>真空・軸対称m=0 TM・PEC。電磁場はピークphasor、全領域U=1 J。'
        '半領域はU=0.5 Jから明示的に鏡映。R/Q(acc)=|V|²/(ωU)、Vは符号付きEzの通過位相積分です。'
        '角部のピーク場は収束保証の対象外です。</p>'
        '<label for="selector">例題 </label><select id="selector">'+''.join(options)+'</select>'+''.join(panels)+
        '<h2>検証一覧</h2><table><tr><th>対象</th><th>結果</th><th>記録</th></tr>'+''.join(rows)+'</table>'
        '<p><a href="numerical.json">コマンド・環境・全数値検査</a>。画面操作を含む最終判定は同じフォルダのsuite.jsonに保存します。</p>'
        '<h2>変更・再計算・保存</h2><p>各記録のcaseを参考にexamplesのJSONを複製し、寸法・分割数等を編集します。'
        '計算済みcase.jsonを直接書き換えても保存済みの場は変わりません。必ず新しい出力先へ再計算してください。'
        '</p><pre>superfish-ng solve examples/pillbox.json --out out/my-new-run\n'
        'superfish-ng plot out/my-new-run --mode 1 --mesh --out out/my-new-mesh.png</pre>'
        '<p>図とCSVはローカルファイルとして保存済みです。計算・入力エラーは各job.logとJSONで確認してください。</p>'
        '<script>document.getElementById("selector").addEventListener("change",e=>document.querySelectorAll(".mode").forEach(s=>s.hidden=s.id!==e.target.value))</script></html>', encoding='utf-8')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--run-legacy', action='store_true')
    parser.add_argument('--native-only', action='store_true', help='no Wine comparison; deliberately cannot pass the complete milestone')
    parser.add_argument('--pillbox-reference-run', type=Path)
    parser.add_argument('--flat-reference-run', type=Path)
    parser.add_argument('--rounded-reference-root', type=Path)
    parser.add_argument('--rounded7-chord-m', type=float, default=7.5e-7)
    parser.add_argument('--rounded7-extra-reference', action='append', nargs=3, default=[],
                        metavar=('PHASE_INDEX', 'DX_CM', 'DIRECTORY'), help='supplemental saved Wine refinement for one 0-based phase')
    parser.add_argument('--reference-wait-seconds', type=float, default=0., help='read-only wait for ongoing rounded Wine outputs; contents are then validated by each comparison')
    parser.add_argument('--skip-browser', action='store_true', help='skip UI checks; deliberately cannot pass the complete milestone')
    args = parser.parse_args(argv)
    references = [args.pillbox_reference_run, args.flat_reference_run, args.rounded_reference_root]
    if (args.run_legacy and args.native_only) or ((args.run_legacy or args.native_only) and any(references)):
        parser.error('choose live Wine, native-only, or saved references')
    if not args.run_legacy and not args.native_only and not all(references):
        parser.error('supply all three reference paths, --run-legacy, or explicit --native-only')
    if not 0 < args.rounded7_chord_m < .001:
        parser.error('rounded7 chord tolerance must be positive and below 1 mm')
    if not 0 <= args.reference_wait_seconds <= 86400:
        parser.error('reference wait must be between 0 and 86400 seconds')
    if args.native_only and args.rounded7_extra_reference:
        parser.error('supplemental Wine references cannot be used with native-only')
    extra7, previous_dx = [], dict.fromkeys(range(7), .0125)
    for phase_text, dx_text, directory in args.rounded7_extra_reference:
        try:
            phase, dx = int(phase_text), float(dx_text)
        except ValueError:
            parser.error('supplemental phase and dx must be numeric')
        if phase not in previous_dx or not 0 < dx < previous_dx[phase]:
            parser.error('supplemental phase must be 0..6 and dx strictly finer for that phase')
        previous_dx[phase] = dx
        extra7.append((str(phase), str(dx), str(Path(directory).resolve())))
    out = args.out.resolve()
    if not out.is_relative_to(ROOT/'out') or out == ROOT/'out':
        parser.error('suite output must be a new subdirectory under project out/')
    out.mkdir(parents=True, exist_ok=False)
    sources = [p for folder in ('src', 'scripts', 'tests', 'examples') for p in sorted((ROOT/folder).rglob('*'))
               if p.is_file() and '__pycache__' not in p.parts]
    hashes = {str(p.relative_to(ROOT)): digest(p) for p in sources}
    report = {'status': 'running', 'passed': False, 'native_computation': 'all NG solves freshly executed; no native-run imports',
              'wine_compared': not args.native_only, 'source_sha256': hashes, 'jobs': [], 'browser': [],
              'environment': {'python': platform.python_version(), 'platform': platform.platform(), 'openblas_num_threads': 1}}
    environment = dict(os.environ, OPENBLAS_NUM_THREADS='1', MPLCONFIGDIR=os.environ.get('MPLCONFIGDIR', '/tmp/superfish-matplotlib'))
    wine = ['--run-legacy'] if args.run_legacy else []
    pillbox = wine or (['--reference-run', str(args.pillbox_reference_run.resolve())] if args.pillbox_reference_run else [])
    flat = list(wine)
    if args.flat_reference_run:
        reference = json.loads((args.flat_reference_run/'comparison.json').read_text())
        if not reference.get('passed') or not reference.get('wine_compared'):
            parser.error('flat reference must be a passing Wine comparison')
        flat = ['--reference-dirs']+sorted({str(Path(m['source_directory']).parent) for r in reference['legacy'] for m in r['modes']})
        for extra in reference.get('supplemental_legacy', []):
            mode = extra['mode']
            flat += ['--extra-wine-reference', str(extra['phase_index']), str(mode['dx_cm']), mode['source_directory']]
    rounded = {name: wine or (['--reference-dirs', str((args.rounded_reference_root/name).resolve())]
                              if args.rounded_reference_root else []) for name in ('rounded4', 'rounded7')}
    jobs = [
        ('validation', '基礎物理・入力出力・回帰テスト', 'validate.py', [], 'validation.json'),
        ('pillbox', 'Pillbox TM010/TM011・長さ掃引', 'seminar_pillbox.py', pillbox, 'comparison.json'),
        ('symmetry', 'Pillbox半領域・電気/磁気対称面', 'seminar_symmetry.py',
         [] if args.native_only else ['--reference-run', str(out/'pillbox')], 'comparison.json'),
        ('flat4', '平坦ディスク4セル・全モード', 'seminar_multicell.py', ['--case', 'flat4', '--wine-dx', '.05', '.025', '.0125', '.01', '--wine-timeout-s', '1200']+flat, 'comparison.json'),
        ('rounded4', '円弧ディスク4セル・全モード', 'seminar_multicell.py', ['--case', 'rounded4', '--wine-timeout-s', '1200']+rounded['rounded4'], 'comparison.json'),
        ('end_cells', 'full-cell / half-cell端部比較', 'seminar_end_cells.py', ['--flat-half-extra-n', '384'], 'comparison.json'),
        ('geometry4', '4セル円弧近似の細分検査', 'seminar_geometry.py', ['--case', 'rounded4'], 'comparison.json'),
        ('geometry7', '7セル円弧近似の細分検査', 'seminar_geometry.py', ['--case', 'rounded7', '--triangulation', 'crossed', '--tolerances-m',
         str(4*args.rounded7_chord_m), str(args.rounded7_chord_m), str(args.rounded7_chord_m/4)], 'comparison.json'),
        ('rounded7', '円弧ディスク7セル・全モード', 'seminar_multicell.py', ['--case', 'rounded7', '--triangulation', 'crossed', '--levels', '64', '128', '256',
         '--chord-tolerance-m', str(args.rounded7_chord_m), '--wine-timeout-s', '1200']+rounded['rounded7']+
         [value for extra in extra7 for value in ['--extra-wine-reference', *extra]], 'comparison.json'),
    ]
    for name, label, script, options, filename in jobs:
        command = [sys.executable, str(ROOT/'scripts'/script), '--out', str(out/name)]+options
        row = {'name': name, 'label': label, 'command': command, 'report_file': filename, 'status': 'running'}
        report['jobs'].append(row); write_json(out/'suite.json', report)
        print(f'START {name}', flush=True)
        start = time.monotonic()
        if name in rounded and args.rounded_reference_root and args.reference_wait_seconds:
            count = 7 if name == 'rounded7' else 4
            files = [args.rounded_reference_root/name/f'dx{dx:g}'/f'mode{i}'/filename
                     for dx in (.05, .025, .0125) for i in range(1, count+1) for filename in ('CAVITY.SFO', 'OUTSF7.TXT')]
            if name == 'rounded7':
                files += [Path(extra[2])/filename for extra in extra7 for filename in ('CAVITY.SFO', 'OUTSF7.TXT')]
            row['reference_wait_completed'] = wait_for_reference_files(files, args.reference_wait_seconds)
        with (out/f'{name}.log').open('w') as log:
            result = subprocess.run(command, cwd=ROOT, env=environment, stdout=log, stderr=subprocess.STDOUT)
        path = out/name/filename
        try:
            numerical = json.loads(path.read_text()) if path.exists() else None
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            numerical = None
            row['report_error'] = str(exc)
        row.update(exit_code=result.returncode, seconds=time.monotonic()-start, status='PASS' if job_success(result.returncode, numerical) else 'FAIL')
        if path.exists(): row['report_sha256'] = digest(path)
        print(f'{row["status"]} {name}', flush=True)
        write_json(out/'suite.json', report)
    report['numerical_passed'] = all(j['status'] == 'PASS' for j in report['jobs']) and report['wine_compared']
    write_json(out/'numerical.json', report)
    portal(out, report['jobs'], report['numerical_passed'])
    if not args.skip_browser:
        for name, _, _, _, _ in jobs:
            page = out/name/'index.html'
            if not page.exists(): continue
            browser_out = out/'browser'/name
            command = ['node', str(ROOT/'scripts/verify_gallery.mjs'), '--html', str(page), '--out', str(browser_out)]
            if name == 'symmetry': command += ['--mode', 'static']
            with (out/f'browser-{name}.log').open('w') as log:
                result = subprocess.run(command, cwd=ROOT, env=environment, stdout=log, stderr=subprocess.STDOUT)
            path = browser_out/'verification.json'
            data = json.loads(path.read_text()) if path.exists() else None
            report['browser'].append({'name': name, 'passed': job_success(result.returncode, data), 'directory': str(browser_out)})
        command = ['node', str(ROOT/'scripts/verify_gallery.mjs'), '--html', str(out/'index.html'), '--out', str(out/'browser/portal')]
        with (out/'browser-portal.log').open('w') as log:
            result = subprocess.run(command, cwd=ROOT, env=environment, stdout=log, stderr=subprocess.STDOUT)
        path = out/'browser/portal/verification.json'
        data = json.loads(path.read_text()) if path.exists() else None
        report['browser'].append({'name': 'portal', 'passed': job_success(result.returncode, data), 'directory': str(path.parent)})
    report['source_changed_during_run'] = hashes != {str(p.relative_to(ROOT)): digest(p) for p in sources}
    report['passed'] = (report['numerical_passed'] and len(report['browser']) == 7
                        and all(r['passed'] for r in report['browser']) and not report['source_changed_during_run'])
    report['status'] = 'PASS' if report['passed'] else 'FAIL / INCOMPLETE'
    write_json(out/'suite.json', report)
    print(f'{report["status"]}: {out}/index.html', flush=True)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
