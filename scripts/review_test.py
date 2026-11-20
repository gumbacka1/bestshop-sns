# 깃허브 서버에서 울산본점 네이버·LG 리뷰가 읽히는지 시험 (저장 없음, 로그만)
import sys, time
sys.path.insert(0, "scripts")
import review_collect as rc
from playwright.sync_api import sync_playwright
NV, LG = "32514602", "ST00004185"
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    nv = b.new_page(user_agent=rc.MOBILE_UA, locale="ko-KR")
    for name, f in [("네이버 첫화면", lambda: rc.read_naver(nv, NV)),
                    ("네이버 날짜별(11/1~)", lambda: sorted(rc.read_nv_dates(nv, NV, "2026-11-01").items())),
                    ("LG 날짜별(11/1~)", lambda: sorted(rc.read_lg(b.new_page(locale="ko-KR"), LG, "2026-11-01").items()))]:
        t = time.time()
        try:
            print(f"■ {name}: {f()}  ({time.time()-t:.0f}초)")
        except Exception as e:
            print(f"■ {name}: 실패 {type(e).__name__}: {str(e)[:300]}")
            try:
                print("   화면 앞부분:", nv.inner_text("body")[:300].replace("\n", " "))
            except Exception:
                pass
    b.close()
