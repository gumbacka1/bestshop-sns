# 베스트샵(bestshop.lge.co.kr) 판촉 수집 → data/lge_full/bestshop_promos.json
# 이벤트 목록·상세, 행사 매장(오픈·지점별), 웨딩·기업·입주 혜택 페이지의 제목·기간·혜택 문구·이미지 링크.
import json, re, os, sys, time, html as H, datetime, urllib.request, urllib.parse, urllib.error

BASE = 'https://bestshop.lge.co.kr'
UA = 'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/124 Mobile Safari/537.36'
OUT = os.path.join(os.path.dirname(__file__), '..', 'data', 'lge_full')
SEEDS = ['/', '/event/list/all', '/event/list/ing', '/event/list/benefit', '/event/list/subscribe',
         '/shop/eventStoreList/open', '/shop/eventStoreList/branch', '/benefit/certifyBenefit/wedding',
         '/benefit/certifyBenefit/company', '/benefit/aptBenefitList', '/event/detail/EV10571002',
         '/event/detail/EV11062002', '/event/liveBroadcast']
LINK = re.compile(r'(/event/detail/EV\d+|/shop/eventStore[A-Za-z]*/[A-Za-z0-9_-]+|/shop/eventStoreDetail[^"\'\s<>]*|'
                  r'/benefit/[A-Za-z]+(?:/[A-Za-z0-9_-]+)?|/event/list/[a-z]+|/shop/[a-zA-Z]+Detail[^"\'\s<>]*)')


def get(url, data=None, tries=3):
    err = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers={'User-Agent': UA, 'Accept-Language': 'ko-KR,ko;q=0.9',
                                                                   **({'X-Requested-With': 'XMLHttpRequest'} if data else {})})
            with urllib.request.urlopen(req, timeout=40) as r:
                return r.read().decode('utf-8', 'ignore')
        except urllib.error.HTTPError as e:
            err = e
            if e.code in (400, 404, 410): break
            time.sleep(2 + i * 3)
        except Exception as e:
            err = e; time.sleep(2 + i * 3)
    print('실패', url, err, file=sys.stderr)
    return ''


def text_of(h, cap=40000):
    h = re.sub(r'(?is)<(script|style|noscript)[^>]*>.*?</\1>', ' ', h)
    h = re.sub(r'(?i)<br\s*/?>|</(p|li|tr|div|h\d|dt|dd|strong)>', '\n', h)
    h = re.sub(r'(?i)</t[dh]>', ' | ', h)
    t = H.unescape(re.sub(r'<[^>]+>', ' ', h))
    L = [re.sub(r'[ \t ]+', ' ', x).strip(' |') for x in t.split('\n')]
    return '\n'.join(x for x in L if x)[:cap]


def imgs(raw):
    h = raw.replace('\\/', '/')
    out = []
    for u in re.findall(r'(?:https?:)?//[^"\'\s)<>]+?\.(?:jpg|jpeg|png|webp|gif)', h) + \
             ['https://static-best.lge.co.kr' + x for x in re.findall(r'["\'(](/kr/upload/[^"\'\s)<>]+?\.(?:jpg|jpeg|png|webp|gif))', h)]:
        u = ('https:' + u) if u.startswith('//') else u
        if re.search(r'img_sns_share|/icons?/|logo|btn_|ico_|favicon|/common/', u): continue
        if u not in out: out.append(u)
    return out[:80]


def page(path):
    raw = get(BASE + path)
    if not raw: return None, raw
    t = text_of(raw)
    title = re.search(r'<title>([^<]{1,200})</title>', raw)
    og = re.search(r'property="og:title"\s+content="([^"]{1,200})"', raw)
    lines = t.split('\n')
    d = {'url': BASE + path, 'title': H.unescape((og or title).group(1)).strip() if (og or title) else '',
         '기간': [x for x in lines if re.search(r'20\d\d[.\-/]\s?\d{1,2}[.\-/]\s?\d{1,2}', x) and len(x) < 120][:6],
         '혜택': [x for x in lines if re.search(r'\d+\s*%|\d[\d,]*\s*(만\s*)?(원|P|포인트)|캐시백|사은품|할인|증정|무료', x) and len(x) < 200][:80],
         '조건': [x for x in lines if re.search(r'대상|조건|유의|제외|한정|기간|구매 시|구독 시', x) and len(x) < 200][:40],
         'text': t,
         'images': imgs(raw)}
    return d, raw


def main():
    os.makedirs(OUT, exist_ok=True)
    seen, queue, pages, endpoints = set(), list(SEEDS), {}, set()
    while queue and len(seen) < 400:
        p = queue.pop(0)
        if p in seen: continue
        seen.add(p)
        d, raw = page(p)
        time.sleep(0.4)
        if not raw: continue
        if d: pages[p] = d
        for e in re.findall(r'["\'](/[A-Za-z0-9/_.-]*(?:ajax|api|Ajax|Api)[A-Za-z0-9/_.-]*)["\']', raw):
            endpoints.add(e)
        for l in LINK.findall(raw):
            l = H.unescape(l).split('#')[0]
            if l not in seen and l not in queue: queue.append(l)
    # 목록 API 시도(있으면 이벤트를 더 찾는다)
    for e in sorted(endpoints):
        if re.search(r'event|Event|store|Store|benefit|Benefit', e) and len(e) < 120:
            for body in (None, b'page=1&pageSize=100', b'currentPage=1&rowCount=100'):
                t = get(BASE + e, body, tries=1)
                for l in LINK.findall(t or ''):
                    if l not in seen:
                        d, raw = page(l); seen.add(l); time.sleep(0.4)
                        if d: pages[l] = d
                if t: break
    from collections import Counter
    cnt = Counter(x for v in pages.values() for x in set(v['text'].split('\n')))
    common = {x for x, c in cnt.items() if c >= max(5, len(pages) * 0.3)}
    for v in pages.values():
        for k in ('혜택', '조건', '기간'):
            v[k] = [x for x in v[k] if x not in common]
        v['text'] = '\n'.join(x for x in v['text'].split('\n') if x not in common)
    ev = {k: v for k, v in pages.items() if '/event/detail/' in k}
    out = {'updated': (datetime.datetime.utcnow() + datetime.timedelta(hours=9)).strftime('%Y-%m-%d %H:%M'),
           '페이지수': len(pages), '이벤트수': len(ev), 'endpoints': sorted(endpoints)[:200], 'pages': pages}
    json.dump(out, open(os.path.join(OUT, 'bestshop_promos.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print('베스트샵 판촉', out['페이지수'], '페이지, 이벤트', out['이벤트수'])


if __name__ == '__main__':
    main()
