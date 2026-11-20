# -*- coding: utf-8 -*-
"""
하이프라자 297개 지점 SNS 직접 수집기 (경인담당 대시보드 없이 동작)
 - 카톡 채널 친구 수: 카카오톡 채널 공개 홈 정보 (로그인 불필요)
 - 인스타 팔로워·게시물·최근 게시일·릴스 조회수: 메타 공식 Instagram Graph API (Business Discovery)
   → 업무용 인스타 비즈니스 계정 + 메타 앱 토큰이 있어야 해요. 없으면 인스타는 건너뛰어요.

사용:
  python3 sns_collect.py stores_master.json daily_in.json(없으면 -) daily_out.json latest_out.json
  인스타까지 받으려면 환경변수 IG_TOKEN(접속 키), IG_USER_ID(우리 비즈니스 계정 ID)를 넣어요.
결과 파일 형식은 대시보드가 쓰는 것과 같아요(daily: 날짜별 팔로워·카톡, latest: 최신값).
"""
import json, os, sys, time, datetime as dt, urllib.request, urllib.parse, urllib.error

master, din, dout, lout = sys.argv[1:5]
if master.endswith('.tsv'):   # 한 줄에 "담당|지점|인스타아이디|카톡아이디"
    stores = [dict(zip(('team', 'store', 'ig', 'kakao'), l.rstrip('\n').split('|'))) for l in open(master, encoding='utf-8') if l.strip()]
else:
    stores = json.load(open(master))
KST = dt.timezone(dt.timedelta(hours=9))
now = dt.datetime.now(KST)
today = now.date().isoformat()
UA = {'User-Agent': 'Mozilla/5.0'}


def get_json(url, timeout=20):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))


def kakao(cid):
    d = get_json(f'https://pf.kakao.com/rocket-web/web/profiles/{cid}/home')
    return d['profile'].get('friend_count')


IG_TOKEN, IG_USER = os.environ.get('IG_TOKEN'), os.environ.get('IG_USER_ID')
FIELDS = 'followers_count,follows_count,media_count,media.limit(25){timestamp,media_product_type,view_count,permalink}'
ENGAGE_TEAM = os.environ.get('ENGAGE_TEAM', '경북담당').strip()   # 이 담당만 전체 게시물 누적 좋아요·댓글을 셈 (261120 사용자 요청)
EFIELDS = 'followers_count,follows_count,media_count,media.limit(50){timestamp,media_product_type,view_count,permalink,like_count,comments_count}'


def kst(ts):   # 메타 시각(UTC) → 한국 시각 'YYYY-MM-DD HH:MM'
    try:
        return dt.datetime.strptime(ts[:19], '%Y-%m-%dT%H:%M:%S').replace(tzinfo=dt.timezone.utc).astimezone(KST).strftime('%Y-%m-%d %H:%M')
    except Exception:
        return ts[:16]


def bd_get(handle, fields):
    q = urllib.parse.urlencode({'fields': f'business_discovery.username({handle}){{{fields}}}', 'access_token': IG_TOKEN})
    return get_json(f'https://graph.facebook.com/v25.0/{IG_USER}?{q}')['business_discovery']


def engage(handle, bd):   # 전체 게시물 좋아요·댓글 합계 (50개씩 다음 장까지 모두)
    m = bd.get('media') or {}
    allm = list(m.get('data') or [])
    cur = ((m.get('paging') or {}).get('cursors') or {}).get('after')
    pages = 0
    while cur and (m.get('paging') or {}).get('next') and pages < 20:
        pages += 1
        time.sleep(0.4)
        m = bd_get(handle, f'media.after({cur}).limit(50){{like_count,comments_count}}').get('media') or {}
        allm += m.get('data') or []
        cur = ((m.get('paging') or {}).get('cursors') or {}).get('after')
    hidden = sum(1 for x in allm if x.get('like_count') is None)
    return {'likesTot': sum(x.get('like_count') or 0 for x in allm), 'commentsTot': sum(x.get('comments_count') or 0 for x in allm),
            'likesHidden': hidden, 'engageN': len(allm), 'engageAt': now.strftime('%Y-%m-%d %H:%M')}


