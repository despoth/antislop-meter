#!/usr/bin/env node
/* Лист кадров для антислопометра.
   node shots.js <url> [--out DIR] [--w 1440] [--h 900] [--frames 8] [--wait 1200] [--full]
   Кадры снимаются со скроллом, анимации успевают отработать. */
const path = require('path'), fs = require('fs');
const NM = [
  path.join(process.env.HOME, '.claude/skills/antislop/tools/node_modules'),
  '/Users/alexeykolpikov/!-WORK/!-REFERENCES/Lebedev/tools/node_modules',
];
let chromium;
for (const p of NM) { try { ({ chromium } = require(path.join(p, 'playwright-core'))); break; } catch (e) {} }
if (!chromium) { console.error('playwright-core не найден'); process.exit(1); }

const a = process.argv.slice(2);
const url = a[0];
const opt = (k, d) => { const i = a.indexOf('--' + k); return i > -1 ? a[i + 1] : d; };
const flag = k => a.includes('--' + k);
const OUT = opt('out', path.join(process.env.TMPDIR || '/tmp', 'shots-' + new URL(url).hostname.replace(/\W/g, '-')));
const W = +opt('w', 1440), H = +opt('h', 900), FRAMES = +opt('frames', 8), WAIT = +opt('wait', 1200), SCALE = +opt('scale', 2);

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const root = path.join(process.env.HOME, 'Library/Caches/ms-playwright');
  const cands = [];
  for (const d of fs.readdirSync(root).filter(d => d.startsWith('chromium')).sort().reverse()) {
    cands.push(
      path.join(root, d, 'chrome-mac-arm64/Chromium.app/Contents/MacOS/Chromium'),
      path.join(root, d, 'chrome-mac/Chromium.app/Contents/MacOS/Chromium'),
      path.join(root, d, 'chrome-headless-shell-mac-arm64/chrome-headless-shell'),
      path.join(root, d, 'chrome-headless-shell-mac/chrome-headless-shell'));
  }
  cands.push('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome');
  const exe = cands.find(p => fs.existsSync(p));
  if (!exe) { console.error('браузер не найден'); process.exit(1); }
  const browser = await chromium.launch({
    headless: true, executablePath: exe,
    args: ['--hide-scrollbars', '--autoplay-policy=no-user-gesture-required', '--force-device-scale-factor=' + SCALE],
  });
  const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: SCALE });
  await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 }).catch(() => {});
  await page.waitForTimeout(2500);
  const total = await page.evaluate(() => document.body.scrollHeight);
  const step = Math.max(1, Math.round((total - H) / Math.max(1, FRAMES - 1)));
  const files = [];
  for (let i = 0; i < FRAMES; i++) {
    const y = i * step;
    await page.evaluate(v => window.scrollTo({ top: v, behavior: 'instant' }), y);
    await page.waitForTimeout(WAIT);
    const f = path.join(OUT, String(i + 1).padStart(2, '0') + '.png');
    await page.screenshot({ path: f });
    files.push(f);
  }
  if (!flag('nofull')) {
    const f = path.join(OUT, 'full.png');
    await page.screenshot({ path: f, fullPage: true });
    files.push(f);
  }
  await browser.close();
  console.log('высота страницы: ' + total + 'px, шаг ' + step + 'px');
  files.forEach(f => console.log(f));
})();
