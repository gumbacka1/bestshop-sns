# 엘지닷컴 전 모델 수집 → data/lge_full/
# 사이트맵에서 제품 주소를 모두 모은 뒤, 모델마다 상품 페이지와 구독 페이지를 읽는다.
# 모으는 것: 이름·출시·용량·등급·가격(정상가·할인가·최대혜택가)·닷컴 전용·리뷰,
#           사양 전체, 구독료(3~6년)·케어 유형·방문 주기·케어 안내 글, 사진·영상 링크,
#           제휴카드·구독 혜택·다품목 혜택 안내 글, 품목별 랭킹(일시불·구독).
# 표준 라이브러리만 사용(엑셀은 lge_full_excel.py 에서 따로 만든다).
import json, re, os, sys, time, html as H, datetime, urllib.request, urllib.parse, urllib.error
from concurrent.futures import ThreadPoolExecutor

BASE = 'https://www.lge.co.kr'
UA = 'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/124 Mobile Safari/537.36'
OUT = os.path.join(os.path.dirname(__file__), '..', 'data', 'lge_full')
ONLY = [s for s in os.environ.get('ONLY', '').split(',') if s]     # 경로 이름으로 품목 제한(시험용)
LIMIT = int(os.environ.get('LIMIT', '0') or 0)                      # 품목당 모델 수 제한(시험용)
WORKERS = int(os.environ.get('WORKERS', '6') or 6)
# 가전 품목만(사업자·소모품·액세서리 제외). 사이트맵 경로의 첫 칸 기준.
SKIP_PATH = re.compile(r'business|accessor|consumable|parts|filter|support|story|benefit|care-solutions|'
                       r'homestyle|company|cart|my-page|event|search|lg-signature-story', re.I)
RANK_CATS = [('TV', 'CT50000025', 'CT50238002'), ('냉장고', 'CT50000065', 'CT50178000'),
             ('세탁기', 'CT50000101', 'CT50136000'), ('건조기', 'CT50000107', 'CT50000178'),
             ('워시타워', 'CT50387000', 'CT50390000'), ('에어컨', 'CT50000131', 'CT50080000')]
INFO_PAGES = {
    '제휴카드_구독': '/benefits/card-discount?CareDiscount=Y',
    '제휴카드_전체': '/benefits/card-discount',
    '구독_제휴카드안내': '/care-solutions/rentalService-benefits?rental-scrvice=cards',
    '구독_혜택안내': '/care-solutions/rentalService-benefits',
    '다품목할인': '/benefits/exhibitions/multiple-products',
    '구독_결합할인': '/benefits/exhibitions/detail-PE00423001',
    '구독_FAQ_제휴카드': '/story/user-guide/care-solutions-faq8',
}
PRICE_KEYS = ['obsOriginalPrice', 'obsSellingPrice', 'obsMemberPrice', 'obsCouponPrice', 'maxBenefitPrice',
              'obsDiscountRate', 'rtModelSeq', 'reviewRatingAvg', 'reviewCount', 'reviewRating', 'totalReviewCount']
TEXT_KEYS = ['modelName', 'modelDisplayName', 'modelReleaseDate', 'lgecomOnlyFlag', 'superCategoryName',
             'categoryName', 'subCategoryName', 'keywdNmA', 'keywdNmB', 'keywdNmC', 'modelId', 'salesModelCode',
             'modelStatusCode', 'buyBtnFlag', 'rtFlag', 'careshipFlag', 'energyGrade']


def get(url, data=None, tries=3, timeout=40):
    err = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers={
                'User-Agent': UA, 'Accept-Language': 'ko-KR,ko;q=0.9',
                **({'X-Requested-With': 'XMLHttpRequest'} if data else {})})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode('utf-8', 'ignore'), r.geturl()
        except urllib.error.HTTPError as e:
            err = e
            if e.code in (400, 404, 410): break      # 없는 페이지는 다시 묻지 않는다
            time.sleep(2 + i * 4)
        except Exception as e:
            err = e
            time.sleep(2 + i * 4)
    if not (isinstance(err, urllib.error.HTTPError) and err.code in (400, 404, 410)):
        print('실패', url, err, file=sys.stderr)
    return '', url


def now_kst():
    return datetime.datetime.utcnow() + datetime.timedelta(hours=9)


def unesc(h):
    return h.replace('\\"', '"').replace('\\/', '/').replace('\\u0026', '&')