def instagram(handle, full=False):
    bd = bd_get(handle, EFIELDS if full else FIELDS)
    media = ((bd.get('media') or {}).get('data') or [])[:25]   # 릴스·최근 게시는 다른 담당과 같게 최근 25개 기준
    reels = [m for m in media if m.get('media_product_type') == 'REELS' and m.get('view_count') is not None]
    top = max(reels, key=lambda m: m['view_count']) if reels else None
    return {'followers': bd.get('followers_count'), 'following': bd.get('follows_count'), 'posts': bd.get('media_count'),
            'lastPost': media[0]['timestamp'][:10] if media else None,
            'reelsTot': sum(m['view_count'] for m in reels) if reels else None,
            'reelsMax': top['view_count'] if top else None, 'reelsN': len(reels) if reels else None,
            'reelsUrl': top.get('permalink') if top else None,
            # 261120: 최근 게시글 표용 — 경북담당 25개(조회수·좋아요·댓글), 다른 담당 10개(조회수만)
            'recent': [{'t': kst(m['timestamp']), 'url': m.get('permalink'), 'type': m.get('media_product_type'), 'v': m.get('view_count'),
                        **({'l': m.get('like_count'), 'c': m.get('comments_count')} if full else {})} for m in media[:25 if full else 10]],
            **(safe_engage(handle, bd) if full else {})}


def safe_engage(handle, bd):   # 좋아요·댓글 다음 장 조회가 실패해도 팔로워 등은 그대로 저장 (이전 누적값 유지)
    try:
        return engage(handle, bd)
    except Exception:
        return {}


daily = {(r['date'], r['handle']): r for r in (json.load(open(din)) if din != '-' else [])}
old_latest = {}
if os.path.exists(lout):
    try:
        old_latest = {r['handle']: r for r in json.load(open(lout))}
    except Exception:
        pass
latest, errs = [], {'kakao': 0, 'ig': 0}
IG_MAX = int(os.environ.get('IG_MAX', '89'))   # 메타 앱 시간당 호출 한도 때문에 한 번에 최대 이만큼만 (새 글 알림 지점 6개는 별도)
SKIP_KAKAO = os.environ.get('SKIP_KAKAO') == '1'   # 1이면 이번 실행은 카톡을 건너뛰고 이전 값 유지
WATCH = [w.strip() for w in os.environ.get('WATCH', '').split(',') if w.strip()]   # 새 글 알림 지점 이름 → 매 실행마다 인스타 확인
TEAM = os.environ.get('TEAM_REFRESH', '').strip()   # 예: 경북담당 → 이 담당 지점은 이번 실행에 무조건 새로 수집(시간별 기록 + 하루 숫자도 실시간 반영, 261120 사용자 요청)
hourly = []
new_posts = []
stores = sorted(stores, key=lambda s: 0 if s['store'] in WATCH else 1)   # 알림 지점 먼저
ig_used, ig_stop, ig_codes = 0, False, {}
# 오늘 아직 인스타를 못 받은 지점부터 순서대로
for s in stores:
    base = {'team': s['team'], 'store': s['store'], 'handle': s['ig']}
    prev = old_latest.get(s['ig'], {})
    rec = {**base, **{k: prev.get(k) for k in ('followers', 'following', 'posts', 'lastPost', 'kakao', 'reelsTot', 'reelsMax', 'reelsN', 'reelsUrl', 'igDate', 'igSrc', 'recent', 'seen', 'likesTot', 'commentsTot', 'likesHidden', 'engageN', 'engageAt')}}
    rec['status'] = 'ok'
    if s.get('kakao') and not SKIP_KAKAO:
        try:
            rec['kakao'] = kakao(s['kakao'])
        except Exception:
            errs['kakao'] += 1; rec['status'] = 'partial'
        time.sleep(0.4)
    ig_now = False
    watch = s['store'] in WATCH or (TEAM and s['team'] == TEAM)
    if IG_TOKEN and IG_USER and not ig_stop and (watch or ((rec.get('igDate') != today or rec.get('igSrc') == 'fallback') and ig_used < IG_MAX)):
        if not watch:
            ig_used += 1
        try:
            rec.update(instagram(s['ig'], full=bool(ENGAGE_TEAM) and s['team'] == ENGAGE_TEAM)); rec['igDate'] = today; rec['igSrc'] = 'api'; ig_now = True
            if TEAM and s['team'] == TEAM:
                hourly.append({**base, 'date': today, 'time': now.strftime('%H:%M'), 'followers': rec.get('followers'),
                               'following': rec.get('following'), 'posts': rec.get('posts'),
                               'likes': rec.get('likesTot'), 'comments': rec.get('commentsTot')})
            if s['store'] in WATCH:
                urls = [x['url'] for x in (rec.get('recent') or [])[:5] if x.get('url')]
                if prev.get('seen') is not None:   # 처음 실행 때는 기준만 잡고 알리지 않음
                    for x in (rec.get('recent') or [])[:5]:
                        if x.get('url') and x['url'] not in prev['seen']:
                            new_posts.append({'team': s['team'], 'store': s['store'], 'handle': s['ig'], **x})
                rec['seen'] = (urls + [u for u in (prev.get('seen') or []) if u not in urls])[:15]
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8', 'ignore')
            try:
                c = str(json.loads(body)['error'].get('code'))
            except Exception:
                c = str(e.code)
            ig_codes[c] = ig_codes.get(c, 0) + 1
            if c == '190':
                ig_stop = True   # 키 만료·무효
            if '"code":4' in body or '"code":17' in body or '"code":32' in body:
                ig_stop = True   # 한도 도달 → 다음 실행 때 이어서
            errs['ig'] += 1; rec['status'] = 'partial'
        except Exception:
            errs['ig'] += 1; rec['status'] = 'partial'
        time.sleep(0.4)
    rec['updated'] = now.strftime('%Y-%m-%d %H:%M')
    latest.append(rec)
    key = (today, s['ig'])
    old = daily.get(key, {})
    daily[key] = {**base, 'date': today,
                  'followers': rec.get('followers') if ig_now else old.get('followers'),
                  'following': rec.get('following') if ig_now else old.get('following'),
                  'kakao': rec.get('kakao'),
                  'posts': rec.get('posts') if ig_now else old.get('posts')}
    # 주간 증가 기준값: 그날 아침(12시 전) 수집값을 따로 고정 — 경북 시간별 수집이 덮어써도 전 담당 같은 시각으로 비교 (261120)
    for k in ('followers', 'following'):
        if old.get('am_' + k) is not None:
            daily[key]['am_' + k] = old['am_' + k]
        elif ig_now and now.hour < 12 and rec.get(k) is not None:
            daily[key]['am_' + k] = rec.get(k)

