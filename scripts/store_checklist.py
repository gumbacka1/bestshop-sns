# 베스트샵 운영 모델 체크용 엑셀 (품목 묶음별 시트, '운영' 칸에 O 선택)
import json, os, re, datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.formatting.rule import FormulaRule
B = os.path.join(os.path.dirname(__file__), '..')
P = json.load(open(os.path.join(B, 'data/lge_full/products.json'), encoding='utf-8'))
F = 'LG스마트체2.0 Regular'
G = [('냉장고', {'냉장고', '김치냉장고', '컨버터블 패키지', '와인셀러'}),
     ('세탁·의류', {'세탁 건조기', '세탁기', '의류건조기', '의류관리기', '신발관리기', '시스템 아이어닝'}),
     ('TV·영상', {'TV', '스탠바이미', '오디오', '프로젝터'}),
     ('에어컨', {'에어컨', '시스템 에어컨', 'OS 계절가전', '선풍기'}),
     ('주방', {'정수기', '전기레인지', '식기세척기', '광파오븐/전자레인지', '주방소형가전', '식물생활가전'}),
     ('공기·생활', {'공기청정기', '가습 공기청정기', '360° 공기청정기', '시스템 공기청정기', '제습기', '가습기', '청소기', '무선청소기', '환기 시스템', '바스에어시스템', '안마의자', '마인드웰니스', 'AI Home 제품'}),
     ('PC·모니터', {'노트북', '모니터', '일체형/데스크톱/태블릿', '사이니지'})]
MISSING = [('TV·영상', 'TV', 'OLED', 'OLED83G5KW', 'LG 올레드 evo AI (벽걸이형)', 13000000, None),
           ('냉장고', '냉장고', '', 'D604MEE52', 'LG 일반냉장고 오브제컬렉션 (구독 랭킹)', None, 23900),
           ('냉장고', '냉장고', '', 'M301S31', 'LG 모던엣지 냉장고 (랭킹)', 720000, None)]
def num(v):
    try: return int(float(v))
    except Exception: return None
def rv(v):
    s = re.sub(r'\D', '', str(v or '')); return int(s) if s else 0
rows = {g: [] for g, _ in G}; rows['기타'] = []
for p in P:
    if p.get('modelStatusCode') == 'NOT_FOR_SALE': continue
    pm = (p.get('care') or {}).get('price_map') or {}
    if not p.get('obsOriginalPrice') and not pm: continue
    c = p.get('categoryName') or ''
    g = next((n for n, s in G if c in s), '기타')
    sp = p.get('specs') or {}
    rel = (p.get('modelReleaseDate') or sp.get('동일모델의 출시년월') or '')[:7]
    cap = next((v for k, v in sp.items() if re.search(r'전체 용량|화면 크기|냉방면적|세탁 용량|건조 용량|용량', k)), '')
    sub72 = min([v.get('monthlyPrice') or 0 for k, v in pm.items() if k.startswith('72_') and v.get('monthlyPrice')] or [0]) or None
    orig = num(p.get('obsOriginalPrice')); disc = orig - (num(p.get('obsMemberPrice')) or 0) if orig else None
    rows[g].append(['', '', c, p.get('subCategoryName') or '', p.get('modelName'), p.get('modelDisplayName') or '', rel, str(cap)[:20],
                    orig, disc, sub72, 'Y' if p.get('다품목') == 'Y' else '', 'Y' if p.get('lgecomOnlyFlag') == 'Y' else '',
                    '판매예정' if p.get('modelStatusCode') == 'READY_FOR_SALE' else ('품절' if p.get('modelStatusCode') == 'SOLD_OUT' else ''),
                    rv(p.get('reviewCount'))])
import csv
_have = {(p.get('modelName') or '').upper() for p in P}
_mp = os.path.join(B, 'data/lge_full/mltp/다품목_모델마스터.csv')
if os.path.exists(_mp):
    for r in csv.DictReader(open(_mp, encoding='utf-8-sig')):
        if r['모델명'].upper() in _have or any(r['모델명'] == x[3] for x in MISSING): continue
        gg = next((n for n, st in G if r['제품군'] in st), '기타')
        if '냉장' in r['제품군']: gg = '냉장고'
        elif any(k in r['제품군'] for k in ('오븐', '식기', '정수')): gg = '주방'
        elif any(k in r['제품군'] for k in ('로봇', '안마', '청소', '공기')): gg = '공기·생활'
        MISSING.append((gg, r['제품군'], '', r['모델명'], r['제품명'], int(float(r['정가'] or 0)) or None, int(float(r['구독월요금'] or 0)) or None))
