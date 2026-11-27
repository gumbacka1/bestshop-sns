# 엘지닷컴 구독 상세 페이지를 브라우저로 열어 선납 선택 화면과 금액을 그대로 읽음
import json, sys
from playwright.sync_api import sync_playwright
url = 'https://www.lge.co.kr/product/care-solutions/refrigerators/s834mee141'
seen = []
with sync_playwright() as pw:
    b = pw.chromium.launch(); pg = b.new_page(viewport={'width': 1400, 'height': 1600}, locale='ko-KR')
    def on_resp(r):
        if 'subscription' in r.url and r.request.resource_type in ('xhr', 'fetch'):
            try: seen.append({'url': r.url, 'body': r.json()})
            except Exception: pass
    pg.on('response', on_resp)
    pg.goto(url, wait_until='domcontentloaded', timeout=60000); pg.wait_for_timeout(5000)
    for _ in range(6): pg.mouse.wheel(0, 1500); pg.wait_for_timeout(400)
    txt = pg.inner_text('body')
    i = 0
    for k in range(8):
        i = txt.find('선납', i + 1)
        if i < 0: break
        print('TXT', txt[max(0, i - 200):i + 300].replace('\n', ' / '))
    els = pg.query_selector_all('button, label, [role=radio], [role=tab], option, a')
    for e in els:
        t = (e.inner_text() or '').strip()
        if '선납' in t or '%' in t and len(t) < 20: print('EL', e.evaluate('x=>x.tagName'), t[:60])
    pg.screenshot(path='shot.png', full_page=False)
    b.close()
json.dump(seen, open('prepay.json', 'w'), ensure_ascii=False, indent=1)
print('RESP', len(seen), [s['url'][:140] for s in seen][:20])
