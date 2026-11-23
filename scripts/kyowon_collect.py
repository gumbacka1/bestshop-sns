# -*- coding: utf-8 -*-
"""교원(라이프·케어) 접수현황 → 지점·매니저·상품별 구좌 집계 → data/kyowon.json (암호화)

- 로그인 정보는 깃허브 Secrets(KW_LIFE_ID/PW, KW_CARE_ID/PW)에서만 읽음. 로그에 찍지 않음.
- 고객 이름·전화번호는 저장하지 않음 (지점·매니저·상품별 숫자만).
- 결과는 관리자 비밀번호(KW_ADMIN_PW)로 암호화해서 저장 → 공유 페이지 관리자 로그인 때만 풀림.
- 기준: 이번 달 1일 ~ 오늘 접수일자, 숫자는 구좌. 신청완료 = 완료, 예약·콜대기중 = 예약 (261123 사용자 결정)
- KW_DEBUG=1 이면 화면 구조(검색 줄·엑셀 버튼·페이지 번호)만 로그에 남김 (고객 정보 없음)
"""
import base64, json, os, re, sys, tempfile, time, datetime as dt
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'data' / 'kyowon.json'
KST = dt.timezone(dt.timedelta(hours=9))
DEBUG = os.environ.get('KW_DEBUG') == '1'

SITES = {
    'life': {'base': 'https://kyowonlifecall.co.kr/KYOWONLIFE', 'id': 'KW_LIFE_ID', 'pw': 'KW_LIFE_PW', 'label': '라이프'},
    'care': {'base': 'https://lgcaresolutionkyowon.co.kr/LGCARE', 'id': 'KW_CARE_ID', 'pw': 'KW_CARE_PW', 'label': '케어'},
}
SALT = b'bestshop-sns-kyowon-v1'
DONE = {'신청완료'}
RSV = {'예약', '콜대기중'}


def log(*a):
    print(*a, flush=True)


# ---------- 지점 목록 ----------
def norm(s):
    s = re.sub(r'\s+', '', str(s or ''))
    s = s.replace('베스트샵', '').replace('LG전자', '').replace('(', '').replace(')', '')
    return s


def load_master():
    stores, order = [], []
    for ln in (ROOT / 'scripts' / 'master.tsv').read_text(encoding='utf-8').splitlines():
        p = ln.split('|')
        if len(p) < 2 or not p[1].strip():
            continue
        team, store = p[0].strip(), p[1].strip()
        stores.append((team, store))
        if team not in order:
            order.append(team)
    alias = {}
    ap = ROOT / 'scripts' / 'kyowon_alias.tsv'
    if ap.exists():
        for ln in ap.read_text(encoding='utf-8').splitlines():
            if ln.startswith('#') or '|' not in ln:
                continue
            a, b = ln.split('|', 1)
            alias[norm(a)] = b.strip()
    return stores, order, alias


def matcher(stores, alias):
    by = {norm(s): s for _, s in stores}
    names = {s for _, s in stores}

    def f(name):
        n = norm(name)
        if n in alias and alias[n] in names:
            return alias[n]
        if n in by:
            return by[n]
        for k in (n + '점', n.rstrip('점'), n.replace('본점', '점'), n.replace('점', '본점', 1)):
            if k in by:
                return by[k]
        return None
    return f


# ---------- 표 읽기 ----------
def hkey(h):
    return re.sub(r'\s+', '', str(h or ''))


COLS = {'매장명': 'store', '담당매니져': 'mgr', '담당매니저': 'mgr', '담당매니져사번': 'mid', '담당매니저사번': 'mid',
        '가입상품': 'prod', '가입구좌': 'qty', '고객상태': 'status', '접수일시': 'at', '신청완료일자': 'done_at', '조직구분': 'org'}


def rows_from_grid(grid):
    """2차원 표(머리 줄 포함) → [{store,mgr,...}]"""
    hi = next((i for i, r in enumerate(grid) if any(hkey(c) == '매장명' for c in r)), None)
    if hi is None:
        return []
    head = [COLS.get(hkey(c)) for c in grid[hi]]
    out = []
    for r in grid[hi + 1:]:
        d = {}
        for k, v in zip(head, r):
            if k and k not in d:
                d[k] = '' if v is None else str(v).strip()
        if d.get('store') and d.get('status') and hkey(d.get('status')) != '고객상태':
            out.append(d)
    return out


