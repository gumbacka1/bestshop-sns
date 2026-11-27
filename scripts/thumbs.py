# 미리보기용 작은 사진 묶음(커밋 안 함, 실행 결과물로만 내려받음)
import json, io, base64, urllib.request, concurrent.futures as cf
from PIL import Image
D = json.load(open('data/lge_dotcom.json', encoding='utf-8'))
MD = json.load(open('calc/models.json', encoding='utf-8'))['models']
urls = set()
for c in D['cats']:
    for x in c['all']: urls.add(x['img'])
    for g in c['groups']:
        for x in c['buy'][g] + c['sub'][g]: urls.add(x['img'])
for x in MD:
    if x.get('img'): urls.add(x['img'])
urls = [u for u in urls if u]
def one(u):
    try:
        b = urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0 Chrome/124'}), timeout=20).read()
        im = Image.open(io.BytesIO(b)).convert('RGB'); im.thumbnail((180, 180))
        o = io.BytesIO(); im.save(o, 'WEBP', quality=68)
        return u, 'data:image/webp;base64,' + base64.b64encode(o.getvalue()).decode()
    except Exception as e:
        return u, None
out = {}
with cf.ThreadPoolExecutor(12) as ex:
    for u, d in ex.map(one, urls):
        if d: out[u] = d
json.dump(out, open('thumbs.json', 'w'))
print(len(urls), len(out))
