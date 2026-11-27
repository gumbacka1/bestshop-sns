import re,urllib.request,json
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36'
u='https://www.lge.co.kr/product/care-solutions/refrigerators/s834mee141'
t=urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':UA}),timeout=40).read().decode('utf-8','ignore')
print('LEN',len(t))
for kw in ['선납','prepay','Prepay','PREPAY','prePay','advance','Advance','prpay','preRental','선결제']:
    idx=[m.start() for m in re.finditer(kw,t)][:6]
    print('KW',kw,len(re.findall(kw,t)))
    for i in idx[:4]: print('  CTX',t[max(0,i-250):i+350].replace('\n',' '))
for js in sorted(set(re.findall(r'src="([^"]+\.js[^"]*)"',t)))[:60]:
    try:
        s=urllib.request.urlopen(urllib.request.Request(js if js.startswith('http') else 'https://www.lge.co.kr'+js,headers={'User-Agent':UA}),timeout=30).read().decode('utf-8','ignore')
        for m in re.finditer(r'.{0,160}(선납|prepay|Prepay|prePay).{0,220}',s):
            print('JS',js[-50:],'|',m.group(0)[:380]);break
        for m in set(re.findall(r'["\'](/[\w/]*(?:[Pp]repay|[Pp]rePay|calc|Calc|price|Price)[\w/]*\.lgajax)["\']',s)): print('API',js[-40:],m)
    except Exception as e: pass