def text_of(h, start=None, end=None, cap=4000):
    """HTML → 줄 단위 글. start~end 사이만(없으면 전체)."""
    h = re.sub(r'(?is)<(script|style|noscript)[^>]*>.*?</\1>', ' ', h)
    h = re.sub(r'(?i)<br\s*/?>|</(p|li|tr|div|h\d|dt|dd)>', '\n', h)
    h = re.sub(r'(?i)</t[dh]>', ' | ', h)
    t = H.unescape(re.sub(r'<[^>]+>', ' ', h))
    lines = [re.sub(r'[ \t ]+', ' ', x).strip(' |') for x in t.split('\n')]
    lines = [x for x in lines if x]
    if start:
        i = next((k for k, x in enumerate(lines) if start in x), None)
        if i is None:
            return ''
        lines = lines[i:]
        if end:
            j = next((k for k, x in enumerate(lines[1:], 1) if end in x), None)
            if j: lines = lines[:j]
    return '\n'.join(lines)[:cap]


def first(h, key):
    m = re.search(r'"%s"\s*:\s*("(?:[^"\\]|\\.){0,300}"|-?[\d.]+|true|false|null)' % key, h)
    if not m: return None
    v = m.group(1)
    try:
        return json.loads(v)
    except Exception:
        return v.strip('"')


# ---------- 1. 사이트맵 → 제품 주소 ----------
def sitemap_urls():
    idx, _ = get(BASE + '/sitemap.xml')
    maps = re.findall(r'<loc>\s*([^<\s]+)\s*</loc>', idx) or [BASE + '/sitemap_product-detail-list.xml']
    prod, care = set(), set()
    for sm in maps:
        if not re.search(r'product-detail|care-solution|product', sm): continue
        x, _ = get(sm, timeout=120)
        for u in re.findall(r'<loc>\s*([^<\s]+)\s*</loc>', x):
            u = H.unescape(u.strip())
            if '/care-solutions/' in u: care.add(u)
            elif 'product-detail' in sm or re.search(r'/product/|/[a-z0-9-]+/[a-z0-9._-]+$', u): prod.add(u)
    print('사이트맵', len(maps), '제품 주소', len(prod), '구독 주소', len(care))
    return prod, care


def path_cat(u):
    p = urllib.parse.urlparse(u).path.strip('/').split('/')
    if p and p[0] == 'product': p = p[1:]
    return (p[0] if len(p) >= 2 else ''), (p[-1] if p else '')


# ---------- 2. 상품 페이지 ----------
def product(u):
    raw, final = get(u)
    if not raw: return None
    h = unesc(raw)
    d = {'url': final or u}
    for k in TEXT_KEYS + PRICE_KEYS:
        v = first(h, k)
        if v not in (None, ''): d[k] = v
    title = re.search(r'<title>([^<]{1,200})</title>', raw)
    d['title'] = H.unescape(title.group(1)).strip() if title else ''
    if 'modelName' not in d:
        d['modelName'] = path_cat(u)[1].upper()
    # 화면에 보이는 가격 글(정규식이 못 잡을 때 대비)
    vis = {}
    for lab in ['할인 전 판매가', '최대혜택가', '쿠폰 적용 시', '총 금액']:
        m = re.search(lab + r'[^0-9]{0,80}?([\d,]{5,})\s*원', text_of(raw, cap=20000))
        if m: vis[lab] = int(m.group(1).replace(',', ''))
    d['price_text'] = vis
    # 사양 전체
    specs = {}
    for n, v in re.findall(r'\{"name":"([^"]{1,60})","value":"([^"]{0,400})"', h):
        if n not in specs and not v.startswith('\\u003c') and not v.startswith('<'):
            specs[n] = v.replace('\\n', ' ').strip()
    d['specs'] = specs
    sold = re.search(r'판매되는 제품은\s*([^<"\\]{1,40})입니다', h)
    d['sold_as'] = sold.group(1).strip() if sold else ''
    summ = re.findall(r'AI 제품 요약.{0,20}?((?:<li[^>]*>[^<]{1,40}</li>\s*){2,8})', raw, re.S)
    d['ai_summary'] = re.findall(r'>([^<]{1,40})<', summ[0]) if summ else []
    # 케어 안내(상품 페이지 안 구독 영역)
    d['care_text'] = text_of(raw, '케어 방문 주기', '구독료 혜택', 2500) or text_of(raw, '케어서비스', '구독료 혜택', 2500)
    d['care_notes'] = text_of(raw, '구독하기 전에 꼭 확인', '전체 보기', 1200)
    # 사진·영상 링크
    imgs = []
    for m in re.findall(r'(?:https?:)?//(?:static|www)\.lge\.co\.kr/kr/images/[^"\'\s)]+?\.(?:jpg|jpeg|png|webp)', h):
        m = 'https:' + m if m.startswith('//') else m
        if m not in imgs: imgs.append(m)
    for m in re.findall(r'"(/kr/images/[^"]+?\.(?:jpg|jpeg|png|webp))"', h):
        m = 'https://static.lge.co.kr' + m
        if m not in imgs: imgs.append(m)
    vids = []
    for m in re.findall(r'(?:youtube\.com/(?:embed/|watch\?v=)|youtu\.be/)([\w-]{11})', h):
        v = 'https://www.youtube.com/watch?v=' + m
        if v not in vids: vids.append(v)
    for m in re.findall(r'(?:https?:)?//[^"\'\s]+?\.mp4', h):
        m = 'https:' + m if m.startswith('//') else m
        if m not in vids: vids.append(m)
    d['images'] = imgs[:60]
    d['videos'] = vids[:20]
    rv = re.search(r'제품 리뷰\s*([\d,]+)', text_of(raw, cap=8000))
    if rv: d['review_text'] = int(rv.group(1).replace(',', ''))
    return d


