# 엘지닷컴 구독 상세의 '케어서비스 소개 동영상'·케어 내용 수집 (품목·세부 분류별 대표 모델) → data/care_videos.json
import json, os, collections
from playwright.sync_api import sync_playwright
B = os.path.join(os.path.dirname(__file__), '..')
P = json.load(open(os.path.join(B, 'data/lge_full/products.json'), encoding='utf-8'))
pick = collections.OrderedDict()
for p in P:
    c = p.get('care') or {}
    if not c.get('price_map') or 'care-solutions' not in (c.get('url') or ''): continue
    key = (p.get('categoryName') or '', p.get('subCategoryName') or '')
    pick.setdefault(key, (p['modelName'], c['url']))
JS = '''() => { const out = {videos: [], title: '', items: [], cycle: ''};
 const sec = [...document.querySelectorAll('section,div,[role=region]')].find(e => (e.getAttribute('aria-label')||'').includes('케어십') || /케어서비스를 확인해보세요/.test(e.innerText||'')) || document;
 sec.querySelectorAll('video, video source, iframe').forEach(v => { const s = v.currentSrc || v.src || v.getAttribute('data-src') || ''; if (s) out.videos.push({src: s, poster: v.poster || ''}); });
 document.querySelectorAll('[data-video-src],[data-src$=".mp4"],[data-mp4]').forEach(v => out.videos.push({src: v.getAttribute('data-video-src') || v.getAttribute('data-src') || v.getAttribute('data-mp4'), poster: ''}));
 const h = [...document.querySelectorAll('h2')].find(e => /케어서비스를 확인해보세요/.test(e.innerText)); out.title = h ? h.innerText : '';
 out.items = [...document.querySelectorAll('h3')].map(e => e.innerText.trim()).filter(t => /분해|세척|A\\/S|점검|교체|케어|살균/.test(t)).slice(0, 12);
 const ul = [...document.querySelectorAll('li')].map(e => e.innerText.trim()).filter(t => /개월마다|개월 차|무상 A\\/S는/.test(t)); out.cycle = [...new Set(ul)].slice(0, 6).join(' / ');
 return out; }'''
res = {}
with sync_playwright() as pw:
    b = pw.chromium.launch(); pg = b.new_page(viewport={'width': 1280, 'height': 1600}, locale='ko-KR')
    for (cat, sub), (m, url) in pick.items():
        try:
            pg.goto(url, wait_until='domcontentloaded', timeout=60000); pg.wait_for_timeout(2500)
            for _ in range(8): pg.mouse.wheel(0, 2500); pg.wait_for_timeout(300)
            btn = pg.query_selector('button:has-text("케어서비스 소개 동영상 재생")')
            if btn:
                try: btn.click(timeout=3000); pg.wait_for_timeout(1500)
                except Exception: pass
            d = pg.evaluate(JS)
            d['videos'] = [v for i, v in enumerate(d['videos']) if v['src'] and v['src'] not in [w['src'] for w in d['videos'][:i]]]
            res[f'{cat}|{sub}'] = dict(model=m, url=url, **d); print(cat, sub, m, len(d['videos']), d['title'])
        except Exception as e:
            res[f'{cat}|{sub}'] = {'model': m, 'url': url, 'error': str(e)[:120]}
    b.close()
json.dump(res, open(os.path.join(B, 'data/care_videos.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('완료', len(res))
