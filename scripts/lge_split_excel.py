# 큰 엑셀을 품목 묶음별로 나눔 → data/lge_full/split/ (드라이브 올리기용, 파일당 3MB 아래 목표)
import json, os, sys, glob
sys.path.insert(0, os.path.dirname(__file__))
import lge_full_excel as X
D = X.D
OUT = os.path.join(D, 'split'); os.makedirs(OUT, exist_ok=True)
for f in glob.glob(os.path.join(OUT, '*.xlsx')): os.remove(f)
G = [('냉장고', {'냉장고', '김치냉장고', '컨버터블 패키지', '와인셀러'}),
     ('세탁·의류', {'세탁 건조기', '세탁기', '의류건조기', '의류관리기', '신발관리기', '시스템 아이어닝'}),
     ('TV·영상', {'TV', '스탠바이미', '오디오', '프로젝터'}),
     ('에어컨', {'에어컨', '시스템 에어컨', 'OS 계절가전', '선풍기'}),
     ('주방', {'정수기', '전기레인지', '식기세척기', '광파오븐/전자레인지', '주방소형가전', '식물생활가전'}),
     ('공기·생활', {'공기청정기', '가습 공기청정기', '360° 공기청정기', '시스템 공기청정기', '제습기', '가습기', '청소기', '무선청소기', '환기 시스템', '바스에어시스템', '안마의자', '마인드웰니스', 'AI Home 제품'}),
     ('PC·모니터', {'노트북', '모니터', '일체형/데스크톱/태블릿', '사이니지'})]
P = X.load('products.json', [])
used = set()
for name, cats in G:
    part = [p for p in P if p.get('categoryName') in cats]
    used.update(id(p) for p in part)
    X.main(part, os.path.join(OUT, f'엘지닷컴_{name}_{{day}}_v1.xlsx'), no_common=True)
rest = [p for p in P if id(p) not in used]
X.main(rest, os.path.join(OUT, '엘지닷컴_기타품목_{day}_v1.xlsx'), no_common=True)
X.main([], os.path.join(OUT, '엘지닷컴_공통(혜택·카드·판촉·랭킹)_{day}_v1.xlsx'))
for f in sorted(glob.glob(os.path.join(OUT, '*.xlsx'))): print(round(os.path.getsize(f) / 1e6, 2), 'MB', os.path.basename(f))
