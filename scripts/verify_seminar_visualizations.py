"""Verify a visual edition; optionally print its PDFs with isolated headless Chrome."""
from __future__ import annotations

import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess
import tempfile
from urllib.parse import unquote, urlsplit


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs = []
        self.ids = []
        self.images = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        for key in ('href', 'src'):
            if key in attrs:
                self.refs.append(attrs[key])
        if tag == 'img':
            self.images += 1
            if not attrs.get('alt'):
                raise ValueError('Image without alternative text')


def verify(out: Path, render_pdf: bool):
    manifest = json.loads((out / 'manifest.json').read_text())
    base = (out / manifest['source_root_relative']).resolve()
    records = []
    for name in ('01-superfish', '02-superfish-ng'):
        pdf = out / (name + '.pdf')
        if render_pdf:
            if pdf.exists():
                raise FileExistsError(f'Keep existing PDF; use a fresh edition: {pdf}')
            with tempfile.TemporaryDirectory(prefix='seminar-visual-chrome-') as profile:
                command = ['google-chrome', '--headless', '--disable-gpu',
                           '--disable-background-networking', '--disable-extensions',
                           '--no-first-run', '--no-default-browser-check',
                           f'--user-data-dir={profile}', '--no-pdf-header-footer',
                           f'--print-to-pdf={pdf}', (out / (name + '.html')).as_uri()]
                result = subprocess.run(command, capture_output=True, text=True, timeout=120)
                (out / (name + '-print.log')).write_text(result.stdout + result.stderr)
                result.check_returncode()
        info = subprocess.check_output(['pdfinfo', str(pdf)], text=True)
        text = subprocess.check_output(['pdftotext', '-layout', str(pdf), '-'], text=True)
        for expected in ('可視化追補版', '円筒の長さ掃引', '半領域境界の確認',
                         '最終点は比較基準', 'フォルダ構成'):
            if expected not in text:
                raise ValueError(f'{name}: missing PDF text {expected}')
        records.append({'name': name, 'pdfinfo': info, 'text_verified': True})

    checked = 0
    images = {}
    for path in out.glob('*.html'):
        page = Page()
        page.feed(path.read_text())
        if len(page.ids) != len(set(page.ids)):
            raise ValueError(f'Duplicate anchors: {path}')
        images[path.name] = page.images
        if path.stem != 'index' and page.images != 22 + 7 + len(manifest['figures']):
            raise ValueError(f'Wrong image count: {path}')
        for ref in page.refs:
            url = urlsplit(ref)
            if url.scheme:
                continue
            target = (path.parent / unquote(url.path)).resolve() if url.path else path
            if not target.is_relative_to(base) or not target.exists():
                raise ValueError(f'Broken or external path: {path}: {ref}')
            if url.fragment:
                linked = Page()
                linked.feed(target.read_text())
                if url.fragment not in linked.ids:
                    raise ValueError(f'Broken anchor: {path}: {ref}')
            checked += 1
    for path, expected in manifest['source_sha256'].items():
        if hashlib.sha256((base / path).read_bytes()).hexdigest() != expected:
            raise ValueError(f'Source changed: {path}')
    result = {'passed': True, 'pdf': records, 'local_links_checked': checked,
              'images': images, 'new_figures': len(manifest['figures']),
              'source_hashes_verified': len(manifest['source_sha256'])}
    (out / 'verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('edition', type=Path)
    parser.add_argument('--render-pdf', action='store_true')
    args = parser.parse_args()
    verify(args.edition.resolve(), args.render_pdf)
