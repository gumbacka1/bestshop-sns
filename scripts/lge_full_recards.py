# 저장된 안내 글(benefits.json)에서 제휴카드 표만 다시 뽑는다(수집 없이 다시 계산할 때)
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from lge_full_collect import card_rows
p = os.path.join(os.path.dirname(__file__), '..', 'data', 'lge_full', 'benefits.json')
B = json.load(open(p, encoding='utf-8'))
for k, v in B.items():
    v['cards'] = card_rows(v.get('text') or '') if '카드' in k else []
json.dump(B, open(p, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print({k: len(v['cards']) for k, v in B.items()})
