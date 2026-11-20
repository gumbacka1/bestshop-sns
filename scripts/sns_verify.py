# -*- coding: utf-8 -*-
"""
SNS 대시보드 자동 점검 (수집이 끝날 때마다 깃허브에서 실행, Claude 사용량 없음)
결과: data/verify.json  →  Claude 예약 작업(10시 27분)이 읽고 한 줄로 알려요.

점검 항목
 1) 297개 지점이 오늘 공식(api)으로 수집됐는지
 2) 팔로워가 0이거나 비어 있는 곳
 3) 팔로워 전일비가 10% 넘게 바뀐 곳 (계정이 잘못 연결됐을 때 티가 남)
 4) 경북 내 권역 6곳 주간 증가·증가율을 대시보드와 같은 규칙으로 따로 계산 (월요일 아침 − 전 월요일 아침)
사용: python3 sns_verify.py data/latest.json data/daily.json data/verify.json
"""
import json, sys, datetime as dt

lat_p, day_p, out_p = sys.argv[1:4]
KST = dt.timezone(dt.timedelta(hours=9))
now = dt.datetime.now(KST)
today = now.date().isoformat()
latest = json.load(open(lat_p, encoding='utf-8'))
daily = json.load(open(day_p, encoding='utf-8'))
MY = ['황금본점', '율하점', '범어점', '제주본점', '이도본점', '서귀포점']
KNOWN = {'lgbestshop_munrae'}   # 문래점: 공식 조회 오류 110, 알고 있는 곳

# 1) 오늘 공식 수집
api = [r for r in latest if r.get('igDate') == today and r.get('igSrc') == 'api']
missing = [r['store'] for r in latest if r not in api and r.get('handle') not in KNOWN]
temp = [r['store'] for r in latest if r.get('igSrc') == 'fallback' and r.get('handle') not in KNOWN]

# 2) 0 또는 빈 값 (공식 수집된 곳 중)
empty = [r['store'] for r in api if not r.get('followers')]

# 3) 전일비 10% 초과
dates = sorted({r['date'] for r in daily})
by = {(r['date'], r['handle']): r for r in daily}
jump = []
if today in dates and dates.index(today) > 0:
    yday = dates[dates.index(today) - 1]
    for r in api:
        a, b = by.get((yday, r['handle']), {}).get('followers'), r.get('followers')
        if a and b and abs(b - a) / a > 0.10:
            jump.append({'store': r['store'], 'from': a, 'to': b, 'rate': round((b - a) / a * 100, 1)})

# 4) 주간 증가 (대시보드 규칙, 261120 변경: 가장 최근 월요일 아침값 − 그 전 월요일 아침값 = 월~일 한 주, 그 전 월요일 기록이 없으면 가장 오래된 기록일)
mondays = [d for d in dates if dt.date.fromisoformat(d).weekday() == 0]
base = mondays[-1] if mondays else (dates[-1] if dates else None)
prev = None
if base:
    target = (dt.date.fromisoformat(base) - dt.timedelta(days=7)).isoformat()
    before = [d for d in dates if d < base]
    prev = target if target in dates else (before[0] if before else None)
handle = {r['store']: r['handle'] for r in latest}
week = []
for st in MY:
    h = handle.get(st)
    am = lambda r: r.get('am_followers', r.get('followers'))   # 아침값(없으면 그날 값)
    a = am(by.get((prev, h), {})) if prev else None
    b = am(by.get((base, h), {})) if base else None
    d = (b - a) if (a is not None and b is not None) else None
    week.append({'store': st, 'base': b, 'prev': a, 'diff': d, 'rate': round(d / a * 100, 1) if d is not None and a else None})

problems = []
if missing:
    problems.append(f"오늘 공식 수집 안 된 곳 {len(missing)}개")
if empty:
    problems.append(f"팔로워 0·빈 값 {len(empty)}개")
if jump:
    problems.append(f"전일비 10% 넘게 바뀐 곳 {len(jump)}개")
res = {'at': now.strftime('%Y-%m-%d %H:%M'), 'date': today, 'total': len(latest), 'api_today': len(api),
       'ok': not problems, 'problems': problems,
       'missing': missing[:30], 'temp_left': len(temp), 'empty': empty[:30], 'jump': jump[:30],
       'week': {'base': base, 'prev': prev, 'is_monday': now.weekday() == 0, 'rows': week}}
json.dump(res, open(out_p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f"점검 {'이상 없음' if res['ok'] else ' / '.join(problems)} | 공식 {len(api)}/{len(latest)}")
