# Ось G: модульная сетка, узлы, силовые линии, сдвоенные волоски, рамка в рамке.
# python3 grid.py <url> [url...]
import sys, asyncio
from playwright.async_api import async_playwright

JS = r"""() => {
  const W = innerWidth, vis = [];
  document.querySelectorAll('h1,h2,h3,h4,p,img,video,figure,button,a[class],li,[class*=card],[class*=item],[class*=tile],[class*=col]').forEach(e => {
    const r = e.getBoundingClientRect(), s = getComputedStyle(e);
    if (s.display === 'none' || s.visibility === 'hidden') return;
    if (r.width < 60 || r.height < 24) return;
    if (r.width > W * 0.96) return;
    if (r.top > 24000) return;
    vis.push({ l: Math.round(r.left), r: Math.round(r.right), w: Math.round(r.width) });
  });
  // волоски: элементы толщиной <=2px и длиной >120px + бордеры
  const lines = [];
  document.querySelectorAll('*').forEach(e => {
    const r = e.getBoundingClientRect(), s = getComputedStyle(e);
    if (r.width < 4 && r.height < 4) return;
    if (s.visibility === 'hidden' || s.display === 'none') return;
    const solid = s.backgroundColor !== 'rgba(0, 0, 0, 0)' && s.backgroundColor !== 'transparent';
    if (r.height <= 2 && r.width > 120 && solid) lines.push({ o: 'h', p: Math.round(r.top), a: Math.round(r.left), b: Math.round(r.right) });
    if (r.width <= 2 && r.height > 120 && solid) lines.push({ o: 'v', p: Math.round(r.left), a: Math.round(r.top), b: Math.round(r.bottom) });
    ['Top','Bottom'].forEach(k => { if (parseFloat(s['border'+k+'Width']) > 0 && parseFloat(s['border'+k+'Width']) <= 2 && r.width > 120)
      lines.push({ o: 'h', p: Math.round(k === 'Top' ? r.top : r.bottom), a: Math.round(r.left), b: Math.round(r.right) }); });
    ['Left','Right'].forEach(k => { if (parseFloat(s['border'+k+'Width']) > 0 && parseFloat(s['border'+k+'Width']) <= 2 && r.height > 120)
      lines.push({ o: 'v', p: Math.round(k === 'Left' ? r.left : r.right), a: Math.round(r.top), b: Math.round(r.bottom) }); });
  });
  // рамка в рамке
  let nested = 0; const framed = [...document.querySelectorAll('*')].filter(e => {
    const s = getComputedStyle(e), r = e.getBoundingClientRect();
    return r.width > 100 && r.height > 60 && ['Top','Right','Bottom','Left'].every(k => parseFloat(s['border'+k+'Width']) > 0);
  });
  framed.forEach(e => { if (framed.some(o => o !== e && o.contains(e))) nested++; });
  return { W, blocks: vis, lines, nested, framed: framed.length };
}"""

def analyse(d):
    W, blocks = d['W'], d['blocks']
    if len(blocks) < 6: return None
    edges = sorted(b['l'] for b in blocks)
    # силовые линии: кластеры левых краёв в пределах 6px
    clusters, cur = [], [edges[0]]
    for e in edges[1:]:
        if e - cur[-1] <= 6: cur.append(e)
        else: clusters.append(cur); cur = [e]
    clusters.append(cur)
    clusters.sort(key=len, reverse=True)
    power = [(round(sum(c)/len(c)), len(c)) for c in clusters if len(c) >= 3]
    on_power = sum(n for _, n in power[:3])
    # подбор колоночной сетки: margin + k*step
    best = None
    origins = sorted({min(edges)} | {x for x, _ in power[:4]})
    for margin in origins:
        for cols in (4, 6, 8, 12):
            for gut in (0, 16, 20, 24, 32, 40):
                step = (W - 2*margin - gut*(cols-1)) / cols + gut
                if step < 40: continue
                hit = sum(1 for b in blocks if abs((b['l']-margin) - round((b['l']-margin)/step)*step) <= 4)
                score = hit/len(blocks)
                if not best or score > best[0]: best = (score, cols, round(step), gut)
    # сдвоенные волоски
    pairs = 0
    for o in ('h', 'v'):
        L = sorted([x for x in d['lines'] if x['o'] == o], key=lambda x: x['p'])
        for i in range(len(L)-1):
            a, b = L[i], L[i+1]
            if 0 < b['p'] - a['p'] <= 14 and min(a['b'], b['b']) - max(a['a'], b['a']) > 100: pairs += 1
    return {'blocks': len(blocks), 'power': power[:3], 'on_power': on_power,
            'snap': best, 'pairs': pairs, 'nested': d['nested'], 'framed': d['framed']}

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={'width': 1440, 'height': 900})
        print(f"{'страница':<14}{'блоков':>7}{'в узлах':>9}{'сетка':>9}{'силовые линии':>28}{'волоски':>9}{'рамка²':>8}")
        for u in sys.argv[1:]:
            name = u.rstrip('/').split('/')[-1] or 'hub'
            try:
                await pg.goto(u, wait_until='networkidle', timeout=45000)
                await pg.wait_for_timeout(2500)
                r = analyse(await pg.evaluate(JS))
                if not r: print(f"{name:<14} мало блоков"); continue
                sc, cols, step, gut = r['snap']
                pw = ' · '.join(f"{x}px×{n}" for x, n in r['power']) or 'нет'
                share = round(r['on_power']/r['blocks']*100)
                print(f"{name:<14}{r['blocks']:>7}{str(round(sc*100))+'%':>9}{str(cols)+'кол':>9}{pw:>28}{r['pairs']:>9}{r['nested']:>8}   линии держат {share}%")
            except Exception as e:
                print(f"{name:<14} ошибка {str(e)[:50]}")
        await b.close()

asyncio.run(main())