def read_file(path):
    raw = Path(path).read_bytes()
    import pandas as pd
    grids = []
    try:
        if raw[:2] == b'PK' or raw[:4] == b'\xd0\xcf\x11\xe0':
            xl = pd.read_excel(path, sheet_name=None, header=None, dtype=str)
            grids = [df.fillna('').values.tolist() for df in xl.values()]
        else:
            txt = None
            for enc in ('utf-8', 'cp949', 'euc-kr'):
                try:
                    txt = raw.decode(enc); break
                except Exception:
                    pass
            from io import StringIO
            grids = [df.fillna('').astype(str).values.tolist() for df in pd.read_html(StringIO(txt), header=None)]
    except Exception as e:
        log('  엑셀 읽기 실패:', type(e).__name__, str(e)[:200])
        return None
    if DEBUG:
        for g in grids:
            log('  [엑셀] 크기', len(g), 'x', len(g[0]) if g else 0, '| 앞 줄:', [str(c)[:12] for c in (g[0] if g else [])][:16])
            hi = next((i for i, r in enumerate(g) if any(hkey(c) == '매장명' for c in r)), None)
            log('  [엑셀] 머리 줄 위치:', hi, [str(c)[:12] for c in (g[hi] if hi is not None else [])][:20])
    best = []
    for g in grids:
        r = rows_from_grid(g)
        if len(r) > len(best):
            best = r
    return best


JS_GRID = """() => {
  const t = [...document.querySelectorAll('table')].filter(x => /매장명/.test(x.innerText) && /고객상태/.test(x.innerText));
  const rows = [];
  for (const tb of t) for (const tr of tb.querySelectorAll('tr')) {
    const cs = [...tr.children].filter(c => c.tagName === 'TD' || c.tagName === 'TH');
    if (cs.some(c => c.querySelector('table'))) continue;
    const v = cs.map(c => c.innerText.replace(/\\s+/g, ' ').trim()).filter((x, i) => !(x === '' && cs[i].querySelector('img')));
    if (v.length >= 10) rows.push(v);
  }
  return rows;
}"""


# ---------- 사이트 ----------
def login(page, base, uid, pw):
    page.goto(base + '/easycti/jsp/main/best_login.jsp', wait_until='domcontentloaded', timeout=90000)
    page.wait_for_timeout(1500)
    boxes = page.locator('input:visible:not([type=checkbox]):not([type=hidden]):not([type=button]):not([type=submit]):not([type=image])')
    if boxes.count() < 2:
        raise RuntimeError('로그인 칸을 못 찾음')
    boxes.nth(0).fill(uid)
    boxes.nth(1).fill(pw)
    btn = page.locator('button:visible, input[type=submit]:visible, input[type=image]:visible, a:has(img[src*="login" i]):visible').first
    with page.expect_navigation(timeout=60000, wait_until='domcontentloaded'):
        if btn.count():
            btn.click()
        else:
            boxes.nth(1).press('Enter')
    page.wait_for_timeout(1500)
    if 'login' in page.url.lower():
        raise RuntimeError('로그인 실패 (아이디·비밀번호 확인 필요)')


def search(page, base, d1, d2):
    page.goto(base + '/easycti/jsp/list/best_list.jsp', wait_until='domcontentloaded', timeout=120000)
    page.wait_for_timeout(2000)
    ok = page.evaluate("""([a, b]) => {
      const ins = [...document.querySelectorAll('input')].filter(i => /^\\d{4}-\\d{2}-\\d{2}$/.test(i.value) || /date|sdate|edate|start|end/i.test(i.name + i.id));
      if (ins.length < 2) return 'no-date';
      ins[0].value = a; ins[1].value = b;
      ['input','change'].forEach(e => { ins[0].dispatchEvent(new Event(e, {bubbles:true})); ins[1].dispatchEvent(new Event(e, {bubbles:true})); });
      const td = ins[1].closest('td') || ins[1].parentElement;
      const ls = [...td.querySelectorAll('a, button, input[type=image]')];
      const go = ls[ls.length - 1];
      if (!go) return 'no-btn';
      go.click(); return 'ok';
    }""", [d1, d2])
    if ok != 'ok':
        raise RuntimeError('조회 실패: ' + ok)
    page.wait_for_load_state('domcontentloaded', timeout=120000)
    ov = page.locator('text=조회 요청 시간')
    for _ in range(90):
        if not ov.count() or not ov.first.is_visible():
            break
        page.wait_for_timeout(1000)
    page.wait_for_timeout(1500)


