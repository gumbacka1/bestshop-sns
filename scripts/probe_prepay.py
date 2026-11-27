import re,urllib.request
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36'
def get(u): return urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':UA}),timeout=40).read().decode('utf-8','ignore')
t=get('https://www.lge.co.kr/product/care-solutions/refrigerators/s834mee141')
for js in sorted(set(re.findall(r'src="([^"]+\.js[^"]*)"',t))):
    try: s=get(js if js.startswith('http') else 'https://www.lge.co.kr'+js)
    except Exception: continue
    for kw in ['prepayRate','prepay','정액','정률','선납']:
        for m in list(re.finditer(kw,s))[:3]:
            print('JS',js[-45:],kw,'|',s[max(0,m.start()-300):m.start()+300].replace('\n',' '))
    for m in set(re.findall(r'["\'`](/[\w\-/{}$.]*(?:subscription|Subscription|rental|Rental|care)[\w\-/{}$.]*)["\'`]',s)): print('PATH',js[-40:],m)
