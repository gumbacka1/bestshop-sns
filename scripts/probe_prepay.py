import urllib.request,re
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36'
def get(u,h=None):
    r=urllib.request.Request(u,headers=dict({'User-Agent':UA},**(h or {})))
    with urllib.request.urlopen(r,timeout=40) as x: return x.status,x.read().decode('utf-8','ignore')
t=get('https://www.lge.co.kr/product/care-solutions/refrigerators/s834mee141')[1]
js=[j for j in set(re.findall(r'src="([^"]+\.js[^"]*)"',t)) if '4150-' in j][0]
s=get('https://www.lge.co.kr'+js)[1]
for m in set(re.findall(r'"(https?://[^"]{5,80})"',s)): print('URL',m)
i=s.find('summary/subscription/monthly'); print('CTX',s[max(0,i-3000):i-1500].replace('\n',' ')[:1500])
for base in ['https://www.lge.co.kr','https://www.lge.co.kr/product','https://www.lge.co.kr/api','https://www.lge.co.kr/product/api']:
    for path in ['/ajax/v2/models/MD10635828/summary/subscription/options','/ajax/v1/models/MD10635828/summary/subscription/options']:
        try: st,b=get(base+path,{'Accept':'application/json','X-Requested-With':'XMLHttpRequest'});print('TRY',base+path,st,b[:300])
        except Exception as e: print('TRY',base+path,e)
