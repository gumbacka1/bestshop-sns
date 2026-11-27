# care_videos.json 에서 '케어 소개' 영상만 골라 care 필드로 정리 (같은 품목 안에서 빈 곳은 채움)
import json, re, os
p = os.path.join(os.path.dirname(__file__), '..', 'data/care_videos.json'); d = json.load(open(p, encoding='utf-8'))
def score(s):
    return 3 if 'rmsf' in s else 2 if re.search('caresolution', s, re.I) else 1 if 'rentalcare' in s else 0
for v in d.values():
    c = sorted([x['src'] for x in v.get('videos', []) if score(x['src'])], key=lambda s: -score(s))
    v['care'] = c[0] if c else ''
for k, v in d.items():
    if not v['care']:
        cat = k.split('|')[0]
        alt = [w['care'] for kk, w in d.items() if kk.split('|')[0] == cat and w['care']]
        if cat == '김치냉장고' and not alt: alt = [w['care'] for kk, w in d.items() if kk.startswith('냉장고|') and w['care']]
        v['care'] = alt[0] if alt else ''
json.dump(d, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(sum(1 for v in d.values() if v['care']), len(d))
