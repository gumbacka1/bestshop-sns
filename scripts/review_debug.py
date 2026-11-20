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
        names = pg.evaluate("""() => [...document.querySelectorAll('*')].filter(e => e.children.length === 0 && /^[가-힣]{2,4} (매니저|부지점장|지점장|명장)$/.test((e.innerText || '').trim())).map(e => e.innerText.trim())""")
        names = list(dict.fromkeys(names))
        print("   매니저 이름:", names)
        total, seen = 0, set()
        for k, nm in enumerate(names):
            try:
                pg.goto(f"https://bestshop.lge.co.kr/storehub/dtl-{lg}/manager", wait_until="networkidle", timeout=30000); pg.wait_for_timeout(1200)
                pg.get_by_text(nm, exact=True).first.click(timeout=5000); pg.wait_for_timeout(2500)
                url = pg.url
                try: pg.get_by_text(re.compile("리뷰")).last.scroll_into_view_if_needed(timeout=2000)
                except Exception: pass
                rc._expand(pg, lambda: re.findall(rc.DATE_RE, pg.inner_text("body")), SINCE, 30)
                body = pg.inner_text("body")
                ds = [d for d in re.findall(rc.DATE_RE, body) if SINCE <= d <= UNTIL]
                total += len(ds)
                print(f"   {nm}: {url[-70:]} → 11/1~11/19 {len(ds)}건")
                if k == 0:
                    m = re.search(rc.DATE_RE, body)
                    print("   [구조]", body[:250].replace("\n", " / "), " ... ", body[max(0, m.start()-150):m.end()+150].replace("\n", " / ") if m else "날짜 없음")
            except Exception as e:
                print("   실패:", nm, str(e)[:120])
        print(f"   매니저 페이지 합계 11/1~11/19 = {total}")
    b.close()
