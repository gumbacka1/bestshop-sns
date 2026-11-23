# 엘지닷컴 베스트 랭킹(일시불·구독) 수집 → data/lge_dotcom.json
# 닷컴 비교 판매(관리자 화면)용. 표준 라이브러리만 사용.
import json, re, time, urllib.request, urllib.parse, datetime, os, sys

BASE = 'https://www.lge.co.kr'
API = BASE + '/mkt/api/bestRanking/retrieveCategoryProductList.lgajax'
UA = 'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/124 Mobile Safari/537.36'
OUT = os.path.join(os.path.dirname(__file__), '..', 'data', 'lge_dotcom.json')

# key, 이름, 일시불 카테고리, 구독 카테고리, 세부 분류
CATS = [
    ('tv', 'TV', 'CT50000025', 'CT50238002', ['OLED TV', 'LED TV']),
    ('ref', '냉장고', 'CT50000065', 'CT50178000', ['양문형', '600L급', '800L급']),
    ('wm', '세탁기', 'CT50000101', 'CT50136000', ['드럼', '통돌이']),
    ('dr', '건조기', 'CT50000107', 'CT50000178', ['건조기']),
    ('wt', '워시타워', 'CT50387000', 'CT50390000', ['워시타워', '워시콤보']),
    ('ac', '에어컨', 'CT50000131', 'CT50080000', ['2in1', '스탠드', '벽걸이']),
]
LINES = ['컴팩트', '매직스페이스', 'Fit & Max', '컨버터블', '뷰', '위너', '쿨', '타워', '듀얼쿨', '사계절',
         'OLED', 'evo', 'QNED', 'NANO', '나노셀', 'Mini RGB', '울트라 HD', '일반 LED', '통돌이', '컴포트',
         '오브제컬렉션', 'AI', '워시콤보', '미니워시', '양문형']
SKIP_SPEC = re.compile(r'모델명|KC|인증|정격|제조|품질|A/S|소비전력|무게|기본 코스|클라우드|코스목록|도어 열림|전자파|출시년월|색상|고지|크기 \(박스|포장')


def get(url, data=None, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers={'User-Agent': UA, 'X-Requested-With': 'XMLHttpRequest',
                                                                   'Accept-Language': 'ko-KR,ko;q=0.9'})
            with urllib.request.urlopen(req, timeout=40) as r:
                return r.read().decode('utf-8', 'ignore')
        except Exception as e:
            err = e
            time.sleep(2 + i * 3)
    print('실패', url, err, file=sys.stderr)
    return ''


def ranking(kind, cid):
    body = urllib.parse.urlencode({'rankingType': kind, 'categoryId': cid}).encode()
    t = get(API, body)
    try:
        d = json.loads(t)['data'][0]
        return d.get('subscribeRankingList' if kind == 'subscribe' else 'bestRankingProductList') or []
    except Exception:
        return []


def num(s):
    m = re.search(r'[\d.]+', s or '')
    return float(m.group()) if m else 0.0


def size(p):
    for k in ('keywdNmA', 'keywdNmB'):
        t = p.get(k) or ''
        if re.search(r'(cm|L|kg|Kg|㎡)', t):
            return t
    return ''


def grade(p):
    for k in ('keywdNmA', 'keywdNmB'):
        t = p.get(k) or ''
        if '등급' in t:
            return t
    return ''


def group(c, p):
    n = p.get('modelName', ''); s = p.get('subCategoryName') or ''; v = num(size(p))
    if c == 'tv': return 'OLED TV' if n.startswith('OLED') else 'LED TV'
    if c == 'ref':
        if s == '양문형': return '양문형'
        if 800 <= v < 900: return '800L급'
        if 600 <= v < 700: return '600L급'
        return None
    if c == 'wm': return '드럼' if '드럼' in s else '통돌이'
    if c == 'dr': return '건조기'
    if c == 'wt': return '워시콤보' if '콤보' in s else '워시타워'
    if c == 'ac': return '벽걸이' if '벽걸이' in s else ('2in1' if '2in1' in s else '스탠드')


def short(name):
    n = (name or '').replace('LG ', '', 1)
    return re.sub(r'\s+', ' ', n).strip()


def item(c, p, rank, sub=False):
    return {
        'm': p['modelName'], 'n': short(p.get('modelDisplayName')), 'sz': size(p), 'gr': grade(p),
        'rel': (p.get('modelReleaseDate') or '')[:7], 'price': p.get('obsSellingPrice') or 0,
        'orig': p.get('obsOriginalPrice') or 0, 'max': p.get('maxBenefitPrice') or 0,
        'img': ('https://static.lge.co.kr' + p['mediumImageAddr']) if p.get('mediumImageAddr') else '',
        'only': p.get('lgecomOnlyFlag') == 'Y', 'bts': int(p.get('btsOrdQty') or 0), 'obs': int(p.get('obsOrdQty') or 0),
        'r': rank, 'url': BASE + (p.get('modelUrlPath') or ''), 'g': group(c, p), 'desc': p.get('productPriceDesc') or '',
        'sub': sub,
    }


def lines(name):
    return {t for t in LINES if t in (name or '')}


