# 베스트샵 판촉 상세를 실제 브라우저(Playwright)로 열어 본문 이미지·화면을 모으고 글자 인식
# 결과: data/lge_full/bestshop_render.json (글자만), 이미지·화면은 /tmp/bs_render (아티팩트)
import json, os, re, hashlib, subprocess, urllib.request
from playwright.sync_api import sync_playwright
D = os.path.join(os.path.dirname(__file__), '..', 'data', 'lge_full')
OUTD = '/tmp/bs_render'; os.makedirs(OUTD, exist_ok=True)
P = json.load(open(os.path.join(D, 'bestshop_promos.json'), encoding='utf-8'))['pages']
targets = [k for k in P if re.search(r'/event/detail/|paymentDiscount|affiliateDiscount|certifyBenefit|aptBenefit|eventStoreBranchDetail', k)]
targets += [k for k in P if 'eventStoreOpenDetail' in k][:3]
SKIP = re.compile(r'img_sns_share|/icons?/|logo|btn_|ico_|favicon|/common/|renewal/main/icon')

def ocr(path):
    base = path + '_t'
    subprocess.run(['convert', path + '[0]', '-colorspace', 'Gray', '-crop', '100%x1400', '+repage', base + '_%03d.png'], capture_output=True)
    tiles = sorted(x for x in os.listdir(OUTD) if x.startswith(os.path.basename(base) + '_'))
    out = []
    for t in tiles:
        try:
            r = subprocess.run(['tesseract', os.path.join(OUTD, t), '-', '-l', 'kor+eng', '--psm', '6'], capture_output=True, text=True, timeout=120)
            out.append(r.stdout)
        except subprocess.TimeoutExpired:
            pass
        os.remove(os.path.join(OUTD, t))
    return '\n'.join(x.strip() for x in '\n'.join(out).split('\n') if len(x.strip()) > 1)

res = {}
with sync_playwright() as pw:
    b = pw.chromium.launch()
    pg = b.new_page(viewport={'width': 900, 'height': 1400}, locale='ko-KR')
    for k in targets:
        url = 'https://bestshop.lge.co.kr' + k
        try:
            pg.goto(url, wait_until='networkidle', timeout=60000)
            for _ in range(12):
                pg.mouse.wheel(0, 2500); pg.wait_for_timeout(400)
            pg.wait_for_timeout(1500)
            srcs = pg.eval_on_selector_all('img', 'els => els.filter(e => e.naturalWidth >= 300 && e.naturalHeight >= 150).map(e => e.currentSrc || e.src)')
            alts = pg.eval_on_selector_all('img', 'els => els.filter(e => e.naturalWidth >= 300).map(e => e.alt).filter(a => a && a.length > 3)')
            body = pg.inner_text('main') if pg.query_selector('main') else ''
            shot = hashlib.md5(k.encode()).hexdigest()[:10] + '_page.png'
            pg.screenshot(path=os.path.join(OUTD, shot), full_page=True)
        except Exception as e:
            res[k] = {'error': str(e)[:150]}; continue
        imgs = []
        for s in dict.fromkeys(srcs):
            if SKIP.search(s): continue
            f = os.path.join(OUTD, hashlib.md5(s.encode()).hexdigest()[:12] + '.img')
            try:
                req = urllib.request.Request(s, headers={'User-Agent': 'Mozilla/5.0', 'Referer': url})
                open(f, 'wb').write(urllib.request.urlopen(req, timeout=40).read())
                imgs.append({'src': s, 'file': os.path.basename(f), 'text': ocr(f)})
            except Exception as e:
                imgs.append({'src': s, 'error': str(e)[:100]})
        res[k] = {'title': P[k].get('title'), 'url': url, 'shot': shot, 'alts': alts[:40], 'body_text': body[:20000], 'images': imgs}
        print(k, '이미지', len(imgs))
    b.close()
json.dump(res, open(os.path.join(D, 'bestshop_render.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('완료', len(res))
