import urllib.request,json,time
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36'
def get(u):
    r=urllib.request.Request(u,headers={'User-Agent':UA,'Accept':'application/json','Referer':'https://www.lge.co.kr/'})
    return json.loads(urllib.request.urlopen(r,timeout=40).read().decode('utf-8','ignore'))
M={'냉장고 S834MEE141':'MD10635828','김치 Z330MEEF21':'MD10545826','TV OLED77C6QNA':'MD10770872','워시타워 WA2525YMP6R':'MD10917857','세탁기 FG24EN':'MD10884826','건조기 RD25ESER':'MD10907839','정수기 WD522MC':'MD10822828','스타일러 SC5GMR80S':'MD10796836','식세기 DUE6BGE':'MD10491826','전기레인지 BEF3ASMLE':'MD10630854','안마의자 MH21BBY':'MD10436841','스탠바이미 32LX6BPGA':'MD10801828','로봇청소기 N95THO':'MD10730837','에어컨 FQ18EN9BE2':'MD10297840','바스에어 MX0120BASV':'MD10753826'}
B='https://www.lge.co.kr'
out={}
for name,mid in M.items():
    try:
        o=get(f'{B}/ajax/v2/models/{mid}/summary/subscription/options')
        out[name]={'options':o}
        s=json.dumps(o,ensure_ascii=False)
        import re
        seqs=list(dict.fromkeys(re.findall(r'"rtModelSeq"\s*:\s*"?(\d+)',s)))[:3]
        out[name]['seqs']=seqs
        for q in seqs[:1]:
            for rate in [None,10,20,30,40,50]:
                u=f'{B}/ajax/v1/models/{mid}/summary/subscription/monthly?rtModelSeq={q}'+(f'&prepayRate={rate}' if rate is not None else '')
                try: out[name][f'monthly_{rate}']=get(u)
                except Exception as e: out[name][f'monthly_{rate}']=str(e)
                time.sleep(0.3)
        print('OK',name,seqs)
    except Exception as e: print('ERR',name,e)
    time.sleep(0.5)
json.dump(out,open('prepay.json','w'),ensure_ascii=False,indent=1)