def match(p, cands):
    v = num(p['sz']); ln = lines(p['n'])
    pool = [q for q in cands if not q['only'] and q['m'] != p['m'] and q['g'] == p['g']]
    for tier in ('2026', '2025'):
        c = [q for q in pool if (q['rel'][:4] >= '2026' if tier == '2026' else q['rel'][:4] == '2025')]
        if not c: continue
        def key(q):
            d = abs(num(q['sz']) - v)
            far = d > max(v * 0.15, 0.1) if v else False
            return (far, -len(ln & lines(q['n'])), d, -q['bts'])
        c.sort(key=key)
        q = c[0]
        d = abs(num(q['sz']) - v)
        return q['m'], (d > v * 0.15) if v else False
    return None, False


def page_specs(url):
    h = get(url).replace('\\"', '"')
    out = {}
    for n, val in re.findall(r'\{"name":"([^"]{1,40})","value":"([^"]{0,200})"', h):
        if n not in out and not val.startswith('\\u003c'):
            out[n] = val.replace('\\n', ' ').strip()
    sold = re.search(r'판매되는 제품은\s*([^<"\\]{1,30})입니다', h)
    return out, (sold.group(1).strip() if sold else ''), h


def care_prices(html):
    h = html.replace('\\"', '"')
    m = re.search(r'"priceMap":(\{.*?\}\}),"partnerPriceMap"', h)
    if not m: return None
    try:
        pm = json.loads(m.group(1))
    except Exception:
        return None
    cur = re.search(r'"currentSelection":"(\d+)((?:_\w+)*)"', h)
    suf = cur.group(2) if cur else None
    res = {}
    for k, v in pm.items():
        if not isinstance(v, dict): continue
        t = k.split('_')[0]
        if suf is not None and k[len(t):] != suf: continue
        res[t] = {'p': v.get('monthlyPrice'), 'o': v.get('originalPrice')}
    care = re.search(r'"careServiceTypes":\[\{"value":"\d+","label":"([^"]{1,80})"', h)
    cyc = re.search(r'"careServiceCycles":\[\{"value":"\d+","label":"([^"]{1,30})"', h)
    return {'terms': res, 'care': care.group(1) if care else '', 'cycle': cyc.group(1) if cyc else ''}


def main():
    now = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
    out = {'updated': now.strftime('%Y-%m-%d %H:%M'), 'cats': [], 'cards': {}, 'care': {}}
    spec_cache, care_cache = {}, {}

    def specs(model, url):
        if model not in spec_cache:
            s, sold, html = page_specs(url); spec_cache[model] = (s, sold); time.sleep(0.4)
        return spec_cache[model]

    def care(model, url):
        if model not in care_cache:
            care_cache[model] = care_prices(get(url)); time.sleep(0.4)
        return care_cache[model]

    for key, name, cid, sid, groups in CATS:
        buy = [item(key, p, i + 1) for i, p in enumerate(ranking('todays', cid))]
        time.sleep(0.5)
        subl = ranking('subscribe', sid)
        sub = [item(key, p, i + 1, True) for i, p in enumerate(subl)]
        sub_url = {p['modelName']: BASE + p['modelUrlPath'] for p in subl if p.get('modelUrlPath')}
        time.sleep(0.5)
        cat = {'key': key, 'name': name, 'groups': groups, 'buy': {}, 'sub': {}, 'n_buy': len(buy), 'n_sub': len(sub)}
        for g in groups:
            cat['buy'][g] = [x for x in buy if x['g'] == g][:10]
            cat['sub'][g] = [x for x in sub if x['g'] == g][:10]
        for g in groups:
            for x in cat['buy'][g]:
                if x['only']:
                    mm, far = match(x, buy)
                    x['match'] = mm; x['far'] = far
                    if mm:
                        st = next(q for q in buy if q['m'] == mm)
                        a, asold = specs(x['m'], x['url']); b, bsold = specs(st['m'], st['url'])
                        diff = []
                        for n in list(a.keys()) + [k for k in b if k not in a]:
                            if SKIP_SPEC.search(n): continue
                            va, vb = a.get(n, ''), b.get(n, '')
                            if va == vb: continue
                            diff.append([n, va or '표기 없음', vb or '표기 없음'])
                        same = [[n, a[n]] for n in a if n in b and a[n] == b[n] and not SKIP_SPEC.search(n)
                                and re.search(r'크기|에너지|용량|화면|해상도|패널', n)][:4]
                        out['cards'][x['m']] = {'dot': x['m'], 'store': mm, 'diff': diff[:12], 'same': same,
                                                'soldA': asold, 'soldB': bsold, 'far': far}
                        for mdl, it in ((x['m'], x), (mm, st)):
                            if mdl not in out['care']:
                                u = sub_url.get(mdl) or (BASE + '/care-solutions' + it['url'].replace(BASE, ''))
                                out['care'][mdl] = care(mdl, u)
                else:
                    if x['m'] not in out['care']:
                        u = sub_url.get(x['m']) or (BASE + '/care-solutions' + x['url'].replace(BASE, ''))
                        out['care'][x['m']] = care(x['m'], u)
        out['cats'].append(cat)
        print(name, '일시불', len(buy), '구독', len(sub), '카드', sum(1 for g in groups for x in cat['buy'][g] if x.get('match')))

    if not any(c['n_buy'] for c in out['cats']):
        print('엘지닷컴 응답 없음 — 저장 안 함'); sys.exit(1)
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
    print('저장', OUT, os.path.getsize(OUT))


if __name__ == '__main__':
    main()