for g, c, s, m, n, o, sub in MISSING:
    rows[g].append(['', '수집 보완 중', c, s, m, n, '', '', o, o, sub, '', '', '목록 누락', 0])
H = ['운영', '메모', '품목', '세부', '모델', '제품명', '출시', '용량·크기', '정상가', '할인가', '구독 6년 월', '다품목', '닷컴전용', '상태', '리뷰 수']
W = [7, 14, 12, 14, 17, 44, 9, 12, 12, 12, 12, 8, 9, 9, 8]
hdr = PatternFill('solid', fgColor='EDEDED'); on = PatternFill('solid', fgColor='E2F0D9')
thin = Side(style='thin', color='BFBFBF'); line = Border(bottom=thin)
wb = Workbook(); ws = wb.active; ws.title = '사용법'
day = (datetime.datetime.utcnow() + datetime.timedelta(hours=9)).strftime('%y%m%d')
guide = [['베스트샵 운영 모델 체크표', ''], ['', ''], ['■ 하는 법', ''],
         ['- 각 시트 맨 왼쪽 "운영" 칸을 누르면 목록이 떠요 → O 선택 (직접 O 입력해도 돼요)', ''],
         ['- 체크하면 그 줄이 연한 초록으로 바뀌어요', ''],
         ['- 메모 칸: 전략모델·본사지정·진열만 등 자유롭게', ''],
         ['- 제목줄 필터로 품목·세부별로 좁혀서 보면 편해요 (리뷰 많은 순 정렬되어 있음)', ''],
         ['- 다 하면 이 파일 그대로 대화창에 올려 주세요', ''], ['', ''], ['■ 시트별 체크 현황', ''], ['시트', '모델 수 / 체크 수']]
for r in guide: ws.append(r)
order = [g for g, _ in G] + ['기타']
for g in order:
    if not rows[g]: continue
    ws.append([g, f'=COUNTA(\'{g}\'!E2:E{len(rows[g]) + 1})&" / "&COUNTIF(\'{g}\'!A2:A{len(rows[g]) + 1},"O")'])
ws.append(['']); ws.append(['▶ 코멘트'])
ws.append(['- 엘지닷컴 ' + day + ' 수집 기준, 판매중지(NOT_FOR_SALE) 모델은 뺐어요'])
ws.append(['- "수집 보완 중" 줄은 사이트 목록에서 빠져 있던 모델이라 가격만 우선 넣었어요'])
for row in ws.iter_rows():
    for c in row: c.font = Font(name=F, size=11, bold=(c.row in (1, 11)))
ws['A1'].font = Font(name=F, size=14, bold=True); ws.column_dimensions['A'].width = 70; ws.column_dimensions['B'].width = 20
for g in order:
    R = sorted(rows[g], key=lambda r: (r[2], r[3], -r[14]))
    if not R: continue
    s = wb.create_sheet(g); s.append(H)
    for r in R: s.append(r)
    n = len(R) + 1
    for i, w in enumerate(W): s.column_dimensions[chr(65 + i)].width = w
    for c in s[1]: c.font = Font(name=F, bold=True); c.fill = hdr; c.alignment = Alignment(horizontal='center', vertical='center')
    for row in s.iter_rows(min_row=2):
        for c in row:
            c.font = Font(name=F); c.border = line
            if c.column in (9, 10, 11): c.number_format = '#,##0;-#,##0;"-"'
            if c.column in (1, 12, 13, 14): c.alignment = Alignment(horizontal='center')
    dv = DataValidation(type='list', formula1='"O"', allow_blank=True); s.add_data_validation(dv); dv.add(f'A2:A{n}')
    s.conditional_formatting.add(f'A2:O{n}', FormulaRule(formula=['$A2="O"'], fill=on))
    s.freeze_panes = 'F2'; s.auto_filter.ref = f'A1:O{n}'; s.row_dimensions[1].height = 22
out = os.path.join('/home/claude/out', f'베샵운영모델_체크_{day}_v2.xlsx')
wb.save(out); print(out, {g: len(rows[g]) for g in order}, round(os.path.getsize(out) / 1e6, 2), 'MB')
