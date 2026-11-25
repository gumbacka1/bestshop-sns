# 베스트샵 판촉 이미지 → 글자 인식(tesseract kor) → data/lge_full/bestshop_ocr.json
# 이미지는 /tmp/bs_img 에만 저장(저장소에는 글자만 올린다).
import json, os, re, subprocess, hashlib, urllib.request, sys
from concurrent.futures import ThreadPoolExecutor
D = os.path.join(os.path.dirname(__file__), '..', 'data', 'lge_full')
IMG = '/tmp/bs_img'; os.makedirs(IMG, exist_ok=True)
P = json.load(open(os.path.join(D, 'bestshop_promos.json'), encoding='utf-8'))['pages']
urls = []
for k, v in P.items():
    for u in v.get('images') or []:
        if u not in urls: urls.append(u)
print('이미지', len(urls))

def one(u):
    name = hashlib.md5(u.encode()).hexdigest()[:12] + os.path.splitext(u.split('?')[0])[1][:5]
    f = os.path.join(IMG, name)
    try:
        q = urllib.parse.quote(u, safe=':/?=&%')
        req = urllib.request.Request(q, headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://bestshop.lge.co.kr/'})
        data = urllib.request.urlopen(req, timeout=40).read()
        if len(data) < 12000: return u, {'skip': 'small'}
        open(f, 'wb').write(data)
        base = f + '_t'
        # 긴 배너는 1400px 높이로 잘라서 하나씩 인식(시간 초과 방지)
        subprocess.run(['convert', f + '[0]', '-colorspace', 'Gray', '-crop', '100%x1400', '+repage', base + '_%03d.png'],
                       check=False, capture_output=True)
        tiles = sorted(x for x in os.listdir(IMG) if x.startswith(os.path.basename(base) + '_'))
        out = []
        for tl in tiles or [os.path.basename(f)]:
            try:
                r = subprocess.run(['tesseract', os.path.join(IMG, tl), '-', '-l', 'kor+eng', '--psm', '6'],
                                   capture_output=True, text=True, timeout=120)
                out.append(r.stdout)
            except subprocess.TimeoutExpired:
                out.append('')
            if tl != os.path.basename(f):
                try: os.remove(os.path.join(IMG, tl))
                except OSError: pass
        t = '\n'.join(x.strip() for x in '\n'.join(out).split('\n') if len(x.strip()) > 1)
        return u, {'file': name, 'bytes': len(data), 'text': t}
    except Exception as e:
        return u, {'error': str(e)[:120]}

import urllib.parse
res = {}
with ThreadPoolExecutor(4) as ex:
    for u, r in ex.map(one, urls):
        res[u] = r
by_page = {}
for k, v in P.items():
    by_page[k] = {'title': v.get('title'), 'url': v.get('url'),
                  'ocr': [{'img': u, **res.get(u, {})} for u in v.get('images') or [] if res.get(u, {}).get('text')]}
json.dump({'images': res, 'pages': by_page}, open(os.path.join(D, 'bestshop_ocr.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, separators=(',', ':'))
print('글자 인식', sum(1 for r in res.values() if r.get('text')), '/', len(res))
