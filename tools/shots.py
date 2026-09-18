#!/usr/bin/env python3
"""Лист кадров сайта через headless Chromium (Playwright).
python3 shots.py <url> [--out DIR] [--w 1440] [--h 900] [--step 900] [--max 14] [--full]
Кадры пишутся в DIR (по умолчанию ./shots/<домен>/), имена 01.png, 02.png…
--full — дополнительно один кадр всей страницы целиком.
"""
import sys, os, re, time
from playwright.sync_api import sync_playwright

def main():
    a = sys.argv[1:]
    if not a: print(__doc__); return
    url = a[0]
    def opt(name, default):
        return a[a.index(name)+1] if name in a else default
    W, H = int(opt('--w', 1440)), int(opt('--h', 900))
    step, mx = int(opt('--step', 900)), int(opt('--max', 14))
    dom = re.sub(r'[^a-z0-9.-]', '_', re.sub(r'^https?://', '', url).split('/')[0])
    out = opt('--out', os.path.join('shots', dom)); os.makedirs(out, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': W, 'height': H}, device_scale_factor=2,
                        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
                                   '(KHTML, like Gecko) Chrome/124 Safari/537.36')
        pg.goto(url, wait_until='networkidle', timeout=60000)
        pg.wait_for_timeout(2500)
        total = pg.evaluate("document.body.scrollHeight")
        n = min(mx, max(1, -(-total // step)))
        files = []
        for i in range(n):
            pg.evaluate(f"window.scrollTo(0,{i*step})")
            pg.wait_for_timeout(1400)          # reveal-анимации
            f = os.path.join(out, f"{i+1:02d}.png"); pg.screenshot(path=f); files.append(f)
        if '--full' in a:
            f = os.path.join(out, "full.png"); pg.screenshot(path=f, full_page=True); files.append(f)
        print(f"высота {total}px, кадров {len(files)} → {out}")
        for f in files: print("  ", f)
        b.close()

if __name__ == '__main__':
    main()