# ---------- 3. 구독 페이지 ----------
def care_page(u):
    raw, final = get(u, tries=2)
    if not raw or ('care-solutions' not in (final or u)): return None
    h = unesc(raw)
    res = {'url': final or u}
    m = re.search(r'"priceMap":(\{.*?\}\}),"partnerPriceMap"', h)
    if m:
        try:
            pm = json.loads(m.group(1))
            res['price_map'] = {k: {kk: v.get(kk) for kk in ('monthlyPrice', 'originalPrice', 'discountPrice')
                                    if isinstance(v, dict) and kk in v} for k, v in pm.items() if isinstance(v, dict)}
        except Exception:
            pass
    m = re.search(r'"partnerPriceMap":(\{.*?\}\})', h)
    if m:
        try: res['partner_price_map'] = json.loads(m.group(1))
        except Exception: pass
    for key in ('careServiceTypes', 'careServiceCycles', 'contractTerms', 'visitCycles', 'careTypes'):
        m = re.search(r'"%s":(\[[^\]]{0,3000}\])' % key, h)
        if m:
            try: res[key] = [x.get('label') for x in json.loads(m.group(1)) if isinstance(x, dict)]
            except Exception: pass
    cur = re.search(r'"currentSelection":"([^"]+)"', h)
    if cur: res['current_selection'] = cur.group(1)
    res['care_text'] = text_of(raw, '케어 방문 주기', '구독료 혜택', 3000) or text_of(raw, '케어서비스', '구독료 혜택', 3000)
    res['benefit_text'] = text_of(raw, '구독료 혜택', '더 알아보기', 800)
    res['notes'] = text_of(raw, '구독하기 전에 꼭 확인', '전체 보기', 1500)
    return res


def terms_summary(c):
    """priceMap → {36:{월,정상}, ...}  (기본 선택 조합 우선)"""
    pm = (c or {}).get('price_map') or {}
    if not pm: return {}
    cur = (c.get('current_selection') or '')
    suf = cur[len(cur.split('_')[0]):] if cur else None
    out = {}
    for k, v in pm.items():
        t = k.split('_')[0]
        if not t.isdigit(): continue
        if suf is not None and k[len(t):] != suf and t in out: continue
        if suf is not None and k[len(t):] != suf and any(kk.split('_')[0] == t and kk[len(t):] == suf for kk in pm):
            continue
        out[t] = {'월': v.get('monthlyPrice'), '정상': v.get('originalPrice')}
    return dict(sorted(out.items(), key=lambda x: int(x[0])))


# ---------- 4. 랭킹 ----------
def ranking(kind, cid):
    body = urllib.parse.urlencode({'rankingType': kind, 'categoryId': cid}).encode()
    t, _ = get(BASE + '/mkt/api/bestRanking/retrieveCategoryProductList.lgajax', body)
    try:
        d = json.loads(t)['data'][0]
        lst = d.get('subscribeRankingList' if kind == 'subscribe' else 'bestRankingProductList') or []
    except Exception:
        return []
    keep = ['modelName', 'modelDisplayName', 'obsSellingPrice', 'obsOriginalPrice', 'maxBenefitPrice', 'lgecomOnlyFlag',
            'keywdNmA', 'keywdNmB', 'modelReleaseDate', 'subCategoryName', 'modelUrlPath', 'btsOrdQty', 'obsOrdQty']
    return [{k: p.get(k) for k in keep} | {'순위': i + 1} for i, p in enumerate(lst)]


