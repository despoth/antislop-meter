#!/usr/bin/env python3
# Антислопометр: быстрый разбор маркеров по URL. python3 probe.py <url> [url...]
import re, sys, json, urllib.request, urllib.error

UA = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124 Safari/537.36'}

MARK = {
 'D-05 счётчики':      r'\b\d{1,3}[\s ]?(\+|K|К|млн|k)\b(?=[^<]{0,40}(лет|years|клиент|client|проект|project|час|hour|ингредиент))',
 'D-10 эмодзи':        r'[\U0001F300-\U0001FAFF✨✅⭐]',
 'D-14 блоб/свечение': r'(radial-gradient|filter:\s*blur|backdrop-filter)',
 'D-15 градиент':      r'linear-gradient\([^)]{0,80}(#|rgb)',
 'D-16 тени/скругл.':  r'(box-shadow:[^;]{3,40}|border-radius:\s*(1[2-9]|2[0-9])px)',
 'D-19 дефолт-шрифт':  r'family=(Inter|Roboto|Manrope|Poppins|Montserrat|Space\+Grotesk|Sora|Plus\+Jakarta)',
 'D-22 Unbounded':     r'family=(Unbounded|Jost|Comfortaa|Questrial)',
 'U-05 рубрика':       r'(Почему мы|Наши преимущества|О нас|Why (choose )?us|What (our )?clients say|Trusted by|Our Services|Наши услуги|Как мы работаем)',
 'U-06 штампы':        r'(индивидуальн\w+ подход|высокое качество|команда профессионал|с любовью|под ключ|лучш\w+ цен|premium quality|passionate team|tailored approach)',
 'U-13 отзыв безым.':  r'([А-ЯA-Z][а-яa-z]+\s+[А-ЯA-Z]\.)(?=[^<]{0,30}(отзыв|клиент|Client|Customer))',
 'U-16 форма-звонок':  r'(Заполните форму|Оставьте заявку|Заказать звонок|Перезвоните мне|Нажимая на кнопку)',
 'P-01 дефицит':       r'(осталось \d|количество мест ограничен|limited (time|spots|offer)|только сегодня|успейте)',
 'P-02 таймер':        r'(data-countdown|id="timer"|обратный отсчёт|сгорит через|ends in)',
 'P-03 скидка/зачёрк': r'(<s>|text-decoration:\s*line-through|скидк|discount|-\d{2}%)',
 'X-05 превосх.':      r'(лучш(ий|ая|ие)|revolutionary|cutting-edge|world-class|№\s?1|best-in-class|уникальн)',
 'E-01 хардкод цвета': r'style="[^"]{0,60}(color|background)\s*:\s*(#|rgb)',
 'E-02 шрифт по месту':r'style="[^"]{0,60}font-(family|size)',
 'E-04 мёртвый блок':  r'style="[^"]{0,40}display\s*:\s*none',
}

# Подключено, но не использовано (E-03): имя в <head> есть, вызовов нет.
LIBS = {
 'GSAP':        (r'gsap[^"\']{0,30}\.js',            r'gsap\.(to|from|fromTo|timeline|registerPlugin)'),
 'ScrollTrigger':(r'ScrollTrigger[^"\']{0,20}\.js',  r'ScrollTrigger\.(create|refresh)|scrollTrigger\s*:'),
 'Swiper':      (r'swiper[^"\']{0,30}\.(js|css)',    r'new\s+Swiper|swiper-slide'),
 'jQuery':      (r'jquery[^"\']{0,30}\.js',          r'\$\(|jQuery\('),
 'Lottie':      (r'lottie[^"\']{0,30}\.js',          r'lottie\.(loadAnimation|play)|<lottie-player'),
 'AOS':         (r'aos[^"\']{0,20}\.(js|css)',       r'AOS\.init|data-aos'),
 'Lenis':       (r'lenis[^"\']{0,20}\.js',           r'new\s+Lenis'),
 'Three.js':    (r'three[^"\']{0,20}\.js',           r'THREE\.(Scene|WebGLRenderer)'),
}

# Техническая опрятность (R-12…R-16).
TIDY = {
 'R-12 alt':      r'<img[^>]+alt="[^"]{4,}"',
 'R-14 фавикон':  r'rel="(icon|shortcut icon|apple-touch-icon)"',
 'R-15 retina':   r'(srcset=|[@ ]2x|\.avif|sizes=")',
 'R-16 SEO':      r'(property="og:|name="description"|application/ld\+json)',
}

def get(u):
    import subprocess
    try:
        r = subprocess.run(['curl','-sL','--compressed','--max-time','20','-A',UA['User-Agent'],u],
                           capture_output=True, timeout=25)
        return r.stdout.decode('utf-8','ignore')
    except Exception:
        return ''

def txt(h):
    h = re.sub(r'<(script|style|noscript)[^>]*>.*?</\1>', ' ', h, flags=re.S)
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', h))

def probe(u):
    h = get(u)
    if not h: return {'url': u, 'error': 'нет ответа'}
    t = txt(h)
    hs = [re.sub(r'<[^>]+>', '', x).strip() for x in re.findall(r'<h[123][^>]*>.*?</h[123]>', h, flags=re.S)]
    hs = [re.sub(r'\s+', ' ', x) for x in hs if 3 < len(x) < 70]
    found = {k: len(re.findall(v, h if k.startswith(('D-14','D-15','D-16','D-19','D-22','P-02')) else t, re.I|re.U))
             for k, v in MARK.items()}
    dead = [n for n, (load, use) in LIBS.items() if re.search(load, h, re.I) and not re.search(use, h, re.I)]
    tidy = [k for k, v in TIDY.items() if re.search(v, h, re.I)]
    ctas = re.findall(r'(Заказать|Оставить заявку|Узнать больше|Записаться|Связаться|Рассчитать стоимость|Get started|Book (a|now)|Contact us|Learn more|Get a free quote)', t, re.I)
    return {'url': u, 'kb': len(h)//1024, 'h_count': len(hs), 'heads': hs[:6],
            'cta_repeat': len(ctas), 'dead': dead, 'tidy': tidy, 'marks': {k: v for k, v in found.items() if v}}

if __name__ == '__main__':
    out = [probe(u) for u in sys.argv[1:]]
    for r in out:
        if r.get('error'): print(f"— {r['url']}: {r['error']}"); continue
        m = ', '.join(f"{k}×{v}" for k, v in sorted(r['marks'].items(), key=lambda x: -x[1]))
        print(f"— {r['url']}  [{r['kb']}КБ, h={r['h_count']}, CTA×{r['cta_repeat']}]")
        print(f"   {m if m else 'маркеров нет'}")
        if r.get('dead'): print(f"   E-03 подключено и не использовано: {', '.join(r['dead'])}")
        print(f"   опрятность: {', '.join(r['tidy']) if r.get('tidy') else 'ничего из R-12…R-16'}")
        if r['heads']: print(f"   заголовки: {' | '.join(r['heads'][:5])}")
