"""Build an additive, offline visual edition from delivered seminar results.

No solver execution and no changes to the original reports or numerical results.
Usage: .venv/bin/python scripts/build_seminar_visualizations.py DELIVERY --out NEW_DIR
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import os
from pathlib import Path
import re

os.environ.setdefault('MPLCONFIGDIR', '/tmp/seminar-visualization-mpl')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def build(base: Path, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=False)
    (out / 'figures').mkdir()
    plt.rcParams.update({'font.family': ['Noto Sans CJK JP', 'DejaVu Sans'], 'font.size': 10,
                         'axes.spines.top': False, 'axes.spines.right': False})
    source = base / '02-superfish-ng'
    used = {}
    figures = []

    def record(path):
        used[str(path.relative_to(base))] = hashlib.sha256(path.read_bytes()).hexdigest()
        return path

    def rows(name):
        with record(source / 'results' / name).open() as stream:
            return list(csv.DictReader(stream))

    def document(name):
        return json.loads(record(source / name).read_text())

    def rel(path):
        return Path(os.path.relpath(path, out)).as_posix()

    def save(fig, name, caption, sources):
        fig.tight_layout(pad=1.8)
        fig.savefig(out / 'figures' / (name + '.png'), dpi=170)
        fig.savefig(out / 'figures' / (name + '.svg'))
        plt.close(fig)
        figures.append({'id': name, 'caption': caption, 'sources': sources})
        links = ' ／ '.join(f'<a href="{html.escape(rel(source / s), quote=True)}">{html.escape(Path(s).name)}</a>' for s in sources)
        return (f'<figure id="{name}"><a href="figures/{name}.svg"><img src="figures/{name}.png" '
                f'alt="{html.escape(caption, quote=True)}"></a><figcaption>{html.escape(caption)} '
                f'元データ：{links} ／ <a href="figures/{name}.svg">SVG</a></figcaption></figure>')

    data = {'NG': rows('superfish-ng-results.csv'), 'Superfish': rows('superfish-results.csv')}
    colors = {'NG': '#007f88', 'Superfish': '#c05220'}
    metrics = [('frequency_mhz', '周波数 [MHz]', 1), ('rq_acc_ohm', 'R/Q (acc) [Ω]', 1),
               ('q0', 'Q₀ [無次元]', 1), ('wall_loss_U1J_w', '壁損失 P（U=1 J）[kW]', .001)]
    result_sources = ['results/superfish-ng-results.csv', 'results/superfish-results.csv']
    fig, axes = plt.subplots(2, 2, figsize=(10, 7))
    for ax, (key, title, scale) in zip(axes.flat, metrics):
        for solver, rr in data.items():
            for mode, marker in [('TM010', 'o'), ('TM011', 's')]:
                selected = sorted([r for r in rr if r['family'].startswith('L') and r['label'] == mode], key=lambda r: r['active_length_m'])
                ax.plot([float(r['active_length_m'])*1000 for r in selected], [float(r[key])*scale for r in selected],
                        label=f'{solver} {mode}', color=colors[solver], marker=marker,
                        linestyle='-' if mode == 'TM010' else '--', fillstyle='none' if solver == 'Superfish' else 'full')
        ax.set(xlabel='空洞長 L [mm]', ylabel=title, xticks=[40, 80, 120]); ax.grid(alpha=.2)
    axes[0, 0].legend(fontsize=8)
    length = save(fig, 'length-sweep', '円筒の長さ掃引：40・80・120 mmの保存計算値。線は点を結ぶ目安。R/Q(circuit)はaccの1/2。', result_sources)

    half = document('results/half-domain-superfish.json')
    symmetry = document('raw/symmetry/comparison.json')
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    x = np.arange(len(half))
    for i, (key, label) in enumerate([('analytic_frequency_relative_error', '周波数'), ('analytic_q0_relative_error', 'Q₀')]):
        axes[0].bar(x+(i-.5)*.3, [r[key]*100 for r in half], width=.3, label=label)
    axes[0].set(xticks=x, xticklabels=[r['label'] for r in half], ylabel='解析値からの相対差 [%]', title='Superfish：半領域計算'); axes[0].legend()
    for key, label, marker in [('stored_energy_j', 'U', 'o'), ('wall_loss_w', 'P', 's'), ('frequency_hz', 'f', '^'), ('q0', 'Q₀', 'x')]:
        yy = [c['levels'][-1]['reflected'][key]/c['levels'][-1]['half'][key] for c in symmetry['cases']]
        axes[1].plot(range(len(yy)), yy, marker=marker, label=label, linestyle='--')
    axes[1].set(xticks=range(len(symmetry['cases'])), xticklabels=[c['name'].replace('-', '\n') for c in symmetry['cases']], ylabel='鏡映全領域 / 元半領域', title='NG：最細水準の鏡映不変量', ylim=(.8, 2.25))
    axes[1].legend(ncol=4, fontsize=8)
    half_plot = save(fig, 'half-domain', '半領域境界の確認。NGはU・Pが2倍、f・Q₀が不変。電圧とR/Qの単純な2倍換算は行わない。', ['results/half-domain-superfish.json', 'raw/symmetry/comparison.json'])

    rf = {}
    for family in ['flat4', 'rounded4', 'rounded7', 'flat-full', 'rounded-full']:
        fig, axes = plt.subplots(2, 2, figsize=(10, 6.6))
        for ax, (key, title, scale) in zip(axes.flat, metrics):
            for solver, rr in data.items():
                selected = [r for r in rr if r['family'] == family]
                selected.sort(key=lambda r: int(r['label'].split('*')[0].split()[0]))
                xx = [int(r['label'].split('*')[0].split()[0]) for r in selected]
                ax.plot(xx, [float(r[key])*scale for r in selected], marker='o' if solver == 'NG' else 'x',
                        linestyle='-' if solver == 'NG' else '--', color=colors[solver], label=solver)
            ax.set(ylabel=title, xlabel='軸上の零交差数' if 'full' in family else '同定した位相 θ/π', xticks=xx)
            if 'full' not in family: ax.set_xticklabels([f'{i}/{len(xx)-1}' for i in xx])
            ax.grid(alpha=.2)
        axes[0, 0].legend()
        rf[family] = save(fig, family+'-rf', f'{family}：場から対応づけた各モードの周波数・RF量。U=1 J、R/Qはacc定義。線は離散点の接続。' + ('フル端部同士の比較で、半セル端部との差を表す図ではない。' if 'full' in family else ''), result_sources)

    higher = document('results/higher-mode-checks.json')
    fig, axes = plt.subplots(1, 3, figsize=(11, 4.7))
    for ax, key, title in zip(axes, ['frequency_hz', 'q0', 'r_over_q_accelerator_ohm'], ['周波数', 'Q₀', 'R/Q (acc)']):
        for solver, prefix in [('NG', 'ng'), ('Superfish', 'superfish')]:
            ax.plot(range(len(higher)), [r[prefix+'_analytic_errors'][key]*100 for r in higher], 'o--', label=solver, color=colors[solver])
        ax.set(yscale='log', ylabel='解析値からの相対差 [%]', title=title, xticks=range(len(higher)))
        ax.set_xticklabels([r['label'] for r in higher], rotation=55, ha='right'); ax.grid(alpha=.2)
    axes[0].legend()
    higher_plot = save(fig, 'higher-mode-errors', '円筒7モードの独立解析比較。周波数・Q₀・R/Qを別々に表示。縦軸は対数で、場の誤差や表面ピーク精度とは異なる。', ['results/higher-mode-checks.json'])

    comparison = rows('relative-comparisons.csv')
    fig, axes = plt.subplots(3, 1, figsize=(11, 8), sharex=True)
    for ax, key, title in zip(axes, ['frequency_hz', 'r_over_q_accelerator_ohm', 'axis_relative_l2'], ['周波数の相対差 [%]', 'R/Q (acc)の相対差 [%]', '符号付き軸場の相対L²差 [%]']):
        yy = [float(r[key])*100 for r in comparison]
        ax.plot(range(len(yy)), yy, 'o', color='#007f88'); ax.set(ylabel=title, yscale='log'); ax.grid(alpha=.2)
    axes[-1].set_xticks(range(len(comparison)), [r['family']+'\n'+r['label'] for r in comparison], rotation=90, fontsize=7)
    comparison_plot = save(fig, 'solver-differences', '本家–NG比較の保存相対差×100。周波数・RF積分・軸場形状を分離して表示。表面ピークの精度判定ではない。', ['results/relative-comparisons.csv'])

    history = rows('mesh-history.csv')
    mesh_plots = ''
    for family in ['L080mm', 'flat4', 'rounded4', 'rounded7']:
        fig, axes = plt.subplots(2, 2, figsize=(10, 6.7))
        for col, solver in enumerate(['NG', 'Superfish']):
            rr = [r for r in history if r['family'] == family and r['solver'] == solver]
            for row, (key, title) in enumerate([('frequency_mhz', '周波数'), ('rq_acc_ohm', 'R/Q (acc)')]):
                ax = axes[row, col]
                if not rr:
                    ax.text(.5, .5, 'このCSVに細分履歴なし', ha='center', transform=ax.transAxes)
                    ax.set_axis_off(); continue
                labels = list(dict.fromkeys(r['label'] for r in rr))
                for label in labels:
                    selected = [r for r in rr if r['label'] == label]
                    values = np.array([float(r[key]) for r in selected]); yy = (values/values[-1]-1)*100
                    ax.plot(range(len(yy)), yy, 'o-', label=label, markersize=3)
                    # Different modes may have supplemental final meshes; annotate their exact labels in data.
                ax.set(title=f'{solver} / {title}', xlabel='保存細分水準（粗→細、系列ごと）', ylabel='各系列の最終保存値からの差 [%]')
                ax.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True)); ax.grid(alpha=.2)
                if row == 0: ax.legend(fontsize=7, ncol=2)
        mesh_plots += save(fig, 'mesh-'+family, f'{family}：CSV内の系列順で描画。最終点は比較基準なので差0。真の誤差や収束率の保証ではない。モードごとの分割値・追加細分は元CSVを参照。', ['results/mesh-history.csv'])

    # Relocate the original field plates without resampling or changing their values.
    for folder, title in [('01-superfish', '本家Superfish'), ('02-superfish-ng', 'Superfish-ng')]:
        original = record(base / folder / 'report.html').read_text()
        plates = re.findall(r'<figure><img src="figures/figure-\d+\.png">.*?</figure>', original, flags=re.S)
        assert len(plates) == 22, (folder, len(plates))
        for plate in plates: original = original.replace(plate, '', 1)
        grouped = {'basic': [], 'higher': [], 'flat4': [], 'rounded4': [], 'rounded7': []}
        for plate in plates:
            caption = re.search(r'<figcaption>(.*?)</figcaption>', plate).group(1)
            group = next((f for f in ['flat4','rounded4','rounded7'] if f in caption), None)
            if group is None: group = 'basic' if re.search(r'TM01[01]：', caption) else 'higher'
            grouped[group].append(plate)
            record(base / folder / re.search(r'src="([^"]+)"', plate).group(1))
        def before(heading, addition):
            nonlocal original
            assert original.count(heading) == 1
            original = original.replace(heading, addition + heading)
        # First place original images, then rewrite all original relative links.
        before('<h3>半領域境界の確認</h3>', ''.join(grouped['basic'])+'<!--LENGTH-->')
        before('<h2>5. 多セル空洞：全モードと分散</h2>', '<!--HALF-->')
        for family, next_heading in [('flat4','<h3>rounded4</h3>'), ('rounded4','<h3>rounded7</h3>'), ('rounded7','<h3>群速度の後処理</h3>')]:
            before(next_heading, ''.join(grouped[family])+f'<!--RF-{family}-->')
        before('<h2>6. 高次円筒モード・ビーズ測定用の参照場</h2>', '<!--ENDS-->')
        before('<h2>7. 本家–NGの差と数値検証</h2>', ''.join(grouped['higher'])+'<!--HIGHER-->')
        before('<h3>7セルπモードの小さいR/Qについて</h3>', '<!--DIFF-->')
        before('<h2>8. 対応できない計算と残る制約</h2>', '<!--MESH-->')
        original = original.replace('<h2>9. 場の図版と保存データ</h2>', '<h2>9. 場の図版と保存データ</h2><p>場の全22図を各実験節（第4〜6節）へ配置した。元の図番号を保持している。</p>')
        def rewrite(match):
            attr, target = match.groups()
            if target.startswith(('#', 'http:', 'https:', 'data:', 'mailto:')): return match.group(0)
            return f'{attr}="{html.escape(rel(base / folder / html.unescape(target)), quote=True)}"'
        for image_path in re.findall(r'<img src="([^"]+)"', original):
            record(base / folder / image_path)
        original = re.sub(r'(href|src)="([^"]+)"', rewrite, original)
        for token, addition in [('LENGTH',length), ('HALF',half_plot), ('ENDS',rf['flat-full']+rf['rounded-full']), ('HIGHER',higher_plot), ('DIFF',comparison_plot), ('MESH',mesh_plots)]+[(f'RF-{f}',rf[f]) for f in ['flat4','rounded4','rounded7']]:
            original = original.replace(f'<!--{token}-->', addition)
        original = re.sub(r'<img src="([^"]+)">', r'<img src="\1" alt="保存計算場・結果の図（説明は直後のキャプション）">', original)
        nav = '<nav class="screen"><a href="index.html">実験別の可視化索引</a> ／ <a href="'+folder+'.pdf">この可視化版のPDF</a></nav><p class="note">可視化追補版：保存済み数値をグラフ化し、場の図を実験節へ移した。計算の再実行はしていない。元の実行日・判定は原報告の記録。<a href="README.md">作成方法と来歴</a></p>'
        original = original.replace('<body>', '<body>'+nav)
        original = original.replace('</style>', 'figure img{display:block;width:100%;height:auto}figure{break-inside:avoid}nav{padding:14px;background:#e8f2f4}</style>')
        (out / (folder+'.html')).write_text(original)

    items = [('length-sweep','円筒・長さ掃引'), ('half-domain','半領域・対称境界'), ('flat4-rf','平坦4セル'), ('rounded4-rf','丸み付き4セル'), ('rounded7-rf','丸み付き7セル'), ('flat-full-rf','フル端部'), ('higher-mode-errors','高次モード・ビーズ参照場'), ('solver-differences','ソルバー比較'), ('mesh-rounded7','細分履歴')]
    table = ''.join('<tr><th>'+name+'</th>'+''.join(f'<td><a href="{f}.html#{key}">{label}</a></td>' for f,label in [('01-superfish','本家'),('02-superfish-ng','NG')])+'</tr>' for key,name in items)
    (out/'index.html').write_text('<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>実験別の可視化</title><style>body{font-family:system-ui;max-width:960px;margin:40px auto;padding:20px;line-height:1.8;color:#203044}table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccd;padding:12px;text-align:left}a{color:#126a86}</style><body><h1>実験別の可視化</h1><p>保存計算値から作った13図と、各冊の既存の場22図を実験節に収録。図はPNGと拡大用SVG、元データへのリンク付き。分散・群速度・周波数スキャン・ビーズ参照場の既存図も各節に保持。</p><p><a href="01-superfish.pdf">本家PDF</a> ／ <a href="02-superfish-ng.pdf">NG PDF</a> ／ <a href="'+rel(base/'index.html')+'">元の全体索引</a></p><table><tr><th>実験・診断</th><th>本家Superfish</th><th>Superfish-ng</th></tr>'+table+'</table><p>未実施のビーズによる周波数シフト、実機測定、非軸対称TM110は結果を作図せず、第8節の制約を保持する。</p><p><a href="README.md">作成方法・来歴</a> ／ <a href="manifest.json">図とデータの対応・SHA-256</a></p></body></html>')
    (out/'manifest.json').write_text(json.dumps({'source_root_relative':rel(base),'solver_rerun':False,'source_sha256':used,'figures':figures},ensure_ascii=False,indent=2)+'\n')
    (out/'README.md').write_text('# セミナーレポート可視化追補版\n\n[実験別索引](index.html)。原本2冊は変更せず、場22図/冊を実験節へ再配置し、保存CSV/JSONから13図を追加した。図の出典とSHA-256はmanifest.json。PNGとSVGは同じデータから生成する。新しい外部資料・依存はない。\n\n周波数・RF・場・細分差の意味を分け、未実施の測定値は補わない。鏡映量の比、相対差の百分率換算、各細分系列の最終保存値を基準とする差だけを後処理する。ソルバー・許容差・元の判定・数値出力は変更していない。\n\n再生成（NumPy/Matplotlibのある環境、出力先は未作成のディレクトリ）:\n```sh\n.venv/bin/python scripts/build_seminar_visualizations.py seminar-reports-20260910 --out seminar-reports-20260910/NEW_VISUAL_EDITION\n```\nPDFは生成HTMLをChromeの印刷でA4出力する。既存PDFは原版として保持。\n')
    print(json.dumps({'output':str(out),'new_figures':len(figures),'sources':len(used)},ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('delivery', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    build(args.delivery.resolve(), args.out.resolve())
