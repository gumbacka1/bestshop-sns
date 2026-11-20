# -*- coding: utf-8 -*-
"""
베스트샵 지점 리뷰 일별 수집 프로그램 v6
- 지점목록_261119_v1.xlsx 의 지점을 차례로 돌며
  ① 네이버 플레이스: 방문자 리뷰 수, 블로그 리뷰 수 (누적 숫자 → 전일비 계산)
  ② LG 베스트샵 매장 리뷰: '어제' 등록된 매장 리뷰 + 매니저 리뷰 수 (네이버 방문자는 제외)
- 결과는 같은 폴더의 '리뷰현황.xlsx' 에 저장합니다.
    · [일별현황] 시트: 오늘 실행 결과 + 전일비 (매번 새로 그림)
    · [원본] 시트: 매일 실행한 숫자가 계속 쌓임 (전일비 계산용, 지우지 마세요)
- 네이버 번호가 비어 있는 지점은 처음 한 번 자동으로 찾아서 지점목록 파일에 채워 넣습니다.
- v6: LG 리뷰를 11/1부터 누적·당월 누적·일별로 셈 (처음엔 11/1부터 펼쳐 세고, 그다음부턴 최근 7일만 다시 셈)
- v5: 결과를 구글 드라이브 "Claude 작업 폴더/04_리뷰 대시보드/reviews_latest.json"에도 저장 (대시보드용)
  (시험: python 리뷰수집_261120_v7.py 드라이브시험)
- v4: LG 리뷰를 최근 7일 날짜별로 세고, 지난 실행보다 늘어난 수를 '신규'로 계산 (늦게 올라오는 리뷰도 잡힘)
- v3: 못 찾은(확인필요) 네이버 번호를 다시 찾고, 검색 사이에 쉬어 감
- v2: 네이버 장소 이름을 읽어서 지점 이름과 맞는지 확인합니다 (지점목록 F·G칸).

[실행 예]
    python 리뷰수집_261120_v7.py          ← 297개 전체 (약 40~60분)
    python 리뷰수집_261120_v7.py 경북     ← 경북담당만 (시험용, 약 5분)
"""

import os
import re
import sys
import time
import json
import string
import html
import random
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
STORE_FILE = os.path.join(HERE, "지점목록_261119_v1.xlsx")
DATA_FILE = os.path.join(HERE, "리뷰현황.xlsx")

TEAM_ORDER = ["경북", "경인", "강남", "경원", "경남", "중부", "서부", "백화점"]
MAX_MORE_CLICKS = 60
LG_DAYS = 7            # LG 리뷰는 늦게 올라오기도 해서 매일 최근 7일을 다시 셈
LG_START = "2026-11-01"   # LG 리뷰 누적 시작일 (11월부터)
NV_DAYS = 7            # 네이버 리뷰도 매일 최근 7일을 다시 셈 (방문자 = 작성일 기준, 블로그 = 글 날짜 기준)
NV_MAX_CLICKS = 40
KDATE_RE = r"(\d{4})년 (\d{1,2})월 (\d{1,2})일"
# 대시보드 이름과 네이버/LG 이름이 다른 지점
NAME_ALIAS = {"갤러리아 센텀시티점": "갤러리아 센터시티점", "현대 충정점": "현대 충청점"}
FONT = "LG스마트체2.0 Regular"
MOBILE_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
             "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")
DATE_RE = r"\d{4}-\d{2}-\d{2}"


# ───────────────────────── 지점 목록 ─────────────────────────
def load_stores():
    wb = load_workbook(STORE_FILE)
    ws = wb.active
    stores = []
    for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        team, name, lg_id, nv_id = (row + (None,) * 4)[:4]
        if not name:
            continue
        stores.append({"row": i, "team": str(team or ""), "name": str(name),
                       "lg": str(lg_id or ""), "nv": str(nv_id or "").strip()})
    return wb, ws, stores


