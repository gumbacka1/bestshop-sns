import re,urllib.request,json
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36'
def get(u,data=None):
    return urllib.request.urlopen(urllib.request.Request(u,data=data,headers={'User-Agent':UA,'X-Requested-With':'XMLHttpRequest'}),timeout=40).read().decode('utf-8','ignore')
t=get('https://www.lge.co.kr/home')
for m in sorted(set(re.findall(r'[\w/.\-]*[Rr]anking[\w/.\-]*',t)))[:40]: print('REF',m)
for js in sorted(set(re.findall(r'src="([^"]+\.js[^"]*)"',t))):
    if 'main' in js or 'home' in js or 'rank' in js.lower():
        try:
            s=get(js if js.startswith('http') else 'https://www.lge.co.kr'+js)
            for m in set(re.findall(r'["\'][\w/]*[Rr]anking[\w/.]*["\']',s)): print('JS',js[-60:],m)
        except Exception as e: print('ERR',js,e)
# try likely APIs
import urllib.parse
for api in ['/mkt/api/bestRanking/retrieveCategoryList.lgajax','/mkt/api/bestRanking/retrieveBestRankingCategoryList.lgajax','/mkt/api/bestRanking/retrieveCategoryProductList.lgajax']:
    for body in [{'rankingType':'todays'},{'rankingType':'todays','categoryId':''}]:
        try: r=get('https://www.lge.co.kr'+api,urllib.parse.urlencode(body).encode());print('API',api,body,r[:1500])
        except Exception as e: print('APIERR',api,e)
