# 6개 지점으로 '더보기' 동작·날짜 구조 점검 (저장 없음, 로그만)
import sys, re, json, time
sys.path.insert(0, "scripts")
import review_collect as rc
from playwright.sync_api import sync_playwright
KEY = {"서귀포점": (3, 55), "이도본점": (0, 55), "율하점": (13, 16), "황금본점": (53, 13), "범어점": (4, 9), "제주본점": (9, 21)}
SINCE, UNTIL = "2026-11-01", "2026-11-19"
CANDS = """() => [...document.querySelectorAll('a,button,span,div')].filter(e => /^\\s*(펼쳐서\\s*)?더보기\\s*$/.test(e.innerText || '') && e.offsetParent !== null)
  .map(e => ({t: e.tagName, c: (e.className || '').toString().slice(0, 40), r: e.getAttribute('role'), y: Math.round(e.getBoundingClientRect().top + scrollY), p: (e.closest('a,button') || {}).tagName || ''}))"""
CLICK = """() => { const els = [...document.querySelectorAll('a,button,span,div')].filter(e => e.children.length <= 2 && /^\\s*(펼쳐서\\s*)?더보기\\s*$/.test(e.innerText || '') && e.offsetParent !== null);
  if (!els.length) return null; els.sort((a, b) => (a.getBoundingClientRect().top) - (b.getBoundingClientRect().top));
  const t = els[els.length - 1]; const c = t.closest('a,button') || t; c.scrollIntoView({block: 'center'}); c.click(); return c.tagName + ' y=' + Math.round(c.getBoundingClientRect().top + scrollY); }"""

def expand(page, date_fn, label, first):
    if first:
        print(f"   [{label}] 처음 '더보기' 후보:", json.dumps(page.evaluate(CANDS)[-6:], ensure_ascii=False))
    seq, extra = [], 0
    for i in range(50):
        ds = date_fn(page.inner_text("body"))
        if seq and seq[-1] == len(ds):
            page.wait_for_timeout(2500); ds = date_fn(page.inner_text("body"))
        seq.append(len(ds))
        if ds and min(ds) < SINCE:
            extra += 1
            if extra > 2:
                break
        r = page.evaluate(CLICK)
        if not r:
            seq.append("버튼없음"); break
        page.wait_for_timeout(1500)
    print(f"   [{label}] 날짜 개수 변화: {seq}")

kd = lambda t: rc._kdates(t)
lgd = lambda t: re.findall(rc.DATE_RE, t)
stores = {s.split("\t")[1]: s.split("\t") for s in open("scripts/review_stores.tsv", encoding="utf-8").read().splitlines()[1:]}
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    for k, name in enumerate(KEY):
        _, _, lg, nv = stores[name][:4]
        print(f"\n■ {name} (정답 네이버 {KEY[name][0]} / 홈페이지 {KEY[name][1]})")
        pg = b.new_page(user_agent=rc.MOBILE_UA, locale="ko-KR")
        bag = {}
        def walk(o):
            if isinstance(o, dict):
                if "visited" in o and "created" in o and o.get("id"):
                    bag[o["id"]] = (o["visited"], o["created"])
                for v in o.values(): walk(v)
            elif isinstance(o, list):
                for v in o: walk(v)
        def on_resp(r):
            if "graphql" in r.url:
                try: walk(r.json())
                except Exception: pass
        pg.on("response", on_resp)
        pg.goto(f"https://m.place.naver.com/place/{nv}/review/visitor?reviewSort=recent", wait_until="domcontentloaded", timeout=30000); pg.wait_for_timeout(3000)
        expand(pg, kd, "네이버 방문자", k == 0)
        body = pg.inner_text("body"); ds = kd(body)
        n = sum(1 for d in ds if SINCE <= d <= UNTIL)
        print(f"   네이버 방문자 11/1~11/19 = {n}  (11/20 {ds.count('2026-11-20')}, 날짜별 {sorted({d: ds.count(d) for d in set(ds) if d >= SINCE}.items())})")
        st = pg.evaluate("() => JSON.stringify(window.__APOLLO_STATE__ || {})")
        cr = re.findall(r'"created":"([^"]+)"', st); vi = re.findall(r'"visited":"([^"]+)"', st)
        def nov(v):
            m = re.match(r"(\d{1,2})\.(\d{1,2})\.", v)
            if m: return "2026-%02d-%02d" % (int(m.group(1)), int(m.group(2)))
            m = re.match(r"(\d{4})-(\d{2})-(\d{2})", v)
            return m.group(0) if m else ""
        try: walk(json.loads(st))
        except Exception: pass
        cv = [(nov(v), nov(c)) for v, c in bag.values()]
        print(f"   [작성일 기준·리뷰만] 모은 리뷰 {len(cv)}개 → 작성일 11/1~11/19 = {sum(1 for v, c in cv if SINCE <= c <= UNTIL)} / 방문일 기준 = {sum(1 for v, c in cv if SINCE <= v <= UNTIL)}")
        if k == 0:
            i = body.find("방문일"); print("   [구조] 첫 리뷰 주변:", body[max(0, i - 200):i + 120].replace("\n", " / "))
        pg.close()
        pg = b.new_page(locale="ko-KR")
        pg.goto(f"https://bestshop.lge.co.kr/storehub/dtl-{lg}/review", wait_until="networkidle", timeout=40000); pg.wait_for_timeout(1500)
        expand(pg, lgd, "홈페이지", k == 0)
        body = pg.inner_text("body")
        ms = list(re.finditer(rc.DATE_RE, body)); cnt = {}; kinds = {}
        for i, m in enumerate(ms):
            d = m.group()
            if not (SINCE <= d <= UNTIL): continue
            pe = ms[i - 1].end() if i else 0; ns = ms[i + 1].start() if i + 1 < len(ms) else len(body)
            before = [l.strip() for l in body[pe:m.start()].splitlines() if l.strip()]
            after = [l.strip() for l in body[m.end():ns].splitlines() if l.strip()]
            w = before[-1] if before else ""; tag = " ".join(after[:2])
            key = "네이버방문자" if "네이버 플레이스 방문자" in w else ("매니저" if "매니저 리뷰" in tag else ("매장" if "매장 리뷰" in tag else "기타:" + tag[:20]))
            kinds[key] = kinds.get(key, 0) + 1
        print(f"   홈페이지 11/1~11/19 종류별: {kinds}")
        if k == 0 and ms:
            m = ms[0]; print("   [구조] 첫 리뷰 주변:", body[max(0, m.start() - 150):m.end() + 150].replace("\n", " / "))
        pg.close()
    b.close()
