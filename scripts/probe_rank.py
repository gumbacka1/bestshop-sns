import re,urllib.request
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36'
for u in ['https://www.lge.co.kr/home']:
    t=urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':UA}),timeout=40).read().decode('utf-8','ignore')
    i=t.find('베스트 랭킹');print(len(t),i)
    for m in re.finditer(r'.{0,200}CT5\d{7}.{0,120}',t[i-2000:i+60000]): print(m.group(0).replace('\n',' ')[:320]);print('--')