def debug_dump(page):
    info = page.evaluate("""() => {
      const strip = h => h.replace(/010-\\d{3,4}-[\\d*]{4}/g, '010-****').slice(0, 1500);
      const ins = [...document.querySelectorAll('input')].filter(i => /^\\d{4}-\\d{2}-\\d{2}$/.test(i.value));
      const bar = ins[0] ? (ins[0].closest('tr') || ins[0].parentElement).outerHTML : 'no date input';
      const xl = [...document.querySelectorAll('a, img, button')].filter(e => /엑셀|excel|xls/i.test(e.outerHTML)).map(e => (e.closest('a') || e).outerHTML).slice(0, 3);
      const pg = [...document.querySelectorAll('td')].filter(td => /\\d\\s*\\|\\s*\\d/.test(td.innerText) && !td.querySelector('table')).map(td => td.outerHTML).slice(0, 1);
      const forms = [...document.forms].map(f => f.name + ' ' + f.method + ' ' + f.action);
      return {url: location.href, bar: strip(bar), excel: xl.map(strip), paging: pg.map(strip), forms};
    }""")
    for k, v in info.items():
        log('  [점검]', k, ':', v)


def try_excel(page):
    el = page.locator('a:has(img[src*="excel" i]), a:has(img[src*="xls" i]), a:has-text("엑셀"), img[src*="excel" i]').first
    if not el.count():
        log('  엑셀 버튼 없음')
        return None
    try:
        with page.expect_download(timeout=180000) as dl:
            el.click()
        fp = Path(tempfile.mkdtemp()) / 'kw.xls'
        dl.value.save_as(fp)
        rows = read_file(fp)
        fp.unlink(missing_ok=True)
        return rows
    except Exception as e:
        log('  엑셀 받기 실패:', type(e).__name__, str(e)[:200])
        return None


def page_rows(page):
    return rows_from_grid(page.evaluate(JS_GRID))


def try_pages(page, limit=400):
    rows, seen, n = [], set(), 1
    while n <= limit:
        cur = page_rows(page)
        key = json.dumps(cur[:2], ensure_ascii=False)
        if not cur or key in seen:
            break
        seen.add(key)
        rows += cur
        n += 1
        nxt = page.locator(f'a:text-is("{n}")').first
        if not nxt.count():
            arrows = page.locator('a:has(img[src*="next" i])')
            if not arrows.count():
                break
            arrows.first.click()
        else:
            nxt.click()
        page.wait_for_load_state('domcontentloaded', timeout=120000)
        page.wait_for_timeout(1200)
    return rows


def qty(s):
    m = re.search(r'\d+', s or '')
    return int(m.group()) if m else 1


def mask(name):
    name = (name or '').strip()
    if '*' in name or len(name) < 2:
        return name or '-'
    return name[0] + '*' + name[2:] if len(name) >= 3 else name[0] + '*'


def aggregate(rows, match, today, yday):
    agg, unmatched, status = {}, {}, {}
    for r in rows:
        st = r.get('status', '')
        status[st] = status.get(st, 0) + 1
        kind = 'd' if st in DONE else ('r' if st in RSV else None)
        if not kind:
            continue
        s = match(r.get('store'))
        q = qty(r.get('qty'))
        if not s:
            unmatched[r.get('store', '')] = unmatched.get(r.get('store', ''), 0) + q
            continue
        a = agg.setdefault(s, {'d': 0, 'r': 0, 'dt': 0, 'rt': 0, 'dy': 0, 'ry': 0, 'mgr': {}, 'prod': {}})
        a[kind] += q
        day = (r.get('done_at') if kind == 'd' and r.get('done_at') else r.get('at', ''))[:10]
        if day == today:
            a[kind + 't'] += q
        elif day == yday:
            a[kind + 'y'] += q
        mk = (r.get('mid') or '') + '|' + mask(r.get('mgr'))
        m = a['mgr'].setdefault(mk, [0, 0])
        m[0 if kind == 'd' else 1] += q
        p = a['prod'].setdefault(r.get('prod') or '-', [0, 0])
        p[0 if kind == 'd' else 1] += q
    for a in agg.values():   # 사번은 묶는 데만 쓰고 저장 안 함
        a['mgr'] = [[k.split('|', 1)[1], v[0], v[1]] for k, v in sorted(a['mgr'].items(), key=lambda x: -(x[1][0] + x[1][1]))]
        a['prod'] = [[k, v[0], v[1]] for k, v in sorted(a['prod'].items())]
    return agg, unmatched, status