def find_naver_id(page, name):
    """네이버 지도에서 'LG전자 베스트샵 지점명'을 검색해 플레이스 번호를 찾습니다."""
    q = quote(f"LG전자 베스트샵 {NAME_ALIAS.get(name, name)}")
    page.goto(f"https://map.naver.com/p/search/{q}", wait_until="domcontentloaded", timeout=30000)
    for _ in range(16):                     # 최대 8초 기다림 (결과가 1개면 주소가 /place/번호 로 바뀜)
        m = re.search(r"/place/(\d+)", page.url)
        if m:
            return m.group(1)
        page.wait_for_timeout(500)
    # 결과가 여러 개면: 모바일 검색 결과에서 첫 번째 번호
    page.goto(f"https://m.map.naver.com/search2/search.naver?query={q}",
              wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(2500)
    m = re.search(r'data-id="(\d{6,})"', page.content()) or re.search(r"/place/(\d{6,})", page.content())
    return m.group(1) if m else ""


# ───────────────────────── 수집 ─────────────────────────
def first_int(pattern, text):
    m = re.search(pattern, text)
    return int(m.group(1)) if m else None


def read_naver(page, nv_id):
    page.goto(f"https://m.place.naver.com/place/{nv_id}/home", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(2500)
    src = page.content()
    visit = first_int(r'"reviewCount"\s*:\s*(\d+)', src)
    blog = first_int(r'"cafeBlogReviewsTotal"\s*:\s*(\d+)', src)
    m = (re.search(r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"', src)
         or re.search(r'"name"\s*:\s*"((?:LG|엘지)[^"]{0,40})"', src))
    place_name = html.unescape(m.group(1)).replace(" : 네이버", "").strip() if m else ""
    return visit, blog, place_name


def _norm_name(t):
    t = re.sub(r"LG\s*전자|엘지전자|LG|베스트\s*샵|BEST\s*SHOP|백화점|\(.*?\)|\s|&", "", t, flags=re.I)
    return re.sub(r"점$", "", t)


def name_ok(store_name, place_name):
    """네이버 장소 이름이 지점 이름과 같은지 (LG전자·베스트샵·백화점·띄어쓰기 무시)"""
    store_name = NAME_ALIAS.get(store_name, store_name)
    return bool(place_name) and _norm_name(store_name) == _norm_name(html.unescape(place_name))


def read_lg(page, lg_id, since_day):
    """since_day(YYYY-MM-DD) 이후 LG 리뷰를 날짜별로 셈 (네이버 방문자 제외) → {날짜: [매장, 매니저]}"""
    page.goto(f"https://bestshop.lge.co.kr/storehub/dtl-{lg_id}/review",
              wait_until="networkidle", timeout=40000)
    page.wait_for_timeout(1500)
    _expand(page, lambda: re.findall(DATE_RE, page.inner_text("body")), since_day, MAX_MORE_CLICKS)

    body = page.inner_text("body")
    ms = list(re.finditer(DATE_RE, body))
    by_date = {}
    for i, m in enumerate(ms):
        d = m.group()
        if d < since_day:
            continue
        prev_end = ms[i - 1].end() if i else 0
        next_start = ms[i + 1].start() if i + 1 < len(ms) else len(body)
        before = [l.strip() for l in body[prev_end:m.start()].splitlines() if l.strip()]
        after = [l.strip() for l in body[m.end():next_start].splitlines() if l.strip()]
        writer = before[-1] if before else ""     # 날짜 바로 앞 = 작성자/출처
        tag = " ".join(after[:2])                 # 날짜 바로 뒤 = 종류
        if "네이버 플레이스 방문자" in writer:
            continue
        cell = by_date.setdefault(d, [0, 0])
        if "매니저 리뷰" in tag:
            cell[1] += 1
        elif "매장 리뷰" in tag:
            cell[0] += 1
    return by_date


CLICK_MORE = """() => { const els = [...document.querySelectorAll('a,button,span,div')].filter(e => e.children.length <= 2 && /^\\s*(펼쳐서\\s*)?더보기\\s*$/.test(e.innerText || '') && e.offsetParent !== null);
  if (!els.length) return false; els.sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top);
  const t = els[els.length - 1]; const c = t.closest('a,button') || t; c.scrollIntoView({block: 'center'}); c.click(); return true; }"""


def _expand(page, dates_fn, since_day, max_clicks=60):
    """맨 아래 '더보기'를 눌러 가며, since_day 보다 오래된 날짜가 보인 뒤 2번 더 넘기고 멈춤.
    버튼이 잠깐 안 보이면 2.5초 기다렸다가 한 번 더 시도."""
    extra, prev = 0, -1
    for _ in range(max_clicks):
        ds = dates_fn()
        if len(ds) == prev:
            page.wait_for_timeout(2500)
            ds = dates_fn()
        prev = len(ds)
        if ds and min(ds) < since_day:
            extra += 1
            if extra > 2:
                break
        if not page.evaluate(CLICK_MORE):
            page.wait_for_timeout(2500)
            if not page.evaluate(CLICK_MORE):
                break
        page.wait_for_timeout(1500)


def _md_to_date(v, today=None):
    """'11.19.목' → '2026-11-19' (연도 없으면 올해, 미래 달이면 작년)"""
    m = re.match(r"(\d{1,2})\.(\d{1,2})\.", v or "")
    if not m:
        m2 = re.match(r"(\d{4})-(\d{2})-(\d{2})", v or "")
        return m2.group(0) if m2 else ""
    t = today or datetime.now()
    y = t.year - (1 if int(m.group(1)) > t.month else 0)
    return "%d-%02d-%02d" % (y, int(m.group(1)), int(m.group(2)))


def _kdates(text):
    return ["%s-%02d-%02d" % (y, int(m), int(d)) for y, m, d in re.findall(KDATE_RE, text)]


def _count_list(page, url, since_day, sort_recent=False):
    """네이버 리뷰 목록에서 since_day 이후 날짜를 셈 → {날짜: 개수}"""
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(2500)
    if sort_recent:
        try:
            page.locator("text=최신순").first.click(timeout=3000)
            page.wait_for_timeout(1500)
        except Exception:
            pass
    _expand(page, lambda: _kdates(page.inner_text("body")), since_day, NV_MAX_CLICKS)
    out = {}
    body = page.inner_text("body")
    for d in _kdates(body):
        if d >= since_day:
            out[d] = out.get(d, 0) + 1
    m = re.search(r"\n리뷰([\d,]+)\n", body)          # 목록 위 "리뷰3,047" = 전체 개수
    return out, (int(m.group(1).replace(",", "")) if m else None)


def _visitor_by_created(page, nv_id, since_day):
    """방문자 리뷰를 작성일(created) 기준으로 셈 → ({날짜: 개수}, 전체 개수)"""
    bag = {}
    def walk(o):
        if isinstance(o, dict):
            if "visited" in o and "created" in o and o.get("id"):
                bag[o["id"]] = _md_to_date(o["created"])
            for x in o.values():
                walk(x)
        elif isinstance(o, list):
            for x in o:
                walk(x)
    def on_resp(r):
        if "graphql" in r.url:
            try:
                walk(r.json())
            except Exception:
                pass
    page.on("response", on_resp)
    try:
        page.goto(f"https://m.place.naver.com/place/{nv_id}/review/visitor?reviewSort=recent", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2500)
        try:
            walk(json.loads(page.evaluate("() => JSON.stringify(window.__APOLLO_STATE__ || {})")))
        except Exception:
            pass
        _expand(page, lambda: [d for d in bag.values() if d], since_day, NV_MAX_CLICKS)
        body = page.inner_text("body")
    finally:
        page.remove_listener("response", on_resp)
    out = {}
    for d in bag.values():
        if d and d >= since_day:
            out[d] = out.get(d, 0) + 1
    m = re.search(r"\n리뷰([\d,]+)\n", body)
    return out, (int(m.group(1).replace(",", "")) if m else None)


BLOG_DATE_KEYS = ("date", "created", "createdString", "createdDate", "writtenDate", "postDate", "regDate", "displayDate")
DOT_DATE_RE = r"(?<![\d.])(?:\d{2,4}\.\d{1,2}\.\d{1,2}\.?(?!\d)|\d{1,2}\.\d{1,2}\.(?=[월화수목금토일]))"


def _any_date(v, today=None):
    """블로그 날짜 글자 → 'YYYY-MM-DD' ('2026.11.12.', '26.11.12.', '11.12.', '3일 전', '어제', '2026년 11월 12일' 등). 모르면 ''"""
    t = today or datetime.now()
    v = str(v or "").strip()
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", v)
    if m:
        return m.group(0)
    m = re.search(KDATE_RE, v)
    if m:
        return "%s-%02d-%02d" % (m.group(1), int(m.group(2)), int(m.group(3)))
    m = re.match(r"(\d{2,4})\.(\d{1,2})\.(\d{1,2})", v)
    if m:
        y = int(m.group(1)); y = y + 2000 if y < 100 else y
        return "%d-%02d-%02d" % (y, int(m.group(2)), int(m.group(3)))
    m = re.match(r"(\d+)\s*(분|시간|일|주)\s*전", v)
    if m:
        n = int(m.group(1)); u = m.group(2)
        if u == "일":
            dd = n
        elif u == "주":
            dd = n * 7
        else:                                   # 분·시간 전 → 오늘 (지금 시각보다 많은 시간 전이면 어제)
            dd = 1 if (u == "시간" and n > t.hour) else 0
        return (t - timedelta(days=dd)).strftime("%Y-%m-%d")
    if v.startswith("어제"):
        return (t - timedelta(days=1)).strftime("%Y-%m-%d")
    if v.startswith("오늘") or v.startswith("방금"):
        return t.strftime("%Y-%m-%d")
    m = re.match(r"(\d{1,2})\.(\d{1,2})\.", v)
    if m:
        return _md_to_date(v, t)
    return ""


def _blog_by_date(page, nv_id, since_day, debug=False):
    """블로그·카페 리뷰를 글 날짜로 셈 (261120: 원래는 '2026년 11월 12일' 글자만 찾아서 거의 0이 나왔음)
    1순위: 네이버 원본 데이터(graphql)의 날짜 / 2순위: 화면의 '2026.11.12.' 모양 날짜. 오늘 이후 날짜는 버림."""
    now = datetime.now(timezone(timedelta(hours=9))).replace(tzinfo=None)
    today = now.strftime("%Y-%m-%d")
    bag, samples = {}, []
    def walk(o):
        if isinstance(o, dict):
            ks = [k for k in BLOG_DATE_KEYS if isinstance(o.get(k), str) and o.get(k)]
            key = o.get("url") or o.get("reviewId") or o.get("id")
            if ks and key and ("visited" not in o):
                d = _any_date(o[ks[0]], now)
                if d:
                    bag[str(key)] = d
                    if debug and len(samples) < 3:
                        samples.append({k: (str(o[k])[:40]) for k in list(o)[:15]})
            for x in o.values():
                walk(x)
        elif isinstance(o, list):
            for x in o:
                walk(x)
    def on_resp(r):
        if "graphql" in r.url:
            try:
                walk(r.json())
            except Exception:
                pass
    page.on("response", on_resp)
    try:
        page.goto(f"https://m.place.naver.com/place/{nv_id}/review/ugc?type=list", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2500)
        try:
            walk(json.loads(page.evaluate("() => JSON.stringify(window.__APOLLO_STATE__ || {})")))
        except Exception:
            pass
        try:
            page.locator("text=최신순").first.click(timeout=3000)
            page.wait_for_timeout(1500)
        except Exception:
            pass
        def text_dates():
            return [_any_date(m.group(0), now) for m in re.finditer(DOT_DATE_RE, page.inner_text("body"))]
        _expand(page, lambda: list(bag.values()) or [d for d in text_dates() if d], since_day, NV_MAX_CLICKS)
        body = page.inner_text("body")
    finally:
        page.remove_listener("response", on_resp)
    src = "graphql"
    dates = list(bag.values())
    if not dates:
        src = "화면"
        dates = [_any_date(m.group(0), now) for m in re.finditer(DOT_DATE_RE, body)]
    out = {}
    for d in dates:
        if d and since_day <= d <= today:
            out[d] = out.get(d, 0) + 1
    m = re.search(r"\n리뷰([\d,]+)\n", body)
    total = int(m.group(1).replace(",", "")) if m else None
    if debug:
        print(f"   [블로그 점검] {nv_id} 읽은 곳={src} 글 {len(dates)}개 기간내 {sum(out.values())} 누적 {total}")
        print("   [블로그 점검] 원본 예시:", json.dumps(samples, ensure_ascii=False)[:600])
        print("   [블로그 점검] 화면 앞부분:", body[:500].replace("\n", " / "))
    return out, total


def read_nv_dates(page, nv_id, since_day, debug=False):
    """→ {날짜: [방문자(작성일), 블로그(글 날짜)]}"""
    v, vt = _visitor_by_created(page, nv_id, since_day)
    time.sleep(random.uniform(1, 2))
    b, bt = _blog_by_date(page, nv_id, since_day, debug)
    if bt is None:                       # 목록 위 "리뷰N"을 못 찾으면 네이버 첫 화면의 블로그 총수로
        try:
            bt = read_naver(page, nv_id)[1]
        except Exception:
            pass
    return {d: [v.get(d, 0), b.get(d, 0)] for d in set(v) | set(b)}, vt, bt


def nv_summary(days, today, yday, month_start):
    tot = lambda d, i: sum(x[i] for k, x in days.items() if k >= d)
    # 261120: 네이버 리뷰 카운트 = 방문자 리뷰만 (블로그는 nv_b_month 로 따로 보관, 건수에는 넣지 않음 — 본사 기준)
    daily = {k: x[0] for k, x in sorted(days.items()) if k >= LG_START}
    return {"nv_v_month": tot(month_start, 0), "nv_b_month": tot(month_start, 1),
            "nv_month": tot(month_start, 0),
            "nv_yday": days.get(yday, [0, 0])[0], "nv_today": days.get(today, [0, 0])[0], "nv_daily": dict(list(daily.items())[-62:])}


def load_hist(lg_ws):
    """LG원본 시트 → {지점: {날짜: [매장, 매니저]}} (나중 기록이 앞 기록을 덮어씀)"""
    hist = {}
    for r in lg_ws.iter_rows(min_row=2, values_only=True):
        if not r or not r[1] or not r[2] or str(r[2]) == "-":
            continue
        hist.setdefault(r[1], {})[str(r[2])] = [r[3] or 0, r[4] or 0]
    return hist


def lg_summary(days, today, yday, month_start):
    tot = lambda d: sum(v[0] + v[1] for k, v in days.items() if k >= d)
    daily = {k: v[0] + v[1] for k, v in sorted(days.items()) if k >= LG_START}
    recent = dict(list(daily.items())[-62:])
    return {"lg_total": tot(LG_START), "lg_month": tot(month_start),
            "lg_yday": sum(days.get(yday, [0, 0])), "lg_today": sum(days.get(today, [0, 0])),
            "lg_mgr_month": sum(v[1] for k, v in days.items() if k >= month_start), "lg_daily": recent}


# ───────────────────────── 엑셀 저장 ─────────────────────────
RAW_HEAD = ["수집일시", "기준일", "담당", "지점명", "네이버 방문자", "네이버 블로그",
            "LG 누적(11/1~)", "LG 당월", "LG 어제"]


def open_data():
    if os.path.exists(DATA_FILE):
        wb = load_workbook(DATA_FILE)
    else:
        wb = Workbook()
        wb.active.title = "일별현황"
    if "원본" not in wb.sheetnames:
        ws = wb.create_sheet("원본")
        ws.append(RAW_HEAD)
    if "LG원본" not in wb.sheetnames:
        ws = wb.create_sheet("LG원본")
        ws.append(["수집일시", "지점명", "리뷰 날짜", "매장 리뷰", "매니저 리뷰"])
    if "네이버원본" not in wb.sheetnames:
        ws = wb.create_sheet("네이버원본")
        ws.append(["수집일시", "지점명", "리뷰 날짜", "방문자 리뷰(방문일)", "블로그 리뷰"])
    return wb


def previous_values(raw_ws, today):
    """오늘 이전 가장 최근 실행의 지점별 네이버 숫자"""
    prev = {}
    for r in raw_ws.iter_rows(min_row=2, values_only=True):
        if not r or not r[0]:
            continue
        day = str(r[0])[:10]
        if day >= today:
            continue
        key = r[3]
        if key not in prev or day >= prev[key][0]:
            prev[key] = (day, r[4], r[5])
    return prev


def diff(now, before):
    if isinstance(now, int) and isinstance(before, int):
        return now - before
    return "-"


def write_report(wb, results, prev, today, target_day):
    if "일별현황" in wb.sheetnames:
        del wb["일별현황"]
    ws = wb.create_sheet("일별현황", 0)

    thin = Side(style="thin", color="BFBFBF")
    border = Border(top=thin, bottom=thin)
    f_norm = Font(name=FONT, size=10, color="000000")
    f_bold = Font(name=FONT, size=10, bold=True, color="000000")
    fill_head = PatternFill("solid", fgColor="EDEDED")
    fill_total = PatternFill("solid", fgColor="FFF2CC")
    center = Alignment(horizontal="center", vertical="center", wrap_text=True)

    ws.append([f"[경북 실행강화팀] 베스트샵 리뷰 일별 현황  (수집 {today} / LG 리뷰: 11/1부터 누적, 네이버 방문자 제외)"])
    ws["A1"].font = Font(name=FONT, size=12, bold=True)
    ws.append([])
    ws.append(["담당", "지점명", "네이버 방문자", "", "네이버 블로그", "", "LG 리뷰 (네이버 방문자 제외)", "", ""])
    ws.append(["", "", "누적", "전일비", "누적", "전일비", "누적(11/1~)", "당월", "어제"])
    for c in (3, 4):
        for cell in ws[c]:
            cell.font, cell.fill, cell.alignment, cell.border = f_bold, fill_head, center, border
    ws.merge_cells("A3:A4"); ws.merge_cells("B3:B4")
    ws.merge_cells("C3:D3"); ws.merge_cells("E3:F3"); ws.merge_cells("G3:I3")

    def line(team, name, items, total=False):
        ws.append([team, name] + items)
        for cell in ws[ws.max_row]:
            cell.font = f_bold if total else f_norm
            cell.alignment, cell.border = center, border
            if total:
                cell.fill = fill_total
            if isinstance(cell.value, int):
                cell.number_format = "#,##0"

    def row_items(r):
        p = prev.get(r["name"], (None, None, None))
        v = r["visit"] if r["visit"] is not None else "-"
        b = r["blog"] if r["blog"] is not None else "-"
        return [v, diff(r["visit"], p[1]), b, diff(r["blog"], p[2]),
                r["lg_total"], r["lg_month"], r["lg_yday"]]

    def sum_items(rows):
        items = [row_items(r) for r in rows]
        out = []
        for k in range(7):
            vals = [it[k] for it in items if isinstance(it[k], int)]
            out.append(sum(vals) if vals else "-")
        return out

    line("계", "", sum_items(results), total=True)
    for team in TEAM_ORDER:
        rows = [r for r in results if r["team"] == team]
        if not rows:
            continue
        line(team, "총계", sum_items(rows), total=True)
        start = ws.max_row + 1
        for r in rows:
            line(team, r["name"], row_items(r))
        if ws.max_row >= start:
            ws.merge_cells(start_row=start, start_column=1, end_row=ws.max_row, end_column=1)

    # ▶ 코멘트
    scored = [(row_items(r), r) for r in results]
    up = sorted([s for s in scored if isinstance(s[0][1], int)], key=lambda s: -s[0][1])[:3]
    lg_top = sorted([s for s in scored if isinstance(s[0][6], int) and s[0][6] > 0], key=lambda s: -s[0][6])[:3]
    fail = [r["name"] for r in results if r["visit"] is None or r["lg_total"] == "-"]
    ws.append([])
    comments = ["▶ 코멘트"]
    if up:
        comments.append("· 네이버 방문자 전일비 상위: " + ", ".join(f"{s[1]['name']}({s[0][1]:+d})" for s in up))
    if lg_top:
        comments.append("· LG 리뷰 어제 상위: " + ", ".join(f"{s[1]['name']}({s[0][6]}건)" for s in lg_top))
    m0 = [r["name"] for r in results if r["lg_month"] == 0]
    comments.append(f"· 이번 달 LG 리뷰 0건 지점: {len(m0)}개 / 전체 {len(results)}개")
    if fail:
        comments.append("· 숫자를 못 읽은 지점(확인 필요): " + ", ".join(fail[:20]))
    for c in comments:
        ws.append([c])
        ws.cell(ws.max_row, 1).font = Font(name=FONT, size=10, bold=(c == "▶ 코멘트"))

    for col, w in zip("ABCDEFGHI", [9, 22, 11, 9, 11, 9, 8, 8, 8]):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = "C5"


# ───────────────────────── 구글 드라이브로 내보내기 (대시보드용) ─────────────────────────
DRIVE_SUB = os.path.join("Claude 작업 폴더", "04_리뷰 대시보드")
JSON_NAME = "reviews_latest.json"


def find_drive_dir():
    """Google Drive 데스크톱 폴더(예: G:\\내 드라이브)를 찾아서 저장 폴더를 돌려줌"""
    cands = []
    for letter in string.ascii_uppercase[3:]:            # D: ~ Z:
        for name in ("내 드라이브", "My Drive"):
            cands.append(f"{letter}:\\{name}")
    home = os.path.expanduser("~")
    cands += [os.path.join(home, "Google Drive", "내 드라이브"), os.path.join(home, "Google Drive", "My Drive"),
              os.path.join(home, "My Drive"), os.path.join(home, "내 드라이브")]
    for c in cands:
        if os.path.isdir(c):
            out = os.path.join(c, DRIVE_SUB)
            os.makedirs(out, exist_ok=True)
            return out
    return None


def export_json(payload):
    out = find_drive_dir()
    if not out:
        print("※ 구글 드라이브 폴더를 못 찾아서 대시보드용 파일은 저장하지 못했어요.")
        return None
    path = os.path.join(out, JSON_NAME)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    print(f"대시보드용 파일 저장 → {path}")
    return path


# ───────────────────────── 실행 ─────────────────────────
def main():
    try:
        sys.stdout.reconfigure(line_buffering=True)   # 기록 파일에 바로바로 적기
    except Exception:
        pass
    if len(sys.argv) > 1 and sys.argv[1] == "드라이브시험":
        export_json({"test": True, "updated": datetime.now().strftime("%Y-%m-%d %H:%M")})
        return
    if len(sys.argv) > 1 and sys.argv[1] == "시험울산":   # 저장 없이 울산본점 네이버 날짜만 세어 보기
        _, _, sts = load_stores()
        s0 = next(x for x in sts if x["name"] == "울산본점")
        with sync_playwright() as p:
            br = p.chromium.launch(headless=True)
            res = read_nv_dates(br.new_page(user_agent=MOBILE_UA, locale="ko-KR"), s0["nv"], LG_START)
            br.close()
        lines = [f"{d}  방문자 {v}  블로그 {b}" for d, (v, b) in sorted(res.items())]
        lines.append(f"합계 방문자 {sum(x[0] for x in res.values())} / 블로그 {sum(x[1] for x in res.values())}")
        open("네이버날짜확인_결과2.txt", "w", encoding="utf-8").write("\n".join(lines))
        print("\n".join(lines))
        return
    team_filter = sys.argv[1].replace("담당", "") if len(sys.argv) > 1 else None
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    target_day = max(LG_START, (now - timedelta(days=LG_DAYS)).strftime("%Y-%m-%d"))   # 매일 다시 세는 시작일
    yday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    month_start = now.strftime("%Y-%m-01")
    wb = open_data()
    hist = load_hist(wb["LG원본"])
    nv_hist = load_hist(wb["네이버원본"])
    nv_target = max(LG_START, (now - timedelta(days=NV_DAYS)).strftime("%Y-%m-%d"))

    st_wb, st_ws, stores = load_stores()
    if team_filter:
        stores = [s for s in stores if s["team"] == team_filter]
    print(f"[{now:%Y-%m-%d %H:%M}] 리뷰 수집 시작 — {len(stores)}개 지점"
          f"{' (' + team_filter + ')' if team_filter else ''}, LG 리뷰 {target_day} 이후 다시 셈 (기록 없는 지점은 {LG_START}부터)\n")

    results = []
    name_check = []
    st_ws.cell(1, 6, "네이버 장소 이름")
    st_ws.cell(1, 7, "이름 확인")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        nv_page = browser.new_page(user_agent=MOBILE_UA, locale="ko-KR")
        lg_page = browser.new_page(locale="ko-KR")

        # ① 네이버 번호 채우기 (처음 한 번)
        missing = [s for s in stores if not s["nv"].isdigit()]   # 빈칸·확인필요 모두 다시 찾기
        if missing:
            print(f"네이버 번호 찾기: {len(missing)}개 지점 (천천히 찾아요)")
            fails, rested = 0, False
            for s in missing:
                if fails >= 8 and rested:
                    s["nv"] = ""
                    st_ws.cell(s["row"], 4, "확인필요")
                    continue                      # 네이버가 막은 것 같으면 남은 건 다음 실행 때
                if fails >= 8:
                    print("  ※ 연속 실패 — 1분 쉬었다가 다시 해요")
                    time.sleep(60); fails, rested = 0, True
                try:
                    s["nv"] = find_naver_id(lg_page, s["name"])
                except Exception:
                    s["nv"] = ""
                fails = 0 if s["nv"] else fails + 1
                st_ws.cell(s["row"], 4, s["nv"] or "확인필요")
                print(f"  {s['name']:14s} → {s['nv'] or '못 찾음'}")
                time.sleep(random.uniform(3, 5))      # 네이버가 막지 않게 쉬어 가기
            st_wb.save(STORE_FILE)
            left = sum(1 for s in stores if not s["nv"].isdigit())
            print(f"  지점목록 파일에 저장했어요. (못 찾은 지점 {left}개 → 다음 실행 때 다시 찾아요)\n")

        # ② 리뷰 수집
        for n, s in enumerate(stores, 1):
            visit = blog = None
            lg_dates, since = None, (target_day if s["name"] in hist else LG_START)
            nv_dates, nv_since = None, (nv_target if s["name"] in nv_hist else LG_START)
            if s["nv"].isdigit():
                try:
                    visit, blog, pname = read_naver(nv_page, s["nv"])
                    st_ws.cell(s["row"], 6, pname or "-")
                    ok = name_ok(s["name"], pname)
                    st_ws.cell(s["row"], 7, "OK" if ok else "확인필요")
                    if not ok:
                        name_check.append(f"{s['name']} → 네이버 '{pname or '이름 못 읽음'}'")
                except Exception:
                    pass
                try:
                    nv_dates = read_nv_dates(nv_page, s["nv"], nv_since)
                except Exception:
                    pass
            if s["lg"]:
                try:
                    lg_dates = read_lg(lg_page, s["lg"], since)
                except Exception:
                    pass
            results.append({"team": s["team"], "name": s["name"], "visit": visit, "blog": blog,
                            "lg_dates": lg_dates, "since": since,
                            "nv_dates": nv_dates, "nv_since": nv_since})
            print(f"  [{n:>3}/{len(stores)}] {s['team']:4s} {s['name']:14s} "
                  f"네이버 {visit if visit is not None else '-':>5} / {blog if blog is not None else '-':>4}"
                  f" (당월 {sum(a + b for a, b in nv_dates.values()) if nv_dates is not None else '-'})"
                  f"  | LG {since}~ {sum(a + b for a, b in lg_dates.values()) if lg_dates is not None else '-'}건")
            time.sleep(0.5)
        browser.close()

    try:
        st_wb.save(STORE_FILE)
    except PermissionError:
        print("※ 지점목록 파일이 열려 있어서 '네이버 장소 이름' 칸은 저장하지 못했어요.")
    if name_check:
        print("\n※ 네이버 번호 확인 필요 (지점 이름과 네이버 장소 이름이 달라요):")
        for line in name_check:
            print("   -", line)
        print("   → 지점목록 파일의 '네이버 번호' 칸을 맞는 번호로 고치면 다음 실행부터 반영돼요.")

    # ③ 저장
    raw = wb["원본"]
    prev = previous_values(raw, today)
    stamp = now.strftime("%Y-%m-%d %H:%M")
    lg_ws = wb["LG원본"]
    for r in results:
        days = hist.setdefault(r["name"], {})
        if r["lg_dates"] is not None:
            # 다시 센 기간은 새 숫자로 덮어씀 (없어진 날짜는 0)
            for d in sorted(set(r["lg_dates"]) | {k for k in days if k >= r["since"]}):
                new = r["lg_dates"].get(d, [0, 0])
                if days.get(d) != new:
                    lg_ws.append([stamp, r["name"], d, new[0], new[1]])
                days[d] = new
            r.update(lg_summary(days, today, yday, month_start))
        else:
            r.update({"lg_total": "-", "lg_month": "-", "lg_yday": "-", "lg_today": "-", "lg_mgr_month": "-", "lg_daily": {}})
    nv_ws = wb["네이버원본"]
    for r in results:
        days = nv_hist.setdefault(r["name"], {})
        if r["nv_dates"] is not None:
            for d in sorted(set(r["nv_dates"]) | {k for k in days if k >= r["nv_since"]}):
                new = r["nv_dates"].get(d, [0, 0])
                if days.get(d) != new:
                    nv_ws.append([stamp, r["name"], d, new[0], new[1]])
                days[d] = new
            r.update(nv_summary(days, today, yday, month_start))
        else:
            r.update({"nv_v_month": None, "nv_b_month": None, "nv_month": None, "nv_yday": None, "nv_daily": {}})
    for r in results:
        raw.append([stamp, target_day, r["team"], r["name"],
                    r["visit"] if r["visit"] is not None else "-",
                    r["blog"] if r["blog"] is not None else "-",
                    r["lg_total"], r["lg_month"], r["lg_yday"]])
    write_report(wb, results, prev, today, target_day)
    stores_out = []
    for r in results:
        p = prev.get(r["name"], (None, None, None))
        stores_out.append({"team": r["team"], "name": r["name"],
                           "visit": r["visit"], "visit_diff": diff(r["visit"], p[1]),
                           "blog": r["blog"], "blog_diff": diff(r["blog"], p[2]),
                           "lg_total": r["lg_total"], "lg_month": r["lg_month"], "lg_yday": r["lg_yday"],
                           "lg_today": r["lg_today"], "lg_mgr_month": r["lg_mgr_month"], "lg_daily": r["lg_daily"],
                           "nv_v_month": r["nv_v_month"], "nv_b_month": r["nv_b_month"], "nv_month": r["nv_month"],
                           "nv_yday": r["nv_yday"], "nv_daily": r["nv_daily"]})
    try:
        export_json({"updated": now.strftime("%Y-%m-%d %H:%M"), "lg_start": LG_START, "month": month_start[:7], "yday": yday,
                     "prev_day": max((v[0] for v in prev.values()), default=None),
                     "rows": stores_out})
    except Exception as e:
        print("※ 대시보드용 파일 저장 실패:", e)
    try:
        wb.save(DATA_FILE)
        print(f"\n저장 완료 → {DATA_FILE}")
    except PermissionError:
        alt = DATA_FILE.replace(".xlsx", f"_{now:%H%M}.xlsx")
        wb.save(alt)
        print(f"\n리뷰현황.xlsx 가 열려 있어서 다른 이름으로 저장했어요 → {alt}")
    print("끝.")


if __name__ == "__main__":
    main()
