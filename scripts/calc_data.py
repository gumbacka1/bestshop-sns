# 계산기용 가벼운 모델 데이터: data/lge_full/products.json → calc/models.json
import json, os, re
B = os.path.join(os.path.dirname(__file__), '..')
P = json.load(open(os.path.join(B, 'data/lge_full/products.json'), encoding='utf-8'))
SMALL = {'주방소형가전', '가습기', '선풍기'}          # 소형가전(3만원) 짐작 — 화면에서 바꿀 수 있음
GROUP = {'세탁 건조기': '세탁·건조', '의류건조기': '세탁·건조', '세탁기': '세탁·건조',
         '가습 공기청정기': '공기청정기', '360° 공기청정기': '공기청정기', '무선청소기': '청소기'}
out = []
for i in P:
    m = i.get('modelName') or i.get('salesModelCode')
    p = i.get('obsOriginalPrice') or 0
    care = i.get('care') or {}
    pm = care.get('price_map') or {}
    if not m: continue
    if not p and not pm: continue
    sub = {}
    for k, v in pm.items():
        t = k.split('_')[0]
        mp = v.get('monthlyPrice') or v.get('originalPrice')
        if not mp: continue
        cur = sub.get(t)
        if cur is None or mp < cur[0]: sub[t] = [mp, v.get('originalPrice') or mp]
    c = i.get('categoryName') or ''
    img = (i.get('images') or [''])[0]
    out.append({
        'm': m, 'n': i.get('modelDisplayName') or m, 'c': c, 's': i.get('subCategoryName') or '',
        'g': GROUP.get(c, c), 'p': p, 'd': i.get('obsMemberPrice') or 0,
        'mb': 1 if i.get('다품목') == 'Y' else 0, 'jb': 1 if i.get('결합') == 'Y' else 0,
        'sm': 1 if c in SMALL else 0, 'o': 1 if i.get('lgecomOnlyFlag') == 'Y' else 0,
        'r': (i.get('modelReleaseDate') or '')[:7], 'rv': int(re.sub(r'\D','',str(i.get('reviewCount') or 0)) or 0),
        'img': img, 'sub': sub, 'care': (care.get('careServiceCycles') or [''])[0],
    })
# 다품목 혜택관 모델마스터(다른 대화 261126 수집)로 다품목·소형·그룹·쿠폰·제품별 캐시백 보정, 빠진 모델 추가
import csv
MP = os.path.join(B, 'data/lge_full/mltp/다품목_모델마스터.csv')
if os.path.exists(MP):
    idx = {x['m'].upper(): x for x in out}
    for r in csv.DictReader(open(MP, encoding='utf-8-sig')):
        m = r['모델명'].strip(); x = idx.get(m.upper())
        ip = lambda k: int(float(r.get(k) or 0) or 0)
        if not x:
            sub = {str(int(float(r['구독개월'] or 72))): [ip('구독월요금'), ip('구독월요금')]} if ip('구독월요금') else {}
            x = {'m': m, 'n': r['제품명'], 'c': r['제품군'], 's': '', 'g': r['그룹'], 'p': ip('정가'), 'd': ip('정가') - ip('판매가'),
                 'mb': 1, 'jb': 0, 'sm': 0, 'o': 0, 'r': '', 'rv': 0, 'img': '', 'sub': sub, 'care': '', 'manual': 1}
            out.append(x); idx[m.upper()] = x
        x['mb'] = 1; x['sm'] = 1 if r['구분'] == '소형' else 0; x['g'] = r['그룹'] or x['g']
        if ip('쿠폰할인'): x['cp'] = ip('쿠폰할인')
        if ip('제품별캐시백'): x['pc'] = ip('제품별캐시백')
# 수집에 빠진 캡처 모델(사용자 캡처 261126): 가격만 수동
if not any(x['m'] == 'OLED83G5KW' for x in out):
    out.append({'m': 'OLED83G5KW', 'n': 'LG 올레드 evo AI (벽걸이형)', 'c': 'TV', 's': 'OLED', 'g': 'TV', 'p': 13000000,
                'd': 0, 'mb': 1, 'jb': 1, 'sm': 0, 'o': 0, 'r': '', 'rv': 0, 'img': '', 'sub': {}, 'care': '', 'manual': 1})
for m, n, p, sub in [('D604MEE52', 'LG 일반냉장고 오브제컬렉션', 0, 23900), ('M301S31', 'LG 모던엣지 냉장고', 720000, 0)]:
    if not any(x['m'] == m for x in out):
        out.append({'m': m, 'n': n, 'c': '냉장고', 's': '', 'g': '냉장고', 'p': p, 'd': 0, 'mb': 0, 'jb': 0, 'sm': 0, 'o': 0, 'r': '', 'rv': 0,
                    'img': '', 'sub': {'72': [sub, sub]} if sub else {}, 'care': '', 'manual': 1})
out.sort(key=lambda x: (-x['rv'], x['m']))
json.dump({'updated': json.load(open(os.path.join(B, 'data/lge_full/meta.json'), encoding='utf-8')).get('updated'), 'models': out},
          open(os.path.join(B, 'calc/models.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print(len(out), os.path.getsize(os.path.join(B, 'calc/models.json')))