def collect_site(pw_ctx, key, cfg, d1, d2, match, today, yday):
    uid, pw = os.environ.get(cfg['id'], ''), os.environ.get(cfg['pw'], '')
    if not uid or not pw:
        raise RuntimeError(cfg['id'] + ' / ' + cfg['pw'] + ' 비밀 칸이 비어 있음')
    br = pw_ctx.chromium.launch()
    ctx = br.new_context(accept_downloads=True, locale='ko-KR', timezone_id='Asia/Seoul')
    page = ctx.new_page()
    page.on('dialog', lambda d: (log('  [알림창]', d.message[:100]), d.accept()))
    try:
        login(page, cfg['base'], uid, pw)
        log(' ', cfg['label'], '로그인 됨')
        search(page, cfg['base'], d1, d2)
        if DEBUG:
            debug_dump(page)
            log('  첫 쪽 줄 수:', len(page_rows(page)))
        rows = try_excel(page)
        how = 'excel'
        if not rows:
            search(page, cfg['base'], d1, d2)
            rows, how = try_pages(page), 'pages'
        log(' ', cfg['label'], how, len(rows), '줄')
        if not rows:
            raise RuntimeError('표를 못 읽음')
        agg, un, st = aggregate(rows, match, today, yday)
        return {'ok': True, 'at': dt.datetime.now(KST).strftime('%Y-%m-%d %H:%M'), 'how': how, 'n': len(rows),
                'stores': agg, 'unmatched': un, 'status': st}
    finally:
        ctx.close(); br.close()


# ---------- 암호화 ----------
def kdf(pw, salt):
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    return PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=200000).derive(pw.encode())


def enc(obj, pw):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    salt, iv = SALT, os.urandom(12)   # 고정 salt: 공유 페이지가 로그인 때 만든 키를 세션에 보관해 다시 씀
    ct = AESGCM(kdf(pw, salt)).encrypt(iv, json.dumps(obj, ensure_ascii=False, separators=(',', ':')).encode(), None)
    b = lambda x: base64.b64encode(x).decode()
    return {'v': 1, 'salt': b(salt), 'iv': b(iv), 'ct': b(ct)}


def dec(box, pw):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    u = base64.b64decode
    return json.loads(AESGCM(kdf(pw, u(box['salt']))).decrypt(u(box['iv']), u(box['ct']), None))


def main():
    apw = os.environ.get('KW_ADMIN_PW', '')
    if not apw:
        sys.exit('KW_ADMIN_PW 비밀 칸이 비어 있음')
    now = dt.datetime.now(KST)
    today = now.strftime('%Y-%m-%d')
    yday = (now - dt.timedelta(days=1)).strftime('%Y-%m-%d')
    d1 = now.strftime('%Y-%m-01')
    stores, order, alias = load_master()
    match = matcher(stores, alias)
    prev = {}
    if OUT.exists():
        try:
            prev = dec(json.loads(OUT.read_text(encoding='utf-8')), apw)
        except Exception as e:
            log('이전 자료 못 풂(처음이거나 비밀번호 바뀜):', type(e).__name__)
    from playwright.sync_api import sync_playwright
    sites = {}
    with sync_playwright() as p:
        for key, cfg in SITES.items():
            log('▶', cfg['label'])
            for t in range(2):
                try:
                    sites[key] = collect_site(p, key, cfg, d1, today, match, today, yday)
                    break
                except Exception as e:
                    log('  실패', t + 1, ':', type(e).__name__, str(e)[:200])
                    time.sleep(5)
            if key not in sites:
                old = (prev.get('sites') or {}).get(key)
                if old and old.get('month') == d1[:7]:
                    old = dict(old); old['ok'] = False; old['stale'] = True
                    sites[key] = old
                else:
                    sites[key] = {'ok': False, 'stores': {}, 'unmatched': {}, 'status': {}}
            sites[key]['month'] = d1[:7]
    data = {'updated': now.strftime('%Y-%m-%d %H:%M'), 'from': d1, 'to': today, 'today': today, 'yday': yday,
            'teams': order, 'stores': [[t, s] for t, s in stores], 'sites': sites}
    if not any(s.get('ok') for s in sites.values()) and prev:
        sys.exit('두 사이트 모두 실패 — 이전 자료 유지')
    OUT.write_text(json.dumps(enc(data, apw), ensure_ascii=False), encoding='utf-8')
    import difflib
    names = [st for _, st in stores]
    for k, s in sites.items():
        un = s.get('unmatched') or {}
        log(SITES[k]['label'], '상태별 줄 수:', s.get('status'), '| 못 맞춘 매장:', len(un))
        for n, q in sorted(un.items(), key=lambda x: -x[1]):
            log('   못맞춤', n, q, '구좌 → 비슷한 우리 지점:', difflib.get_close_matches(n, names, n=2, cutoff=0.5))
    log('저장:', OUT)


if __name__ == '__main__':
    main()