rows = sorted(daily.values(), key=lambda r: (r['date'], r['team'] or '', r['store'] or ''))
ddir = os.path.dirname(os.path.abspath(dout))


def merge_month(folder, ym, new, keyf):   # 월별 보관 파일(data/<folder>/YYYY-MM.json)에 합쳐 저장
    os.makedirs(os.path.join(ddir, folder), exist_ok=True)
    fp = os.path.join(ddir, folder, ym + '.json')
    cur = {}
    if os.path.exists(fp):
        cur = {keyf(r): r for r in json.load(open(fp, encoding='utf-8'))}
    for r in new:
        cur[keyf(r)] = r
    json.dump(sorted(cur.values(), key=keyf), open(fp, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))


for ym in sorted({r['date'][:7] for r in rows}):
    merge_month('daily', ym, [r for r in rows if r['date'][:7] == ym], lambda r: (r['date'], r['team'] or '', r['store'] or '', r['handle']))
if hourly:
    merge_month('hourly', today[:7], hourly, lambda r: (r['date'], r['time'], r['team'] or '', r['store'] or '', r['handle']))
cut = (now.date() - dt.timedelta(days=62)).isoformat()   # 화면용 daily.json은 최근 62일만(가볍게), 전체는 data/daily/월별 파일
json.dump([r for r in rows if r['date'] >= cut], open(dout, 'w'), ensure_ascii=False, separators=(',', ':'))
json.dump(latest, open(lout, 'w'), ensure_ascii=False, separators=(',', ':'))
json.dump(new_posts, open(os.path.join(os.path.dirname(os.path.abspath(lout)), 'new_posts.json'), 'w'), ensure_ascii=False, indent=1)
if WATCH:
    print(f"알림 지점 새 글 {len(new_posts)}개" + ''.join(f"\n - {p['store']} {p['t']} {p['url']}" for p in new_posts))
if TEAM:
    print(f"{TEAM} 시간별 수집 {len(hourly)}곳 ({now:%H:%M})")
done_today = sum(1 for r in latest if r.get('igDate') == today and r.get('igSrc') == 'api')
print(f"인스타 오늘 공식 수집 {done_today}/{len(latest)} (이번 실행 {ig_used}건{', 한도 도달' if ig_stop and '190' not in ig_codes else ''}) | 오류 코드 {ig_codes or '없음'}")
print(f"완료 {now:%Y-%m-%d %H:%M} | 지점 {len(latest)} | 카톡 {'건너뜀' if SKIP_KAKAO else '실패 ' + str(errs['kakao'])} | 인스타 {'실패 ' + str(errs['ig']) if IG_TOKEN else '토큰 없음(건너뜀)'}")