# ---------- 5. 안내 페이지(제휴카드·혜택) ----------
def card_rows(t):
    """'40만원 이상 | 8,000원 | 7,000원 | 15,000원' 같은 줄을 카드별로 묶는다."""
    cards, cur = [], None
    for line in t.split('\n'):
        if re.search(r'\[(신한|롯데|우리|하나|KB|국민|현대|삼성|NH|농협|BC|비씨)[^\]]*\]|카드$|카드\)', line) and len(line) < 60:
            cur = {'카드': line.strip(), '실적별': [], '조건': []}; cards.append(cur); continue
        if cur is None: continue
        if re.search(r'\d+\s*만\s*원\s*이상', line) and re.search(r'[\d,]+\s*원', line.split('이상', 1)[-1]):
            cur['실적별'].append(line.strip())
        elif re.search(r'최대|개월|연회비|기간|자동|청구|결제일', line) and len(line) < 200 and len(cur['조건']) < 12:
            cur['조건'].append(line.strip())
    return [c for c in cards if c['실적별'] or c['조건']]


def main():
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    stamp = now_kst().strftime('%Y-%m-%d %H:%M')
    prod_urls, care_urls = sitemap_urls()
    by_cat = {}
    for u in sorted(prod_urls):
        cat, slug = path_cat(u)
        if not cat or SKIP_PATH.search(cat) or not re.search(r'\d', slug): continue
        if ONLY and cat not in ONLY: continue
        by_cat.setdefault(cat, []).append(u)
    seen = {path_cat(u)[1].lower() for v in by_cat.values() for u in v}
    care_by_slug = {}
    for u in care_urls:
        if '/business/' in u: continue          # 사업자몰 구독 주소는 제외
        cat, slug = path_cat(u.replace('/care-solutions', ''))
        care_by_slug.setdefault(slug.lower(), u)
        # 구독 전용으로만 올라온 모델도 상품 목록에 넣는다
        if cat and not SKIP_PATH.search(cat) and (not ONLY or cat in ONLY):
            pu = BASE + '/' + cat + '/' + slug
            if slug.lower() not in seen:
                by_cat.setdefault(cat, []).append(pu); seen.add(slug.lower())
    # 랭킹에 있는데 사이트맵에 없는 모델도 넣는다
    ranks = {}
    for name, cid, sid in RANK_CATS:
        ranks[name] = {'일시불': ranking('todays', cid), '구독': ranking('subscribe', sid)}
        time.sleep(0.5)
        for lst in ranks[name].values():
            for q in lst:
                up = q.get('modelUrlPath') or ''
                cat, slug = path_cat(BASE + up)
                if slug and slug.lower() not in seen and cat and (not ONLY or cat in ONLY):
                    by_cat.setdefault(cat, []).append(BASE + up); seen.add(slug.lower())
    if LIMIT:
        by_cat = {k: v[:LIMIT] for k, v in by_cat.items()}
    urls = [u for v in by_cat.values() for u in v]
    print('수집 대상 품목', len(by_cat), '모델', len(urls), {k: len(v) for k, v in sorted(by_cat.items(), key=lambda x: -len(x[1]))})

    products = []
    def work(u):
        p = product(u)
        time.sleep(0.3)
        if not p: return None
        cat, slug = path_cat(u)
        p['경로품목'] = cat
        cu = care_by_slug.get(slug.lower())
        if not cu:
            cu = BASE + '/care-solutions/' + cat + '/' + slug   # 사이트맵에 없어도 구독 페이지가 있는지 확인
        if cu:
            c = care_page(cu); time.sleep(0.3)
            if c:
                c['요약'] = terms_summary(c)
                p['care'] = c
        return p
    with ThreadPoolExecutor(WORKERS) as ex:
        for i, p in enumerate(ex.map(work, urls), 1):
            if p: products.append(p)
            if i % 50 == 0: print(f'{i}/{len(urls)} 진행 ({int(time.time()-t0)}초)')

    info = {}
    for k, path in INFO_PAGES.items():
        raw, final = get(BASE + path)
        t = text_of(raw, cap=30000)
        info[k] = {'url': final or BASE + path, 'text': t, 'cards': card_rows(t) if '카드' in k else []}
        time.sleep(0.5)

    if len(products) < 10 and not (ONLY or LIMIT):
        print('수집 결과가 너무 적음 — 저장 안 함', len(products)); sys.exit(1)
    meta = {'updated': stamp, '초': int(time.time() - t0), '모델수': len(products),
            '품목별': {k: sum(1 for p in products if p['경로품목'] == k) for k in by_cat},
            '구독있음': sum(1 for p in products if (p.get('care') or {}).get('요약')),
            '사진있음': sum(1 for p in products if p.get('images')),
            '영상있음': sum(1 for p in products if p.get('videos'))}
    def dump(name, obj):
        with open(os.path.join(OUT, name), 'w', encoding='utf-8') as f:
            json.dump(obj, f, ensure_ascii=False, separators=(',', ':'))
    dump('products.json', products)
    dump('ranking.json', ranks)
    dump('benefits.json', info)
    dump('meta.json', meta)
    print('저장 완료', json.dumps(meta, ensure_ascii=False))


if __name__ == '__main__':
    main()
