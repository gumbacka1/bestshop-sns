# 깃허브에서 297개 지점 네이버·LG 리뷰 수집 (PC 없이)
#   python scripts/review_gh.py collect <몇번째> <몇개로 나눔>   → parts/part<n>.json
#   python scripts/review_gh.py merge                          → data/review_hist.json, data/reviews.json
import sys, os, json, time, random, glob
from datetime import datetime, timedelta, timezone
sys.path.insert(0, "scripts")
import review_collect as rc

KST = timezone(timedelta(hours=9))
HIST, OUT = "data/review_hist.json", "data/reviews.json"


def load(p, d):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return d


def stores():
    out = []
    for line in open("scripts/review_stores.tsv", encoding="utf-8").read().splitlines()[1:]:
        t, n, lg, nv = (line.split("\t") + ["", "", "", ""])[:4]
        if n.strip():
            out.append({"team": t.strip(), "name": n.strip(), "lg": lg.strip(), "nv": nv.strip()})
    return out


def collect(part, parts):
    from playwright.sync_api import sync_playwright
    now = datetime.now(KST)
    h = load(HIST, {})
    lg_t = max(rc.LG_START, (now - timedelta(days=rc.LG_DAYS)).strftime("%Y-%m-%d"))
    nv_t = max(rc.LG_START, (now - timedelta(days=rc.NV_DAYS)).strftime("%Y-%m-%d"))
    team = os.environ.get("TEAM", "").replace("담당", "").strip()
    full = os.environ.get("FULL", "") in ("1", "true", "예")      # 11/1부터 다시 셈 (261120 블로그 날짜 수정 후 1회)
    debug = os.environ.get("NV_DEBUG", "") in ("1", "true", "예")  # 앞 3곳 블로그 화면·원본 일부를 기록에 남김
    ss = [s for s in stores() if not team or s["team"] == team]
    ss = [s for i, s in enumerate(ss) if i % parts == part]
    res = {}
    os.makedirs("parts", exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        nvp = b.new_page(user_agent=rc.MOBILE_UA, locale="ko-KR")
        lgp = b.new_page(locale="ko-KR")
        for k, s in enumerate(ss, 1):
            r = {}
            if s["nv"].isdigit():
                # 블로그 날짜 수정(261120) 전에 센 지점은 한 번 11/1부터 다시 셈
                redo = full or s["name"] not in h.get("blog_v2", [])
                since = nv_t if (s["name"] in h.get("nv", {}) and not redo) else rc.LG_START
                for _ in range(2):
                    try:
                        d, vt, bt = rc.read_nv_dates(nvp, s["nv"], since, debug=(debug and k <= 3))
                        r.update(nv=d, nv_since=since, visit=vt, blog=bt, blog_v2=True)
                        break
                    except Exception as e:
                        print("   네이버 다시 시도:", s["name"], str(e)[:120]); time.sleep(5)
            if s["lg"]:
                since = lg_t if s["name"] in h.get("lg", {}) else rc.LG_START
                for _ in range(2):
                    try:
                        r.update(lg=rc.read_lg(lgp, s["lg"], since), lg_since=since)
                        break
                    except Exception as e:
                        print("   LG 다시 시도:", s["name"], str(e)[:120]); time.sleep(5)
            res[s["name"]] = r
            sm = lambda key: sum(sum(x) for x in r[key].values()) if key in r else "-"
            print(f"[{k}/{len(ss)}] {s['name']} 방문자 {r.get('visit')} 블로그 {r.get('blog')} | 네이버 {sm('nv')} LG {sm('lg')}", flush=True)
            if k % 10 == 0:
                json.dump(res, open(f"parts/part{part}.json", "w", encoding="utf-8"), ensure_ascii=False)
            time.sleep(random.uniform(0.5, 1.5))
        b.close()
    json.dump(res, open(f"parts/part{part}.json", "w", encoding="utf-8"), ensure_ascii=False)


def merge():
    now = datetime.now(KST)
    today, yday, ms = now.strftime("%Y-%m-%d"), (now - timedelta(days=1)).strftime("%Y-%m-%d"), now.strftime("%Y-%m-01")
    h = load(HIST, {})
    for k in ("lg", "nv", "cum"):
        h.setdefault(k, {})
    res = {}
    for f in glob.glob("parts/**/part*.json", recursive=True):
        res.update(load(f, {}))
    print("받은 지점:", len(res))
    dif = lambda a, b: a - b if a is not None and b is not None else None
    rows, prevs = [], []
    for s in stores():
        n, r = s["name"], res.get(s["name"], {})
        for key in ("lg", "nv"):
            if key in r:
                days = h[key].setdefault(n, {})
                for d in set(r[key]) | {x for x in days if x >= r[key + "_since"]}:
                    days[d] = r[key].get(d, [0, 0])
        if r.get("blog_v2") and n not in h.setdefault("blog_v2", []):
            h["blog_v2"].append(n)
        cum = h["cum"].setdefault(n, {})
        if r.get("visit") is not None or r.get("blog") is not None:
            cum[today] = [r.get("visit"), r.get("blog")]
        last = max(cum) if cum else None
        prev = max((d for d in cum if d < (last or today)), default=None)
        cur, pv = cum.get(last, [None, None]) if last else [None, None], cum.get(prev, [None, None]) if prev else [None, None]
        if prev:
            prevs.append(prev)
        row = {"team": s["team"], "name": n, "visit": cur[0], "visit_diff": dif(cur[0], pv[0]),
               "blog": cur[1], "blog_diff": dif(cur[1], pv[1]),
               "nv_id": s["nv"] if s["nv"].isdigit() else "", "lg_id": s["lg"]}   # 대시보드 숫자 링크용
        lgd, nvd = h["lg"].get(n), h["nv"].get(n)
        row.update(rc.lg_summary(lgd, today, yday, ms) if lgd is not None else
                   {"lg_total": None, "lg_month": None, "lg_yday": None, "lg_today": None, "lg_mgr_month": None, "lg_daily": {}})
        row.update(rc.nv_summary(nvd, today, yday, ms) if nvd is not None else
                   {"nv_v_month": None, "nv_b_month": None, "nv_month": None, "nv_yday": None, "nv_today": None, "nv_daily": {}})
        row["on_today"] = None if row["nv_today"] is None and row["lg_today"] is None else (row["nv_today"] or 0) + (row["lg_today"] or 0)
        # 자동 점검
        iss = []
        if s["nv"] and row["visit"] is None:
            iss.append("네이버 못 읽음")
        if s["lg"] and lgd is None:
            iss.append("홈페이지 못 읽음")
        if row["visit_diff"] is not None and nvd is not None and prev:
            # 누적은 그날 수집 시각 값이라, 전날(prev) 수집 뒤에 쓴 리뷰도 변화에 들어감
            # → 전날을 뺀 합(lo) ~ 전날을 넣은 합(hi) 사이면 정상
            end = last or today
            lo = sum(x[0] for d, x in nvd.items() if prev < d <= end)
            hi = sum(x[0] for d, x in nvd.items() if prev <= d <= end)
            vd = row["visit_diff"]
            if vd < lo - 3 or vd > hi + 3:
                iss.append(f"네이버 누적 변화 {vd} vs 새 리뷰 {lo}~{hi}")
        row["check"] = ", ".join(iss)
        rows.append(row)
    caps = [r["name"] for r in rows if r.get("nv_v_month") == 10 or r.get("lg_month") == 10]
    flagged = [{"name": r["name"], "team": r["team"], "issues": r["check"]} for r in rows if r["check"]]
    check = {"flagged": flagged, "cap10": len(caps), "cap10_warn": len(caps) > 40}
    print("점검:", len(flagged), "곳 /", "딱 10에서 멈춘 곳", len(caps))
    json.dump(h, open(HIST, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    json.dump({"updated": now.strftime("%Y-%m-%d %H:%M"), "lg_start": rc.LG_START, "month": ms[:7], "yday": yday,
               "prev_day": max(prevs) if prevs else None, "source": "github", "check": check, "rows": rows},
              open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("저장:", OUT, len(rows), "지점")


if __name__ == "__main__":
    if sys.argv[1] == "collect":
        collect(int(sys.argv[2]), int(sys.argv[3]))
    else:
        merge()
