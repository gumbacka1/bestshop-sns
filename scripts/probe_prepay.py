# 엘지닷컴 구독 상세 페이지를 브라우저로 열어, 페이지가 받아 오는 선납 정보(선납 비율·금액·월 차감·할인)를 제품군별로 기록
import json, re
from playwright.sync_api import sync_playwright
CU = json.load(open('data/care_urls.json'))
P = json.load(open('data/lge_full/products.json'))
mid = {p['modelName']: p.get('modelId') for p in P}
W = ['S834MEE141','M876GBB231','D646GBB041','Z330MEEF21','Z386GBB281','OLED77C6QNA','OLED65C6SNA','75MRGB86BKA','WA2525YMP6R','FC2521UX6C','FG24EN','T19MX8A','RD25ESER','WD522MC','WD724RSB','SC5GMR80S','DUE6BGE','BEF3ASMLE','MH21BBY','32LX6BPGA','N95THO','FQ18EN9BE2','MX0120BASV','AS305DWWLM']
res = {}
with sync_playwright() as pw:
    b = pw.chromium.launch(); pg = b.new_page(viewport={'width': 1400, 'height': 1600}, locale='ko-KR')
    for m in W:
        u = CU.get(m) or next((v for k, v in CU.items() if k.startswith(m)), None)
        if not u or '/product/' not in u: res[m] = {'err': 'no url'}; continue
        got = {}
        def on(r):
            if 'subscription' in r.url and r.request.resource_type in ('xhr', 'fetch'):
                try: got[r.url] = r.json()
                except Exception: pass
        pg.on('response', on)
        try:
            pg.goto('https://www.lge.co.kr' + u, wait_until='domcontentloaded', timeout=60000); pg.wait_for_timeout(5000)
        except Exception as e: res[m] = {'err': str(e)[:80]}
        pg.remove_listener('response', on)
        d = {'url': u}
        for k, v in got.items():
            t = json.dumps(v, ensure_ascii=False)
            if '"prepayDiscount"' in t:
                pdis = re.search(r'"prepayDiscount": (\{.*?\})(?=, "cardBanner")', t)
                d['prepayDiscount'] = json.loads(pdis.group(1)) if pdis else None
                pr = re.search(r'"prepay": (\{"prepayRequired".*?\})(?=\}, \{|\}\])', t)
                if pr:
                    try: d['prepay'] = json.loads(pr.group(1))
                    except Exception: d['prepay_raw'] = pr.group(1)[:400]
            if 'total-fee?' in k: d['total_fee'] = v
            if '/options' in k and 'options/select' not in k: d['options'] = v
        for x in ('prepayDiscount',):
            if d.get(x): d[x].pop('tooltipMessages', None)
        res[m] = d; print('OK', m, json.dumps(d.get('prepayDiscount'), ensure_ascii=False)[:200], json.dumps(d.get('prepay') or d.get('prepay_raw'), ensure_ascii=False)[:200])
    b.close()
json.dump(res, open('prepay.json', 'w'), ensure_ascii=False, indent=1)
