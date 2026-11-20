# 북울산·안동 홈페이지 '매니저' 탭 구조와 매니저별 리뷰 수 점검 (로그만)
import sys, re, json
sys.path.insert(0, "scripts")
import review_collect as rc
from playwright.sync_api import sync_playwright
STORES = {"북울산본점": ("ST00002548", 94), "안동본점": ("ST00002640", 72)}
SINCE, UNTIL = "2026-11-01", "2026-11-19"
LINKS = """() => [...document.querySelectorAll('a')].map(a => [a.innerText.trim().slice(0, 20), a.getAttribute('href') || '']).filter(x => x[1] && !x[1].startsWith('javascript') && x[1] !== '#')"""
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_page(locale="ko-KR")
    for name, (lg, hq) in STORES.items():
        print(f"\n■ {name} (본사 합계 {hq})")
        pg.goto(f"https://bestshop.lge.co.kr/storehub/dtl-{lg}/review", wait_until="networkidle", timeout=40000); pg.wait_for_timeout(1500)
        tabs = [l for l in pg.evaluate(LINKS) if "매니저" in l[0] or "manager" in l[1].lower() or "mng" in l[1].lower()]
        print("   매니저 관련 링크:", tabs[:10])
        try:
            pg.get_by_role("link", name=re.compile("^매니저$")).first.click(timeout=5000)
        except Exception:
            try: pg.locator("text=매니저").first.click(timeout=5000)
            except Exception as e: print("   매니저 탭 클릭 실패", e)
        pg.wait_for_timeout(3000)
        print("   매니저 탭 URL:", pg.url)
        print("   매니저 탭 화면:", pg.inner_text("body")[:700].replace("\n", " / "))
        links = [l for l in pg.evaluate(LINKS) if re.search(r"manager|mng|dtl-|counsel", l[1], re.I)]
        print("   매니저 탭 링크 예시:", links[:25])
        mlinks = list(dict.fromkeys(h for t, h in links if re.search(r"manager|mng", h, re.I) and "review" not in h.lower()))[:20]
        total = 0
        for k, h in enumerate(mlinks):
            url = h if h.startswith("http") else "https://bestshop.lge.co.kr" + h
            try:
                mp = b.new_page(locale="ko-KR"); mp.goto(url, wait_until="networkidle", timeout=30000); mp.wait_for_timeout(1500)
                try: mp.locator("text=리뷰").first.click(timeout=3000); mp.wait_for_timeout(1500)
                except Exception: pass
                rc._expand(mp, lambda: re.findall(rc.DATE_RE, mp.inner_text("body")), SINCE, 30)
                ds = [d for d in re.findall(rc.DATE_RE, mp.inner_text("body")) if SINCE <= d <= UNTIL]
                total += len(ds)
                print(f"   매니저 페이지 {k+1}: {url[-60:]} → 11/1~11/19 {len(ds)}건")
                if k == 0:
                    body = mp.inner_text("body"); m = re.search(rc.DATE_RE, body)
                    print("   [구조]", body[:300].replace("\n", " / "), " ... ", body[max(0, m.start()-150):m.end()+150].replace("\n", " / ") if m else "날짜 없음")
                mp.close()
            except Exception as e:
                print("   매니저 페이지 실패:", url, str(e)[:100])
        print(f"   매니저 페이지 합계 11/1~11/19 = {total}")
    b.close()
